"""Redraw a render as isometric pixel art with Gemini.

usage: gemini_redraw.py <input.png> <output.png> [aspect_ratio] [image_size]
"""

import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))

MODEL = "gemini-3-pro-image-preview"
STYLE_REFS = [ROOT / "refs/style_station_v2.png"]

PROMPT = """The first image is an orthographic 3D render of part of Utrecht, seen from above at 45 degrees.
The second image is a STYLE reference only. Copy how it is drawn, never what is in it.

Redraw the first image as isometric pixel art, in exactly the style of the reference.

HOW TO DRAW:
- Pixel art, like a late-90s city-building game: every surface is a flat area of colour with
  hard pixel edges. Shade each surface with two or three flat tones and a little ordered dithering.
- No photo texture, no noise, no blur, no gradients, no painterly or brush strokes.
- Edges are thin: one or two pixels, a darker tone of the surface colour. Never thick black outlines.
- Roof tiles, windows and solar panels are small regular pixel patterns, not photo detail.
- Trees are rounded clumps built from three flat greens. Grass is flat green with sparse dithering.
- Streets and squares are flat warm grey or brick, with simple pixel paving where the render shows it.
- COLOUR: keep the render's true colours and white balance, in neutral daylight. Grey roofs stay
  neutral grey, white stays white, slate stays blue-grey, glass stays blue. No warm, yellow, orange,
  brown or sepia tint over the image. Do not make it darker or more saturated than the render.
- The whole image is drawn with the same care. Busy parts are not allowed to stay photographic.

FIDELITY COMES FIRST:
1. Draw exactly what the render shows, in the same positions, shapes and sizes, seen from the same camera.
2. Add nothing that is not in the render and remove nothing that is.
3. Where the render shows little detail, keep the drawing just as plain. Little detail in the
   render means little detail in the drawing, never new objects.
4. Do not draw cars, buses, bikes, boats or people.

Water keeps the colour the render shows for it: the canals and ponds here are dark grey-green,
never bright or sky blue. Draw it as a flat area of that colour with a few slightly lighter pixel ripples.
{water}

Return one image with exactly the same framing as the first image."""


def redraw(
    render: Image.Image, water: str, extra: list[Image.Image] | None = None, aspect: str = "1:1", size: str = "1K"
) -> tuple[bytes | None, str]:
    """Returns (image bytes or None, any text the model sent back). `extra` images go last."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = [render, PROMPT.format(water=water), *[Image.open(p) for p in STYLE_REFS], *(extra or [])]
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(aspect_ratio=aspect, image_size=size),
    )
    for wait in (40, 60, 90, 120, 0):  # Tier 1 allows 20 image requests a minute
        try:
            resp = client.models.generate_content(model=MODEL, contents=contents, config=config)
            break
        except errors.ClientError as e:
            if e.code != 429 or not wait:
                raise
            time.sleep(wait)
    data, text = None, ""
    for part in resp.candidates[0].content.parts:
        if part.inline_data:
            data = part.inline_data.data
        elif part.text:
            text += part.text
    return data, text


if __name__ == "__main__":
    src, dst, *rest = sys.argv[1:]
    data, text = redraw(Image.open(src), "Draw water only where the render clearly shows water.", None, *rest)
    if data:
        Path(dst).write_bytes(data)
    print(text or f"saved {dst}")
