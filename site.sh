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
# The buildings and trees once more, transparent elsewhere: the viewer lays them over the cars and walkers behind them.
objects="out/objects-$SCALE.png"
if [ -f "$objects" ]; then
  vips bandjoin "$full $objects" out/objects.v
  vips dzsave out/objects.v "$SITE/tiles-$stamp/objects" --tile-size 1024 --overlap 0 --suffix '.webp[Q=90]'
  rm -f out/objects.v "$SITE/tiles-$stamp/objects.dzi" "$SITE/tiles-$stamp/objects_files/vips-properties.xml"
fi
python3 - "$SCALE" "$stamp" "$SITE" <<'EOF'
import json, os, sys
scale, stamp, site = sys.argv[1:4]
m = json.load(open(f"out/tiles-{scale}/layout.json"))
m["tiles"] = f"tiles-{stamp}/helenaveen_files/"
if os.path.isdir(f"{site}/tiles-{stamp}/objects_files"):
    m["objects"] = f"tiles-{stamp}/objects_files/"
json.dump(m, open(f"{site}/map.json", "w"))
EOF
cp viewer/index.html data/build/places.json data/build/hotspots.json data/build/routes.json data/build/history.json data/build/traffic.json "$SITE/"
cp -r data/build/history "$SITE/history"
[ -d data/build/photos ] && cp -r data/build/photos "$SITE/photos"
touch "$SITE/.nojekyll"
echo "$SITE/ is ready from $full: $(find "$SITE" -type f | wc -l) files, $(du -sh "$SITE" | cut -f1)"
