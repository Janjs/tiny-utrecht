"""Stitch out/render/r{row}_c{col}.png into out/render_full.png (plus a 4K copy)."""

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
view = json.loads((ROOT / "render/view.json").read_text())
w, h = view["canvas_px"]
shot = view["shot_px"]

canvas = Image.new("RGB", (w, h))
for row in range(h // shot):
    for col in range(w // shot):
        canvas.paste(Image.open(ROOT / f"out/render/r{row}_c{col}.png").convert("RGB"), (col * shot, row * shot))
canvas.save(ROOT / "out/render_full.png")
for width, name in ((4096, "render_4k"), (1024, "render_preview")):
    canvas.resize((width, round(h * width / w)), Image.LANCZOS).save(ROOT / f"out/{name}.png")
print("stitched", canvas.size)
