# Isometric Helenaveen

A zoomable isometric pixel-art map of 3 × 3 km around Helenaveen, in the spirit of [isometric.nyc](https://cannoneyed.com/projects/isometric-nyc). Where that project painted every tile with a fine-tuned image model, this one is rendered procedurally from Dutch open data, so it is exact, seamless and rebuilds in about two minutes.

## Pipeline

Run `./build.sh` for everything. The steps:

1. `scripts/fetch.py` downloads the raw data into `data/raw/`: 3D BAG buildings (LoD2.2 with roof shapes), BGT surfaces (roads, water, plots, vegetation), the PDOK aerial photo at 25 cm and AHN surface and terrain heights at 50 cm.
2. `scripts/landmarks.py` names the places people look for: both churches, the parsonage and Sunday school of 1867, school De Peelparel, monuments, the sports park. It gives them their real colors (from Rijksmonumenten photos) and adds what 3D BAG smooths away, like the 26 m tower of the Sint-Willibrorduskerk and the roof turret of the Protestant church, both measured in AHN. `scripts/build_buildings.py` triangulates the 3D BAG solids and samples a roof color per building from the aerial photo. 3D BAG cannot reconstruct greenhouses (lidar goes through glass), so those are extruded from their footprint with a gutter height based on the year of construction. Water tanks, feed silos and sheds come from the BGT.
3. `scripts/build_trees.py` finds individual trees in the canopy height model (AHN surface minus terrain): local maxima for the tops, watershed segmentation for crown size, and the spring aerial photo to tell evergreens from deciduous trees. Municipal street trees from the BGT fill in what the lidar missed.
4. `scripts/build_ground.py` paints the BGT polygons, plus football and tennis lines, the riding arenas and both graveyards from OpenStreetMap, in a fixed palette with patterns (furrows along each field's long axis, paving grids, ripples, a dark far bank on every ditch) and bakes hard sun shadows of the buildings and tree crowns into it.
5. `render/scene.js` is a three.js scene with a 2:1 isometric orthographic camera. Window grids, brick plinths, metal cladding and greenhouse glass are drawn in the building shader, and a post pass inks every depth step as an outline. `render/run.mjs` renders it in headless Chromium on the GPU (Vulkan), tile by tile with a view offset, so tiles line up exactly.
6. `vips dzsave` cuts the stitched image into a Deep Zoom pyramid of WebP tiles, and `viewer/index.html` shows it with OpenSeadragon: tilt-shift blur, RD and GPS coordinates under the cursor, and a search box over every place and address (`scripts/build_places.py`). A link ending in `#Sint-Willibrorduskerk` or `#De-Peelparel` opens on that place.

`./deploy.sh` publishes `site/` to the `gh-pages` branch as a single fresh commit, so the tiles never pile up in the history of `main`.

The camera looks north-east and the sun comes from the west-south-west (`scripts/sun.py`, mirrored in `render/scene.js`).

## Iterating

`node render/run.mjs crop <x> <y> <w> <h> --scale 4 --out out/crop.png` renders one region of the full image in a second, which is the fastest way to try a shader or palette change. `node render/run.mjs crop 0 0 2546 1303 --scale 0.6` gives an overview of the whole map.

## Data

3D BAG (TU Delft, 3DGI, CC BY 4.0), BGT (CC0), AHN (CC0), BAG addresses and the aerial photo (Beeldmateriaal Nederland, CC BY 4.0), all via [PDOK](https://www.pdok.nl). Points of interest, pitches and graveyards from OpenStreetMap (ODbL). Building descriptions from Monumenten in Nederland: Noord-Brabant (1997).
