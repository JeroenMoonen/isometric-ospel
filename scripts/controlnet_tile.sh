#!/usr/bin/env bash
# Repaint one rendered map tile in a smoother, cel-shaded illustration style with
# SDXL img2img plus ControlNet, so the layout of the tile stays where it is.
#
# Usage: scripts/controlnet_tile.sh <color.png> <height.png> <out.png>
#
#   color.png   the color render, e.g. `node render/run.mjs crop ... --kuwahara 2`
#   height.png  the matching height pass (`--pass height`), used as the depth control
#   out.png     where the repainted tile goes
#
# Runs ComfyUI headless (API only, 127.0.0.1) from data/comfyui/, on the GPU through
# PyTorch ROCm. If no server answers on the port, this script starts one and stops it
# again when it is done; set KEEP_SERVER=1 to leave it running for a batch (models stay
# loaded, about 12 GB of GPU memory, so the next tile skips the ~5 s load) and stop it
# afterwards with `pkill -f 'ComfyUI/main.py --listen 127.0.0.1 --port 8188'`.
# The GPU memory (GTT) is shared with the desktop: the script refuses to run next to
# sd-cli or another ComfyUI, the server keeps 30 GB free (RESERVE_VRAM), and the VAE
# runs in tiles. Measured peak for one 2x tile: 13 GB on top of the desktop's ~3.5 GB.
# Setup and model downloads: see the bottom.
#
# Models: DreamShaper XL Turbo v2.1 (base, 8 steps) and xinsir ControlNet Union SDXL
# ProMax, which gets three controls: the height map as "depth", a Canny edge map of
# the color render as "canny", and the color render itself as "tile" (holds colours
# and small shapes). The tile is painted at twice its size and scaled back down,
# then its global colours are matched back to the input.
# About 170 s per 1024 tile on the Radeon 8060S with SCALE=2 (plus ~5 s to start the
# server), about 32 s with SCALE=1.
#
# Env overrides (defaults are the chosen setting):
#   DENOISE  img2img strength, 0..1          (0.6)
#   DEPTH    depth ControlNet strength       (0.6)
#   CANNY    canny ControlNet strength       (0.8)
#   TILE     tile ControlNet strength        (0.5, 0 = off)
#   COLOR_MATCH  pull the global colour statistics back to the input (mkl in Lab), 0..1 (1)
#   SCALE    paint at this multiple of the input size and scale back down (2); 2 gives
#            the model four times the pixels per house and much crisper houses, at
#            about five times the time of SCALE=1
#   CN_END   all controls stop at this fraction of the steps (1.0)
#   CANNY_LO / CANNY_HI  Canny thresholds 0..1 (0.16 / 0.36 divided by SCALE, because
#            upscaling spreads every edge over more pixels and weakens its gradient)
#   STEPS (8)  CFG (2.0)  SEED (42)  SAMPLER (dpmpp_sde)  SCHEDULER (karras)
#   PROMPT / NEGATIVE    replace the prompts
#   COMFY_PORT (8188)  KEEP_SERVER (0)  RESERVE_VRAM (30, GB the server leaves free)
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <color.png> <height.png> <out.png>" >&2
  exit 1
fi
color=$(realpath "$1") height=$(realpath "$2") out=$3

root=$(cd "$(dirname "$0")/.." && pwd)
comfy=$root/data/comfyui
port=${COMFY_PORT:-8188}
api=http://127.0.0.1:$port

ckpt=DreamShaperXL_Turbo_v2_1.safetensors
cnet=xinsir-union-sdxl-promax.safetensors

prompt=${PROMPT:-"isometric vector illustration of a small Dutch village, cel shaded, flat colors, clean sharp edges, simple clean shapes, crisp outlines, bright saturated colors, 1990s isometric city-builder game art, red brick houses with dark grey roofs, lush green round trees, blue canal, green meadows, brown ploughed fields"}
negative=${NEGATIVE:-"photo, photorealistic, watercolor, painting, brush strokes, soft, blurry, muddy, desaturated, washed out, noise, grain, dithering, texture, jpeg artifacts, text, watermark, people, cars, swimming pool"}

scale=${SCALE:-2}
canny_lo=${CANNY_LO:-$(LC_ALL=C awk -v s="$scale" 'BEGIN { printf "%.2f", 0.16 / s }')}
canny_hi=${CANNY_HI:-$(LC_ALL=C awk -v s="$scale" 'BEGIN { printf "%.2f", 0.36 / s }')}

# --- guard -------------------------------------------------------------------------

# The GPU shares its memory (GTT) with the desktop. Two image models at once filled it
# and took Hyprland down, so refuse to run next to another model process: sd-cli, or a
# ComfyUI that is not the one on our port.
others=$({
  pgrep -ax sd-cli
  pgrep -af 'ComfyUI/main\.py' | awk '$2 ~ /python/' | grep -v -- "--port $port "
} || true)
if [[ -n $others ]]; then
  echo "another image model is running, not starting a second one:" >&2
  echo "$others" >&2
  exit 1
