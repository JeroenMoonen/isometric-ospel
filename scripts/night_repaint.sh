#!/usr/bin/env bash
# Overnight job: repaint the whole map with the local image model, publish it as a preview at /ai/
# (the main map stays as it is), and report on Telegram. Scheduled with systemd-run, see README.
set -uo pipefail
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:/usr/local/bin:/usr/bin:/bin"
builtin cd "$(dirname "$0")/.."
mkdir -p out/repaint
exec >>out/repaint/night.log 2>&1
echo "== $(date '+%F %T') start"

# Which model repaints the tiles: "controlnet" (ComfyUI, scripts/controlnet_tile.sh, guided by the height pass)
# or "qwen" (stable-diffusion.cpp, scripts/local_tile.sh img2img).
ENGINE="${ENGINE:-controlnet}"
if [ "$ENGINE" = controlnet ]; then
  # Keep ComfyUI running between tiles (the models stay loaded); it is stopped at the end, see cleanup.
  REPAINT_CMD="${REPAINT_CMD:-KEEP_SERVER=1 scripts/controlnet_tile.sh {inp} {height} {out}}"
else
  REPAINT_CMD="${REPAINT_CMD:-MODE=img2img STRENGTH=0.75 STEPS=8 scripts/local_tile.sh {inp} {out}}"
fi
echo "engine: $ENGINE"
start=$(date +%s)

cleanup() { [ "$ENGINE" = controlnet ] && pkill -f '[C]omfyUI/main.py' 2>/dev/null; true; }
trap cleanup EXIT

fail() {
  echo "== $(date '+%F %T') failed: $1"
  telegram "Helenaveen overschilderen is mislukt: $1. Log: out/repaint/night.log op de Framework." || true
  exit 1
}

if [ "$ENGINE" = controlnet ]; then
  [ -x scripts/controlnet_tile.sh ] || fail "scripts/controlnet_tile.sh ontbreekt"
  if [ ! -f out/full-4-height.png ]; then
    # The height pass, pixel-aligned with out/full-4.png, as the ControlNet guide.
    node render/run.mjs all --scale 4 --tile 2048 --pass height || fail "hoogtepass renderen"
    read -r W H C < <(python3 -c "import json; d=json.load(open('out/tiles-4-height/layout.json')); print(d['width'], d['height'], d['cols'])")
    vips arrayjoin "$(/bin/ls out/tiles-4-height/*.png | tr '\n' ' ')" out/joined-h.v --across "$C"
    vips extract_area out/joined-h.v out/cropped-h.v 0 0 "$W" "$H"
    vips extract_band out/cropped-h.v "out/full-4-height.png[compression=1]" 0 --n 3
    rm -f out/joined-h.v out/cropped-h.v
  fi
else
  grep -q 'MODE' scripts/local_tile.sh || fail "scripts/local_tile.sh kent de img2img-modus (MODE) nog niet"
fi

# Two image models at once exhaust the GPU's 62 GB and crash the desktop (it happened on 10 November).
# Wait up to an hour for any other model process to finish; otherwise skip tonight.
for _ in $(seq 60); do
  pgrep -f '[s]d-cli|[C]omfyUI/main.py' >/dev/null || break
  echo "$(date '+%T') another image model is running, waiting"
  sleep 60
done
pgrep -f '[s]d-cli|[C]omfyUI/main.py' >/dev/null && fail "er draaide na een uur wachten nog een ander beeldmodel op de GPU, dus ik ben niet begonnen"
uv run --quiet scripts/repaint_map.py --cmd "$REPAINT_CMD" || fail "repaint_map.py stopte"
[ -f out/full-4-ai.png ] || fail "geen out/full-4-ai.png"

./site.sh || fail "site.sh (gewone kaart)"
SITE=site/ai USE_AI=1 LABEL="Voorproef: overgeschilderd door lokaal model" ./site.sh || fail "site.sh (voorproef)"
./deploy.sh || fail "deploy.sh"

# A preview for the message: the village before and after, side by side.
read -r x y < <(uv run --quiet --with numpy python -c "
import sys; sys.path.insert(0, 'scripts')
from geo import rd_to_image
px, py = rd_to_image(191900, 377900, height_m=4)
print(int(px - 700), int(py - 450))")
vips crop out/full-4.png out/repaint/preview_before.png "$x" "$y" 1400 900
vips crop out/full-4-ai.png out/repaint/preview_after.png "$x" "$y" 1400 900
magick out/repaint/preview_before.png out/repaint/preview_after.png +append -resize 2400x -quality 88 out/repaint/preview.jpg

tiles=$(find out/repaint/out -name '*.png' | wc -l)
hours=$(( ($(date +%s) - start) / 3600 ))
mins=$(( (($(date +%s) - start) % 3600) / 60 ))
echo "== $(date '+%F %T') done: $tiles tiles in ${hours}h${mins}m"
telegram -f out/repaint/preview.jpg "Helenaveen is overgeschilderd met het lokale model: $tiles tegels in ${hours} uur en ${mins} minuten. Links de huidige kaart, rechts het resultaat. Voorproef: https://jankeesvw.github.io/isometric-helenaveen/ai/ (de gewone kaart blijft staan tot je akkoord geeft)."
