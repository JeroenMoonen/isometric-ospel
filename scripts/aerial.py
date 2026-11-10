"""Aerial photo mosaic at GROUND_RES, with row 0 at the north edge."""

import numpy as np
from PIL import Image

from config import BUILD, GROUND_RES, RAW, XMAX, XMIN, YMAX, YMIN

CHUNK = 500


def load_aerial():
    cache = BUILD / "aerial.npy"
    if cache.exists():
        return np.load(cache)
    n = int((XMAX - XMIN) / CHUNK)
    px = int(CHUNK / GROUND_RES)
    out = np.zeros((n * px, n * px, 3), dtype=np.uint8)
    for ix in range(n):
        for iy in range(n):
            img = np.array(Image.open(RAW / "aerial" / f"{ix}_{iy}.jpg").convert("RGB"))
            row = (n - 1 - iy) * px
            out[row : row + px, ix * px : ix * px + px] = img
    BUILD.mkdir(parents=True, exist_ok=True)
    np.save(cache, out)
    return out


def world_to_px(xy):
    """RD meters (N,2) to fractional pixel coordinates (col, row) in the mosaic."""
    xy = np.asarray(xy, dtype=np.float64)
    return np.stack([(xy[:, 0] - XMIN) / GROUND_RES, (YMAX - xy[:, 1]) / GROUND_RES], axis=-1)
