"""Contact sheet: renders on the top row, teacher frames below -> out/frames/sheet.png"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
renders = sorted((ROOT / "out/frames").glob("*_render.png"))
tile = 512
sheet = Image.new("RGB", (tile * len(renders), tile * 2))
for i, r in enumerate(renders):
    sheet.paste(Image.open(r).convert("RGB").resize((tile, tile)), (i * tile, 0))
    g = r.with_name(r.name.replace("_render", "_gemini"))
    if g.exists():
        sheet.paste(Image.open(g).convert("RGB").resize((tile, tile)), (i * tile, tile))
sheet.save(ROOT / "out/frames/sheet.png")
