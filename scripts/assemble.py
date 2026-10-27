"""Blend the grid tiles from out/grid into one map image: out/map_full.png.

Neighbouring tiles overlap by ~170 px. Each tile owns the middle of its square; in the overlap
the two drawings cross-fade over FADE px, centred between the tile edges, so a difference
between neighbours fades out instead of ending in a straight line. The canvas border is not faded.

Then landmarks that Google's mesh gets wrong are patched in from hand-checked frames (the Dom
tower under scaffolding).

usage: assemble.py
"""

import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
GRID = ROOT / "out/grid"
VIEW = json.loads((ROOT / "render/view.json").read_text())
W, H = VIEW["canvas_px"]
TILE = 1024
FADE = 64
GRID_STRIDE = 896  # same as teacher.py

# (source frame, its top-left on the canvas, box inside the frame to copy)
PATCHES = [
    (ROOT / "out/frames_v4/dom_gemini.png", (4208, 2488), (490, 365, 598, 705)),
]


def ramp(n: int, fade_start: bool, fade_end: bool, margin: int) -> np.ndarray:
    """1-D weight across a tile: 0 in the outer `margin`, rising over FADE px, 1 in the middle."""
    i = np.arange(n, dtype=np.float32) + 0.5
    w = np.ones(n, dtype=np.float32)
    if fade_start:
        w = np.minimum(w, np.clip((i - margin) / FADE, 0, 1))
    if fade_end:
        w = np.minimum(w, np.clip((n - i - margin) / FADE, 0, 1))
    return w


def main() -> None:
    tiles = []
    for p in GRID.glob("g_r*_c*_gemini.png"):
        r, c = map(int, re.match(r"g_r(\d+)_c(\d+)_gemini", p.stem).groups())
        tiles.append((r, c, p))
    # tile positions exactly as teacher.py laid out the grid, whether or not every tile exists yet
    def starts(length: int) -> list[int]:
        n = math.ceil((length - TILE) / GRID_STRIDE) + 1
        return [round(i * (length - TILE) / (n - 1)) for i in range(n)]

    col_x, row_y = starts(W), starts(H)
    ncols, nrows = len(col_x), len(row_y)
    margin_x = ((TILE - (col_x[1] - col_x[0])) - FADE) // 2
    margin_y = ((TILE - (row_y[1] - row_y[0])) - FADE) // 2

    acc = np.zeros((H, W, 3), dtype=np.float32)
    wsum = np.zeros((H, W), dtype=np.float32)
    for r, c, p in tiles:
        x0, y0 = col_x[c], row_y[r]
        img = np.asarray(Image.open(p).convert("RGB").resize((TILE, TILE)), dtype=np.float32)
        wx = ramp(TILE, c > 0, c < ncols - 1, margin_x)
        wy = ramp(TILE, r > 0, r < nrows - 1, margin_y)
        w = wy[:, None] * wx[None, :]
        acc[y0:y0 + TILE, x0:x0 + TILE] += img * w[..., None]
        wsum[y0:y0 + TILE, x0:x0 + TILE] += w
    missing = wsum < 1e-6
    if missing.any():
        print(f"warning: {missing.mean():.2%} of the canvas has no tile; filled from the render")
        render = np.asarray(Image.open(ROOT / "out/render_full.png").convert("RGB"), dtype=np.float32)
        acc[missing] = render[missing]
        wsum[missing] = 1
    out = Image.fromarray(np.clip(acc / wsum[..., None], 0, 255).astype(np.uint8))
    del acc, wsum

    for src, (fx, fy), (x0, y0, x1, y1) in PATCHES:
        feather = 8
        frame = Image.open(src).convert("RGB")
        mask = Image.new("L", frame.size, 0)
        ImageDraw.Draw(mask).rectangle((x0 + feather, y0 + feather, x1 - feather, y1 - feather), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(feather / 2))
        region = out.crop((fx, fy, fx + frame.width, fy + frame.height))
        out.paste(Image.composite(frame, region, mask), (fx, fy))

    out.save(ROOT / "out/map_full.png")
    out.resize((1024, round(1024 * H / W)), Image.LANCZOS).save(ROOT / "out/map_preview.png")
    print("assembled", out.size, f"from {len(tiles)} tiles")


if __name__ == "__main__":
    Image.MAX_IMAGE_PIXELS = None
    main()
