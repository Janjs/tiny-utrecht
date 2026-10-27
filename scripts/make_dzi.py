"""Cut out/map_full.png into a Deep Zoom pyramid for OpenSeadragon: site/map.dzi + site/map_files/.

The sharpest level is lossless WebP so the pixel art stays crisp at full zoom; the smaller
levels, which are only seen zoomed out, are lossy.

usage: make_dzi.py
"""

import math
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out/map_full.png"
OUT = ROOT / "site"
TILE = 1024


def main() -> None:
    img = Image.open(SRC).convert("RGB")
    w, h = img.size
    top = math.ceil(math.log2(max(w, h)))
    files = OUT / "map_files"
    shutil.rmtree(files, ignore_errors=True)
    count = 0
    for level in range(top, -1, -1):
        scale = 2 ** (top - level)
        lw, lh = math.ceil(w / scale), math.ceil(h / scale)
        im = img if scale == 1 else img.resize((lw, lh), Image.LANCZOS)
        d = files / str(level)
        d.mkdir(parents=True)
        for row in range(math.ceil(lh / TILE)):
            for col in range(math.ceil(lw / TILE)):
                tile = im.crop((col * TILE, row * TILE, min((col + 1) * TILE, lw), min((row + 1) * TILE, lh)))
                if level == top:
                    tile.save(d / f"{col}_{row}.webp", lossless=True, method=4)
                else:
                    tile.save(d / f"{col}_{row}.webp", quality=88, method=4)
                count += 1
    (OUT / "map.dzi").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" TileSize="{TILE}" Overlap="0" Format="webp">'
        f'<Size Width="{w}" Height="{h}"/></Image>\n'
    )
    size = sum(p.stat().st_size for p in files.rglob("*.webp"))
    print(f"{count} tiles, {size / 1e6:.1f} MB, levels 0-{top}")


if __name__ == "__main__":
    Image.MAX_IMAGE_PIXELS = None
    main()