fi

# --- server -----------------------------------------------------------------------

started=
stop_server() {
  if [[ -n $started ]]; then
    kill "$started" 2>/dev/null || true
    wait "$started" 2>/dev/null || true
  fi
}
trap stop_server EXIT

if ! curl -sf "$api/system_stats" >/dev/null; then
  [[ -x $comfy/.venv/bin/python ]] || { echo "no venv in $comfy, see the setup notes at the bottom of $0" >&2; exit 1; }
  echo "starting ComfyUI on $api (log: $comfy/server.log)" >&2
  # The VAE works in tiles (see the workflow) and the allocator returns memory, so the GPU never fills up:
  # two models at once once crashed the desktop on this machine.
  PYTORCH_HIP_ALLOC_CONF=expandable_segments:True nohup "$comfy/.venv/bin/python" "$comfy/ComfyUI/main.py" \
    --listen 127.0.0.1 --port "$port" --base-directory "$comfy" \
    --disable-auto-launch --preview-method none \
    --reserve-vram "${RESERVE_VRAM:-30}" \
    >"$comfy/server.log" 2>&1 &
  started=$!
  [[ ${KEEP_SERVER:-0} == 1 ]] && { disown "$started"; started=; }
  for _ in $(seq 120); do
    curl -sf "$api/system_stats" >/dev/null && break
    sleep 1
  done
  curl -sf "$api/system_stats" >/dev/null || { echo "ComfyUI did not come up, see $comfy/server.log" >&2; exit 1; }
fi

# --- inputs -----------------------------------------------------------------------

# Upload both images under a content-hash name, so reruns reuse the upload.
upload() {
  local name
  name=cn_$(sha1sum "$1" | cut -c1-12).png
  curl -sf -F "image=@$1;filename=$name" -F overwrite=true -F type=input "$api/upload/image" | jq -r .name
}
color_name=$(upload "$color")
height_name=$(upload "$height")

# --- workflow (ComfyUI API format) -------------------------------------------------

workflow=$(jq -n \
  --arg ckpt "$ckpt" --arg cnet "$cnet" \
  --arg color "$color_name" --arg height "$height_name" \
  --arg pos "$prompt" --arg neg "$negative" \
  --argjson denoise "${DENOISE:-0.6}" \
  --argjson depth "${DEPTH:-0.6}" --argjson canny "${CANNY:-0.8}" \
  --argjson tile "${TILE:-0.5}" --argjson match "${COLOR_MATCH:-1}" \
  --argjson cn_end "${CN_END:-1.0}" --argjson scale "$scale" \
  --argjson lo "$canny_lo" --argjson hi "$canny_hi" \
  --argjson steps "${STEPS:-8}" --argjson cfg "${CFG:-2.0}" --argjson seed "${SEED:-42}" \
  --arg sampler "${SAMPLER:-dpmpp_sde}" --arg scheduler "${SCHEDULER:-karras}" \
  '{
    "ckpt":   {class_type: "CheckpointLoaderSimple", inputs: {ckpt_name: $ckpt}},
    "color_in":  {class_type: "LoadImage", inputs: {image: $color}},
    "height_in": {class_type: "LoadImage", inputs: {image: $height}},
    "color":  {class_type: "ImageScaleBy", inputs: {image: ["color_in", 0], upscale_method: "lanczos", scale_by: $scale}},
    "height": {class_type: "ImageScaleBy", inputs: {image: ["height_in", 0], upscale_method: "bilinear", scale_by: $scale}},
    "edges":  {class_type: "Canny", inputs: {image: ["color", 0], low_threshold: $lo, high_threshold: $hi}},
    "cn":     {class_type: "ControlNetLoader", inputs: {control_net_name: $cnet}},
    "cn_depth": {class_type: "SetUnionControlNetType", inputs: {control_net: ["cn", 0], type: "depth"}},
    "cn_canny": {class_type: "SetUnionControlNetType", inputs: {control_net: ["cn", 0], type: "canny/lineart/anime_lineart/mlsd"}},
    "cn_tile":  {class_type: "SetUnionControlNetType", inputs: {control_net: ["cn", 0], type: "tile"}},
    "pos":    {class_type: "CLIPTextEncode", inputs: {clip: ["ckpt", 1], text: $pos}},
    "neg":    {class_type: "CLIPTextEncode", inputs: {clip: ["ckpt", 1], text: $neg}},
    "apply_depth": {class_type: "ControlNetApplyAdvanced", inputs: {
      positive: ["pos", 0], negative: ["neg", 0], control_net: ["cn_depth", 0],
      image: ["height", 0], strength: $depth, start_percent: 0, end_percent: $cn_end, vae: ["ckpt", 2]}},
    "apply_canny": {class_type: "ControlNetApplyAdvanced", inputs: {
      positive: ["apply_depth", 0], negative: ["apply_depth", 1], control_net: ["cn_canny", 0],
      image: ["edges", 0], strength: $canny, start_percent: 0, end_percent: $cn_end, vae: ["ckpt", 2]}},
    "apply_tile": {class_type: "ControlNetApplyAdvanced", inputs: {
      positive: ["apply_canny", 0], negative: ["apply_canny", 1], control_net: ["cn_tile", 0],
      image: ["color", 0], strength: $tile, start_percent: 0, end_percent: $cn_end, vae: ["ckpt", 2]}},
    "latent": {class_type: "VAEEncodeTiled", inputs: {pixels: ["color", 0], vae: ["ckpt", 2], tile_size: 512, overlap: 64, temporal_size: 64, temporal_overlap: 8}},
    "sample": {class_type: "KSampler", inputs: {
      model: ["ckpt", 0], seed: $seed, steps: $steps, cfg: $cfg,
      sampler_name: $sampler, scheduler: $scheduler,
      positive: ["apply_tile", 0], negative: ["apply_tile", 1],
      latent_image: ["latent", 0], denoise: $denoise}},
    "decode": {class_type: "VAEDecodeTiled", inputs: {samples: ["sample", 0], vae: ["ckpt", 2], tile_size: 512, overlap: 64, temporal_size: 64, temporal_overlap: 8}},
    "down":   {class_type: "ImageScaleBy", inputs: {image: ["decode", 0], upscale_method: "area", scale_by: (1 / $scale)}},
    "match":  {class_type: "ColorTransfer", inputs: {
      image_target: ["down", 0], image_ref: ["color_in", 0], method: "mkl_lab",
      source_stats: "per_frame", strength: $match}},
    "save":   {class_type: "SaveImage", inputs: {images: ["match", 0], filename_prefix: "controlnet_tile"}},
    "save_edges": {class_type: "SaveImage", inputs: {images: ["edges", 0], filename_prefix: "controlnet_edges"}}
  }')

