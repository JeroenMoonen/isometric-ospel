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
# The defaults live in plain variables: inside ${REPAINT_CMD:-...} the first "}" (of {inp}) would end the expansion.
if [ "$ENGINE" = controlnet ]; then
  # Keep ComfyUI running between tiles (the models stay loaded); it is stopped at the end, see cleanup.
  default_cmd='KEEP_SERVER=1 scripts/controlnet_tile.sh {inp} {height} {out}'
else
  default_cmd='MODE=img2img STRENGTH=0.75 STEPS=8 scripts/local_tile.sh {inp} {out}'
fi
REPAINT_CMD="${REPAINT_CMD:-$default_cmd}"
echo "engine: $ENGINE"
start=$(date +%s)

cleanup() { [ "$ENGINE" = controlnet ] && pkill -f '[C]omfyUI/main.py' 2>/dev/null; true; }
trap cleanup EXIT

fail() {
  echo "== $(date '+%F %T') failed: $1"
  telegram "Helenaveen overschilderen is mislukt: $1. Log: out/repaint/night.log op de Framework." || true
  exit 1
}

# Control images, pixel-aligned with out/full-4.png: the height pass guides ControlNet, and the roads mask keeps
# the rendered roads in the result (scripts/repaint_map.py). Rendered again when the map is newer than they are.
render_pass() {
  local f="out/full-4-$1.png" ok
  [ -f "$f" ] && [ "$f" -nt out/full-4.png ] && return 0
  node render/run.mjs all --scale 4 --tile 2048 --pass "$1" || return 1
  read -r W H C < <(python3 -c "import json; d=json.load(open('out/tiles-4-$1/layout.json')); print(d['width'], d['height'], d['cols'])")
  vips arrayjoin "$(/bin/ls out/tiles-4-"$1"/*.png | tr '\n' ' ')" "out/joined-$1.v" --across "$C" &&
    vips extract_area "out/joined-$1.v" "out/cropped-$1.v" 0 0 "$W" "$H" &&
    vips extract_band "out/cropped-$1.v" "$f[compression=1]" 0 --n "$2"
  ok=$?
  rm -f "out/joined-$1.v" "out/cropped-$1.v"
  return $ok
}

if [ "$ENGINE" = controlnet ]; then
  [ -x scripts/controlnet_tile.sh ] || fail "scripts/controlnet_tile.sh ontbreekt"
  render_pass height 3 || fail "hoogtepass renderen"
else
  grep -q 'MODE' scripts/local_tile.sh || fail "scripts/local_tile.sh kent de img2img-modus (MODE) nog niet"
fi
render_pass roads 1 || fail "wegenmasker renderen"

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
