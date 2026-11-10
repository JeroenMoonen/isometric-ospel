"""Hover areas for the viewer: the outline on screen of every named building, and a small disc for named points.

Polygons are in the render's screen meters (u right, v up from the image center line); the viewer turns them into
image pixels with map.json. Output: data/build/hotspots.json
"""

import json
import math

import numpy as np

from config import BUILD, CX, CY

COS30 = math.cos(math.radians(30))


def screen(x, y, z):
    """Local x east, y up, z south to screen meters, as in render/scene.js."""
    return np.stack([(x + z) / math.sqrt(2), (x - z) / (2 * math.sqrt(2)) + y * COS30], -1)


def hull(pts):
    pts = sorted(set(map(tuple, np.round(pts, 2))))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def main():
    lm = json.loads((BUILD / "landmarks.json").read_text())
    meta = json.loads((BUILD / "buildings.json").read_text())
    v = np.fromfile(BUILD / "buildings.bin", dtype=np.float32).reshape(-1, 12)
    parts = {}
    for i, m in enumerate(meta):
        parts.setdefault(str(m.get("id")).split("-")[0], []).append(i)
    out = []
    for h in lm["hotspots"]:
        if "pid" in h:
            sel = np.isin(v[:, 9], parts.get(h["pid"], []))
            if not sel.any():
                continue
            pts = screen(v[sel, 0], v[sel, 1], v[sel, 2])
        else:
            a = np.linspace(0, 2 * np.pi, 16, endpoint=False)
            x, z = h["x"] - CX + 5 * np.cos(a), CY - h["y"] + 5 * np.sin(a)
            pts = np.concatenate([screen(x, 0 * x, z), screen(x, 0 * x + 3, z)])
        out.append({"name": h["name"], "note": h.get("note"), "poly": [[round(float(p[0]), 2), round(float(p[1]), 2)] for p in hull(pts)]})
    (BUILD / "hotspots.json").write_text(json.dumps(out, ensure_ascii=False))
    print(f"{len(out)} hotspots")


if __name__ == "__main__":
    main()
