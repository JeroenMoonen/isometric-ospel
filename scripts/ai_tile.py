# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=2"]
# ///
"""Repaint a rendered tile as hand-made pixel art with an OpenAI image model.

  uv run scripts/ai_tile.py <input.png> <output.png> [--model gpt-image-2.5-sunburst] [--mask mask.png]

The API key comes from the environment (OPENAI_API_KEY). Prints token usage and an estimated cost.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time

from openai import OpenAI

PROMPT = """Repaint this isometric map tile as detailed hand-made pixel art, in the style of a late-1990s isometric city-building game.

Keep the layout exactly: every building, roof, road, ditch, canal, tree, field and greenhouse stays at the same position, with the same size, shape, outline and orientation. Do not add, remove, move or merge any object. Keep the same camera angle and the same light direction (sun from the upper left). Keep the colors: red-brown brick walls, grey and dark roofs, terracotta roofs where they are red, pale glass greenhouses, green trees, blue water, the same field colors.

Add the hand-drawn detail a pixel artist would: brick courses and window frames on walls, doors, chimneys and dormers, roof tiles and ridge lines, solar panels on some dark roofs, garden fences, hedges and paths, a few parked cars on driveways and streets, tree crowns with clusters of leaves and highlights, grass with texture, furrows in fields, small ripples and reflections in the water.

Crisp pixel art with clean pixel edges and a limited, harmonious palette. No blur, no painterly brush strokes, no text, no labels, no borders."""

# USD per million tokens, from OpenAI's published GPT Image 2.5 rates.
PRICES = {"text_in": 5.0, "image_in": 8.0, "image_out": 30.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--model", default="gpt-image-2.5-sunburst")
    ap.add_argument("--mask")
    ap.add_argument("--quality", default="high")
    ap.add_argument("--prompt-extra", default="")
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY") or subprocess.check_output(
        ["secret", "OPENAI_API_KEY", "Isometric Helenaveen: repaint map tiles with an image model"], text=True
    ).strip()
    client = OpenAI(api_key=key)
    kwargs = dict(
        model=args.model,
        image=open(args.input, "rb"),
        prompt=PROMPT + ("\n\n" + args.prompt_extra if args.prompt_extra else ""),
        size="1024x1024",
        quality=args.quality,
    )
    if args.mask:
        kwargs["mask"] = open(args.mask, "rb")
    t0 = time.time()
    try:
        res = client.images.edit(**kwargs, input_fidelity="high")
    except Exception as e:  # noqa: BLE001
        if "input_fidelity" not in str(e):
            raise
        kwargs["image"].seek(0)
        res = client.images.edit(**kwargs)
    with open(args.output, "wb") as f:
        f.write(base64.b64decode(res.data[0].b64_json))
    u = res.usage.model_dump() if res.usage else {}
    det = u.get("input_tokens_details") or {}
    cost = (
        det.get("text_tokens", 0) * PRICES["text_in"]
        + det.get("image_tokens", 0) * PRICES["image_in"]
        + u.get("output_tokens", 0) * PRICES["image_out"]
    ) / 1e6
    print(json.dumps({"model": args.model, "seconds": round(time.time() - t0, 1), "usage": u, "est_usd": round(cost, 4)}))


if __name__ == "__main__":
    sys.exit(main())
