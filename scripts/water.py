"""OpenStreetMap water for the canvas: a full-canvas mask, per-frame sentences and a check.

usage: water.py mask            -> out/water_mask.png and out/water_overlay.png
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
VIEW = json.loads((ROOT / "render/view.json").read_text())
W, H = VIEW["canvas_px"]


def _join(parts: list[list[list[float]]]) -> list[list[list[float]]]:
    """Join open way segments of a multipolygon relation into closed rings."""
    rings, open_ = [], [p[:] for p in parts]
    while open_:
        cur = open_.pop(0)
        while cur[0] != cur[-1]:
            for i, p in enumerate(open_):
                if p[0] == cur[-1]:
                    cur += p[1:]
                elif p[-1] == cur[-1]:
                    cur += p[::-1][1:]
                else:
                    continue
                open_.pop(i)
                break
            else:
                break  # unclosed; fill it as is
        rings.append(cur)
    return rings


def canvas_mask() -> Image.Image:
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    polys = json.loads((ROOT / "data/water_px.json").read_text())
    for p in polys:
        for r in _join(p["outer"]):
            if len(r) > 2:
                draw.polygon([tuple(x) for x in r], fill=255)
    for p in polys:
        for r in _join(p["inner"]):
            if len(r) > 2:
                draw.polygon([tuple(x) for x in r], fill=0)
    return mask


def frame_mask(cx: int, cy: int, size: int = 1024) -> Image.Image:
    return Image.open(ROOT / "out/water_mask.png").crop((cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2))


def sentence(mask: Image.Image) -> str:
    """One sentence saying how much of the view is water and where."""
    a = np.asarray(mask) > 127
    share = a.mean()
    if share < 0.002:
        return "WATER IN THIS VIEW: none. Nothing in this view is water, so nothing in it uses the water colour."
    h, w = a.shape
    names = [["top left", "top", "top right"], ["left", "centre", "right"], ["bottom left", "bottom", "bottom right"]]
    where = [names[r][c] for r in range(3) for c in range(3)
             if a[r * h // 3:(r + 1) * h // 3, c * w // 3:(c + 1) * w // 3].mean() > 0.01]
    return (f"WATER IN THIS VIEW: about {share * 100:.0f}% of the view, in the {', '.join(where)}: "
            "only the canals, moat or ponds that the render shows there. Nothing else uses the water colour.")


def water_colour(img: Image.Image, mask: Image.Image) -> np.ndarray | None:
    """Median colour inside the OSM water, away from its edges; None if there is too little water."""
    inside = np.asarray(mask.filter(ImageFilter.MinFilter(9))) > 127
    if inside.sum() < 500:
        return None
    return np.median(np.asarray(img.convert("RGB"), dtype=np.float32)[inside], axis=0)


def water_colour_error(drawn: Image.Image, render: Image.Image, mask: Image.Image) -> float:
    """Distance (RGB levels) between the drawn water colour and the render's; 0 when there is no water."""
    d, r = water_colour(drawn, mask), water_colour(render, mask)
    return 0.0 if d is None or r is None else float(np.linalg.norm(d - r))


def invented_water(drawn: Image.Image, mask: Image.Image) -> float:
    """Share of the view drawn as water where OSM says there is none (with a 12 px margin).

    Water is whatever is drawn in a bright blue, or in this drawing's own water colour as a flat area.
    Areas narrower than 9 px (solar panels, glass) are ignored."""
    a = np.asarray(drawn.convert("RGB"), dtype=np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    wet = (b - r > 60) & (b - g > 15)
    own = water_colour(drawn, mask)
    if own is not None:
        close = np.linalg.norm(a - own, axis=2) < 14
        flat = np.asarray(drawn.convert("L").filter(ImageFilter.Kernel((3, 3), [-1] * 4 + [8] + [-1] * 4, 1, 0))) < 6
        wet |= close & flat
    blobs = Image.fromarray(wet.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(9))
    near = np.asarray(mask.filter(ImageFilter.MaxFilter(25))) > 127
    return float(((np.asarray(blobs) > 127) & ~near).mean())


if __name__ == "__main__" and sys.argv[1:] == ["mask"]:
    m = canvas_mask()
    m.save(ROOT / "out/water_mask.png")
    small = (1024, round(1024 * H / W))
    render = Image.open(ROOT / "out/render_full.png").convert("RGB").resize(small)
    blue = Image.new("RGB", small, (0, 120, 255))
    Image.composite(blue, render, m.resize(small).point(lambda v: v * 0.6)).save(ROOT / "out/water_overlay.png")
    print("water share of canvas:", round((np.asarray(m) > 127).mean(), 4))
