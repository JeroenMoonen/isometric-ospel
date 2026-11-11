#!/usr/bin/env bash
# Build the isometric map of Helenaveen from open data, end to end.
#   ./build.sh            fetch, preprocess, render at 4 px/m, cut Deep Zoom tiles into site/
#   SCALE=3 ./build.sh    render at another resolution (update SCALE/WIDTH/HEIGHT in viewer/index.html to match)
set -euo pipefail
builtin cd "$(dirname "$0")"
SCALE="${SCALE:-4}"

(builtin cd scripts && python3 fetch.py)
(builtin cd scripts && uv run --quiet landmarks.py)
(builtin cd scripts && uv run --quiet build_buildings.py)
(builtin cd scripts && uv run --quiet build_trees.py 2>&1 | grep -v GDAL_NODATA)
(builtin cd scripts && uv run --quiet build_ground.py)
(builtin cd scripts && python3 build_places.py)
(builtin cd scripts && uv run --quiet --with numpy python build_hotspots.py)
(builtin cd scripts && python3 build_routes.py)
(builtin cd scripts && uv run --quiet build_traffic.py)
(builtin cd scripts && python3 build_history.py)

[ -d node_modules ] || bun install
node render/run.mjs all --scale "$SCALE" --tile 2048 --kuwahara 2
# The mask of buildings and trees, which the viewer draws again over the cars and walkers behind them.
node render/run.mjs all --scale "$SCALE" --tile 2048 --pass objects

layout="out/tiles-$SCALE/layout.json"
read -r W H C < <(python3 -c "import json; d=json.load(open('$layout')); print(d['width'], d['height'], d['cols'])")
join() {  # tile folder, output image, bands to keep
  vips arrayjoin "$(/bin/ls "$1"/*.png | tr '\n' ' ')" out/joined.v --across "$C"
  vips extract_area out/joined.v out/cropped.v 0 0 "$W" "$H"
  vips extract_band out/cropped.v "$2[compression=1]" 0 --n "$3"
  rm -f out/joined.v out/cropped.v
}
join "out/tiles-$SCALE" "out/full-$SCALE.png" 3
join "out/tiles-$SCALE-objects" "out/objects-$SCALE.png" 1

./site.sh
