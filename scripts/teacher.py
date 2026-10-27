"""Teacher frames: crop render + OSM water, redraw with Gemini, run the checks.

usage: teacher.py <out_dir> [--quarters | --grid] [frame ...]
  default: every frame in FRAMES, each as one 1024 px pair.
  --quarters: each 512 px quarter is zoomed 2x, redrawn, and scaled back to a 512 px pair.
              On dense frames the teacher copies the photo; on a zoomed quarter it redraws.
  --grid: 1024 px tiles covering the whole canvas with overlap, for the full map (g_r{row}_c{col}).
          Resumable: a tile with a <tile>.done file is skipped.

A tile that fails a check is redrawn, up to ATTEMPTS times, then dropped.
Writes <out_dir>/report.txt.
"""

import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from checks import blank_share, flat_share, soft_share
from gemini_redraw import redraw
from water import frame_mask, invented_water, sentence, water_colour_error

ROOT = Path(__file__).resolve().parent.parent
RENDER = Image.open(ROOT / "out/render_full.png").convert("RGB")

# name -> frame centre in canvas pixels
FRAMES = {
    "dom": (4720, 3000),
    "oudegracht": (4480, 4100),
    "station": (2000, 2960),
    "residential": (7000, 2100),
    "park": (6950, 700),
    "lombok": (900, 1700),
    "oost": (7200, 5200),
    "wilhelminapark": (8800, 4640),
}

ATTEMPTS = 3
FLAT_MIN = 0.15  # below this the drawing is a filtered photo
SOFT_MAX = 0.31  # above this too many pixel steps are small, smooth photo shading
WATER_MAX = 0.003  # share of the view drawn as water where OSM has none
BLUE_MIN = 0.92  # drawn blue/red balance relative to the render's; lower is a warm tint
BLANK_MAX = 0.01  # extra share of large blank white areas compared with the render
WATER_COLOUR_MAX = 75  # RGB distance between drawn and rendered water colour (shaded ponds render near black)
GRID_STRIDE = 896  # at most this far between tile origins, so neighbours overlap by 128 px or more


def blue_balance(drawn: Image.Image, render: Image.Image) -> float:
    d = np.asarray(drawn.convert("RGB"), dtype=np.float32).reshape(-1, 3).mean(0)
    r = np.asarray(render, dtype=np.float32).reshape(-1, 3).mean(0)
    return float((d[2] / d[0]) / (r[2] / r[0]))


def tiles(name: str, quarters: bool) -> list[tuple[str, tuple[int, int, int, int]]]:
    """(tile name, crop box in canvas pixels) for a frame."""
    cx, cy = FRAMES[name]
    if not quarters:
        return [(name, (cx - 512, cy - 512, cx + 512, cy + 512))]
    return [
        (f"{name}_q{i}", (cx - 512 + qx, cy - 512 + qy, cx + qx, cy + qy))
        for i, (qx, qy) in enumerate([(0, 0), (512, 0), (0, 512), (512, 512)])
    ]


def grid_tiles() -> list[tuple[str, tuple[int, int, int, int]]]:
    """Overlapping 1024 px tiles from edge to edge of the canvas."""
    view = json.loads((ROOT / "render/view.json").read_text())
    w, h = view["canvas_px"]

    def starts(length: int) -> list[int]:
        n = math.ceil((length - 1024) / GRID_STRIDE) + 1
        return [round(i * (length - 1024) / (n - 1)) for i in range(n)]

    return [
        (f"g_r{r}_c{c}", (x, y, x + 1024, y + 1024))
        for r, y in enumerate(starts(h))
        for c, x in enumerate(starts(w))
    ]


def attempt(tile: str, box: tuple[int, int, int, int], out: Path, n: int) -> str:
    size = box[2] - box[0]
    render = RENDER.crop(box)
    mask = frame_mask((box[0] + box[2]) // 2, (box[1] + box[3]) // 2, size)
    render.save(out / f"{tile}_render.png")
    # the teacher always works at 1024 px; a 512 px quarter is shown zoomed in 2x
    data, text = redraw(render.resize((1024, 1024), Image.LANCZOS), sentence(mask))
    if data is None:
        return f"{tile:14s} #{n} NO IMAGE {text[:200]}"
    drawn_1k = Image.open(BytesIO(data)).convert("RGB").resize((1024, 1024))
    if n > 1:
        (out / f"{tile}_gemini.png").rename(out / f"{tile}_gemini_try{n - 1}.png")
    drawn = drawn_1k.resize((size, size), Image.LANCZOS)
    drawn.save(out / f"{tile}_gemini.png")
    pair = Image.new("RGB", (2 * size, size))
    pair.paste(render, (0, 0))
    pair.paste(drawn, (size, 0))
    pair.save(out / f"{tile}_compare.png")
    # style checks look at what the teacher drew, at the scale it drew it
    flat, soft = flat_share(drawn_1k), soft_share(drawn_1k)
    wet, blue = invented_water(drawn, mask), blue_balance(drawn, render)
    blank = blank_share(drawn) - blank_share(render)
    wcol = water_colour_error(drawn, render, mask)
    checks = (
        ("water-colour", wcol > WATER_COLOUR_MAX),
        ("photo-copy", flat < FLAT_MIN or soft > SOFT_MAX),
        ("invented-water", wet > WATER_MAX),
        ("warm-tint", blue < BLUE_MIN),
        ("blank-area", blank > BLANK_MAX),
    )
    fails = [f for f, bad in checks if bad]
    return (f"{tile:14s} #{n} flat {flat:.3f}  soft {soft:.3f}  invented water {wet:.4f}  blue {blue:.2f}  "
            f"blank {blank:+.3f}  water colour {wcol:.0f}  {'PASS' if not fails else 'FAIL ' + ','.join(fails)}")


def run(tile: str, box: tuple[int, int, int, int], out: Path) -> str:
    done = out / f"{tile}.done"
    if done.exists():
        return done.read_text()
    lines = []
    for n in range(1, ATTEMPTS + 1):
        lines.append(attempt(tile, box, out, n))
        if lines[-1].endswith("PASS"):
            break
    else:
        lines.append(f"{tile:14s} DROPPED after {ATTEMPTS} attempts")
    done.write_text("\n".join(lines))
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    out = ROOT / args.pop(0)
    quarters = "--quarters" in args
    names = [a for a in args if not a.startswith("--")] or list(FRAMES)
    jobs = grid_tiles() if "--grid" in args else [t for name in names for t in tiles(name, quarters)]
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(min(len(jobs), 4)) as pool, open(out / "report.txt", "a") as report:
        futures = [pool.submit(run, *j, out) for j in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            lines = fut.result()
            report.write(lines + "\n")
            report.flush()
            print(f"[{i}/{len(jobs)}] " + lines.splitlines()[-1], flush=True)
