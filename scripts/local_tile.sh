#!/usr/bin/env bash
# Repaint one rendered map tile as pixel art with a local image-edit model.
#
# Usage: scripts/local_tile.sh <input.png> <output.png> [extra prompt]
#
# Runs Qwen-Image-Edit-2511 (Q4_K_M GGUF) with the 4-step Lightning LoRA through
# stable-diffusion.cpp on the GPU via Vulkan (AUR: stable-diffusion.cpp-vulkan-bin).
# Model files live in data/models/; see the curl lines at the bottom for where they come from.
# The prompt is the PROMPT constant from scripts/ai_tile.py, so both paths stay in sync.
# Env overrides: STEPS (4 or 8, default 4), SEED (default 42).
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <input.png> <output.png> [extra prompt]" >&2
  exit 1
fi
input=$1 output=$2 extra=${3:-}

root=$(cd "$(dirname "$0")/.." && pwd)
models=$root/data/models

# Pull the triple-quoted PROMPT out of the Python script.
prompt=$(sed -n '/^PROMPT = """/,/"""$/p' "$root/scripts/ai_tile.py" | sed '1s/^PROMPT = """//; $s/"""$//')
[[ -n $extra ]] && prompt+=$'\n\n'"$extra"

# The output size follows the input, rounded down to a multiple of 16.
read -r w h < <(vipsheader -f width "$input" | tr '\n' ' '; vipsheader -f height "$input")
w=$((w / 16 * 16)) h=$((h / 16 * 16))

# There is a Lightning LoRA for 4 and for 8 steps; pick the one that matches.
steps=${STEPS:-4}
[[ $steps == 4 || $steps == 8 ]] || { echo "STEPS must be 4 or 8" >&2; exit 1; }

sd-cli \
  --diffusion-model "$models/qwen-image-edit-2511-Q4_K_M.gguf" \
  --llm "$models/Qwen2.5-VL-7B-Instruct.Q4_K_M.gguf" \
  --llm_vision "$models/Qwen2.5-VL-7B-Instruct.mmproj-Q8_0.gguf" \
  --vae "$models/qwen_image_vae.safetensors" \
  --lora-model-dir "$models/lora" \
  --model-args qwen_image_zero_cond_t=true \
  -r "$input" -W "$w" -H "$h" \
  -p "$prompt<lora:Qwen-Image-Edit-2511-Lightning-${steps}steps-V1.0-bf16:1>" \
  --steps "$steps" --cfg-scale 1.0 --sampling-method euler --flow-shift 3 \
  --seed "${SEED:-42}" \
  -o "$output"

# Model downloads (about 19.5 GB), run from data/models/:
#   hf=https://huggingface.co
#   curl -LO $hf/unsloth/Qwen-Image-Edit-2511-GGUF/resolve/main/qwen-image-edit-2511-Q4_K_M.gguf
#   curl -LO $hf/mradermacher/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct.Q4_K_M.gguf
#   curl -LO $hf/mradermacher/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct.mmproj-Q8_0.gguf
#   curl -LO $hf/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors
#   mkdir -p lora && for n in 4 8; do f=Qwen-Image-Edit-2511-Lightning-${n}steps-V1.0-bf16.safetensors
#     curl -L -o lora/$f $hf/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/$f; done
