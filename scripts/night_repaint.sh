#!/usr/bin/env bash
# Overnight job: repaint the whole map with the local image model, publish it as a preview at /ai/
# (the main map stays as it is), and report on Telegram. Scheduled with systemd-run, see README.
set -uo pipefail
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:/usr/local/bin:/usr/bin:/bin"
builtin cd "$(dirname "$0")/.."
mkdir -p out/repaint
exec >>out/repaint/night.log 2>&1
echo "== $(date '+%F %T') start"

# The per-tile command; scripts/local_tile.sh documents MODE, STRENGTH and STEPS.
REPAINT_CMD="${REPAINT_CMD:-MODE=img2img STRENGTH=0.75 STEPS=8 scripts/local_tile.sh {inp} {out}}"
start=$(date +%s)

fail() {
  echo "== $(date '+%F %T') failed: $1"
  telegram "Helenaveen overschilderen is mislukt: $1. Log: out/repaint/night.log op de Framework." || true
  exit 1
}

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
