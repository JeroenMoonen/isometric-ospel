#!/usr/bin/env bash
# Cut the rendered map into a Deep Zoom pyramid and assemble site/, without rendering anything.
#   ./site.sh              from out/full-4.png
# Every run writes the tiles to a fresh folder (tiles-<stamp>/), named in map.json, so browsers never mix cached
# tiles of an older version with a new one.
set -euo pipefail
builtin cd "$(dirname "$0")"
SCALE="${SCALE:-4}"
SITE=site

full="out/full-$SCALE.png"
stamp=$(date +%Y%m%d-%H%M%S)

rm -rf "$SITE" && mkdir -p "$SITE/tiles-$stamp"
vips dzsave "$full" "$SITE/tiles-$stamp/helenaveen" --tile-size 1024 --overlap 0 --suffix '.webp[Q=90]'
rm -f "$SITE/tiles-$stamp/helenaveen.dzi" "$SITE/tiles-$stamp/helenaveen_files/vips-properties.xml"
python3 - "$SCALE" "$stamp" "$SITE" <<'EOF'
import json, sys
scale, stamp, site = sys.argv[1:4]
m = json.load(open(f"out/tiles-{scale}/layout.json"))
m["tiles"] = f"tiles-{stamp}/helenaveen_files/"
json.dump(m, open(f"{site}/map.json", "w"))
EOF
cp viewer/index.html data/build/places.json data/build/hotspots.json data/build/routes.json data/build/history.json "$SITE/"
cp -r data/build/history "$SITE/history"
touch "$SITE/.nojekyll"
echo "$SITE/ is ready from $full: $(find "$SITE" -type f | wc -l) files, $(du -sh "$SITE" | cut -f1)"
