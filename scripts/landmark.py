"""Redraw a landmark frame with a photo of how the landmark really looks.

Google's mesh can be out of date (the Dom tower is under scaffolding in it). The frame is
redrawn with the photo as a reference for that one building; everything else follows the render.

usage: landmark.py <frame> <photo> "<what the photo shows>" <out_dir>
  e.g. landmark.py dom refs/dom_tower.jpg "the Dom tower, the tall stone church tower in the centre" out/landmarks
"""

import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from gemini_redraw import PROMPT, STYLE_REFS, redraw
from teacher import FRAMES, RENDER
from water import frame_mask, sentence

ROOT = Path(__file__).resolve().parent.parent

LANDMARK = """
LANDMARK: in the render, {what} is shown wrongly (out-of-date 3D data: scaffolding or a plain block).
The last image is a photo of how it really looks. Draw that one building as in the photo,
seen from the same 45 degree camera, at the same position, footprint and height as in the render,
in the same pixel-art style as everything else. Everything else follows the render exactly."""


def main(frame: str, photo: str, what: str, out_dir: str) -> None:
    out = ROOT / out_dir
    out.mkdir(parents=True, exist_ok=True)
    cx, cy = FRAMES[frame]
    render = RENDER.crop((cx - 512, cy - 512, cx + 512, cy + 512))
    water = sentence(frame_mask(cx, cy)) + LANDMARK.format(what=what)
    data, text = redraw(render, water, extra=[Image.open(ROOT / photo)])
    if data is None:
        sys.exit(f"no image: {text}")
    drawn = Image.open(BytesIO(data)).convert("RGB").resize((1024, 1024))
    drawn.save(out / f"{frame}_landmark.png")
    pair = Image.new("RGB", (2048, 1024))
    pair.paste(render, (0, 0))
    pair.paste(drawn, (1024, 0))
    pair.save(out / f"{frame}_landmark_compare.png")
    print("saved", out / f"{frame}_landmark.png")


if __name__ == "__main__":
    main(*sys.argv[1:])