# --- run --------------------------------------------------------------------------

t0=$(date +%s)
response=$(curl -s -H 'Content-Type: application/json' -d "$(jq -n --argjson p "$workflow" '{prompt: $p}')" "$api/prompt")
id=$(jq -r '.prompt_id // empty' <<<"$response")
[[ -n $id ]] || { echo "ComfyUI refused the workflow: $response" >&2; exit 1; }

while :; do
  history=$(curl -sf "$api/history/$id" || echo '{}')
  status=$(jq -r --arg id "$id" '.[$id].status.status_str // empty' <<<"$history")
  [[ $status == success ]] && break
  if [[ $status == error ]]; then
    jq --arg id "$id" '.[$id].status.messages' <<<"$history" >&2
    exit 1
  fi
  sleep 1
done

file=$(jq -r --arg id "$id" '.[$id].outputs.save.images[0] | "filename=\(.filename)&subfolder=\(.subfolder)&type=\(.type)"' <<<"$history")
mkdir -p "$(dirname "$out")"
curl -sf -o "$out" "$api/view?$file"
# Keep the edge map next to the output when asked, handy to judge the canny control.
if [[ -n ${EDGES_OUT:-} ]]; then
  file=$(jq -r --arg id "$id" '.[$id].outputs.save_edges.images[0] | "filename=\(.filename)&subfolder=\(.subfolder)&type=\(.type)"' <<<"$history")
  curl -sf -o "$EDGES_OUT" "$api/view?$file"
fi
echo "$out ($(($(date +%s) - t0)) s)" >&2

# --- setup (once, everything under data/comfyui/, about 17 GB) ------------------------
#   cd data/comfyui
#   uv venv --python 3.12 .venv
#   # PyTorch with ROCm for gfx1151 from AMD's TheRock stable index. Pin torch to 2.13:
#   # the newest torchvision there (0.28) is built against it, 2.14 breaks torchvision::nms.
#   uv pip install --python .venv/bin/python --index-url https://stable.repo.amd.com/rocm/whl-next/ \
#     --index-strategy unsafe-best-match "torch[device-gfx1151]==2.13.0+rocm10.1.0" \
#     "torchvision[device-gfx1151]==0.28.0+rocm10.1.0" "torchaudio==2.11.*"
#   git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git ComfyUI
#   grep -vE '^(torch|torchvision|torchaudio)$' ComfyUI/requirements.txt > /tmp/comfy-req.txt
#   uv pip install --python .venv/bin/python -r /tmp/comfy-req.txt
#   mkdir -p custom_nodes input output user models/checkpoints models/controlnet
#   hf=https://huggingface.co
#   curl -L -o models/checkpoints/DreamShaperXL_Turbo_v2_1.safetensors \
#     $hf/Lykon/dreamshaper-xl-v2-turbo/resolve/main/DreamShaperXL_Turbo_v2_1.safetensors
#   curl -L -o models/controlnet/xinsir-union-sdxl-promax.safetensors \
#     $hf/xinsir/controlnet-union-sdxl-1.0/resolve/main/diffusion_pytorch_model_promax.safetensors
