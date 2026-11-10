"""Shared settings: the area we render, in RD New (EPSG:28992) meters."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BUILD = ROOT / "data" / "build"

# Helenaveen with the Soemeersingel north to the Willem III-hoeve: 3.5 x 5.5 km.
XMIN, YMIN, XMAX, YMAX = 189850, 376350, 193350, 381850
CX, CY = (XMIN + XMAX) / 2, (YMIN + YMAX) / 2

# Downloads and ground textures come in square chunks of this many meters.
CHUNK = 500
NX, NY = int((XMAX - XMIN) / CHUNK), int((YMAX - YMIN) / CHUNK)

# Ground raster resolution in meters per pixel.
GROUND_RES = 0.25


def write_area():
    """The renderer and the viewer read the area from here."""
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "area.json").write_text(
        json.dumps({"xmin": XMIN, "ymin": YMIN, "xmax": XMAX, "ymax": YMAX, "cx": CX, "cy": CY, "chunk": CHUNK, "nx": NX, "ny": NY})
    )
