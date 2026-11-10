# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""Repaint the whole rendered map with a local image model, tile by tile, and blend the tiles back together.

  uv run scripts/repaint_map.py [--scale 4] [--cmd 'MODE=img2img STRENGTH=0.75 scripts/local_tile.sh {inp} {out}']
                                [--limit N] [--only-blend]

A command with {height} also gets the matching crop of out/full-<scale>-height.png (render/run.mjs --pass height),
for ControlNet: --cmd 'scripts/controlnet_tile.sh {inp} {height} {out}'.

Tiles are 1024 px with 128 px of overlap; in the overlap the two tiles fade into each other, so there are no seams.
Tiles that are (almost) only the empty space around the map are skipped. Finished tiles are kept in
out/repaint/, so a stopped run picks up where it left off. The result is out/full-<scale>-ai.png; build.sh uses it
when USE_AI=1.
"""

import argparse
import shlex
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
TILE, OVERLAP = 1024, 128
BACKGROUND = np.array((0x20, 0x24, 0x2C), np.uint8)  # the void around the map, see render/scene.js

Image.MAX_IMAGE_PIXELS = None


def grid(size):
    stride = TILE - OVERLAP
    starts = list(range(0, max(size - TILE, 0) + 1, stride))
    if starts[-1] + TILE < size:
        starts.append(size - TILE)
    return starts


def feather(h, w):
    """Weight mask: 1 in the middle, fading linearly to 0 across the overlap at each edge."""
    ramp = lambda n: np.clip(np.minimum(np.arange(n) + 0.5, n - np.arange(n) - 0.5) / OVERLAP, 0, 1)
    return np.outer(ramp(h), ramp(w)).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="4")
    ap.add_argument("--cmd", default="MODE=img2img STRENGTH=0.75 scripts/local_tile.sh {inp} {out}")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many new tiles (for a trial run)")
    ap.add_argument("--only-blend", action="store_true", help="don't run the model, just blend what is there")
    args = ap.parse_args()

    src = ROOT / "out" / f"full-{args.scale}.png"
    full = np.array(Image.open(src).convert("RGB"))
    H, W = full.shape[:2]
    work = ROOT / "out" / "repaint"
    (work / "in").mkdir(parents=True, exist_ok=True)
    (work / "out").mkdir(parents=True, exist_ok=True)
    height = None
    if "{height}" in args.cmd:
        height = np.array(Image.open(ROOT / "out" / f"full-{args.scale}-height.png").convert("RGB"))
        assert height.shape == full.shape, "the height pass must be rendered at the same scale as the color image"
        (work / "height").mkdir(parents=True, exist_ok=True)

    tiles = []
    for y in grid(H):
        for x in grid(W):
            crop = full[y : y + TILE, x : x + TILE]
            empty = np.all(crop == BACKGROUND, axis=-1).mean()
            if empty < 0.97:
                tiles.append((x, y))
    print(f"{len(tiles)} tiles with map content (of {len(grid(H)) * len(grid(W))}) for a {W} x {H} image", flush=True)

    if not args.only_blend:
        todo = [(x, y) for x, y in tiles if not (work / "out" / f"{y:05d}_{x:05d}.png").exists()]
        t0, done = time.time(), 0
        for x, y in todo:
            if args.limit and done >= args.limit:
                break
            inp = work / "in" / f"{y:05d}_{x:05d}.png"
            out = work / "out" / f"{y:05d}_{x:05d}.png"
            Image.fromarray(full[y : y + TILE, x : x + TILE]).save(inp)
            hpath = work / "height" / f"{y:05d}_{x:05d}.png"
            if height is not None:
                Image.fromarray(height[y : y + TILE, x : x + TILE]).save(hpath)
            cmd = args.cmd.format(inp=shlex.quote(str(inp)), out=shlex.quote(str(out)), height=shlex.quote(str(hpath)))
            res = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
            if res.returncode != 0 or not out.exists():
                print(f"tile {x},{y} failed:\n{res.stderr[-2000:]}", file=sys.stderr, flush=True)
                continue
            done += 1
            per = (time.time() - t0) / done
            left = len(todo) - done if not args.limit else min(args.limit, len(todo)) - done
            print(f"{done}/{len(todo)} tiles, {per:.0f} s per tile, about {left * per / 3600:.1f} h left", flush=True)

    acc = np.zeros((H, W, 3), np.float32)
    wsum = np.zeros((H, W), np.float32)
    mask = feather(TILE, TILE)
    used = 0
    for x, y in tiles:
        f = work / "out" / f"{y:05d}_{x:05d}.png"
        if not f.exists():
            continue
        img = np.array(Image.open(f).convert("RGB").resize((TILE, TILE), Image.LANCZOS), np.float32)
        acc[y : y + TILE, x : x + TILE] += img * mask[..., None]
        wsum[y : y + TILE, x : x + TILE] += mask
        used += 1
    # Where no repainted tile reaches (the empty corners, or tiles not done yet), keep the original render.
    covered = wsum > 0.05
    result = full.copy()
    result[covered] = np.clip(acc[covered] / wsum[covered, None], 0, 255).astype(np.uint8)
    # The void around the map stays exactly the background color.
    result[np.all(full == BACKGROUND, axis=-1)] = BACKGROUND
    dst = ROOT / "out" / f"full-{args.scale}-ai.png"
    Image.fromarray(result).save(dst, compress_level=1)
    print(f"blended {used} tiles into {dst}", flush=True)


if __name__ == "__main__":
    main()
