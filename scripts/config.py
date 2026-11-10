"""Shared settings: the area we render, in RD New (EPSG:28992) meters."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BUILD = ROOT / "data" / "build"

# 3 x 3 km around the village core of Helenaveen.
XMIN, YMIN, XMAX, YMAX = 190350, 376350, 193350, 379350
CX, CY = (XMIN + XMAX) / 2, (YMIN + YMAX) / 2

# Ground raster resolution in meters per pixel.
GROUND_RES = 0.25
