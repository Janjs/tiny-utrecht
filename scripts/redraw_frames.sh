#!/bin/sh
# Redraw every out/frames/*_render.png in parallel, then score and build a contact sheet.
cd "$(dirname "$0")/.." || exit 1
for r in out/frames/*_render.png; do
  uv run --with pillow --with google-genai python scripts/gemini_redraw.py "$r" "${r%_render.png}_gemini.png" 1:1 1K 2>&1 | grep -E "saved|text:|Error" &
done
wait
uv run --with pillow --with numpy python scripts/checks.py out/frames/*_gemini.png
uv run --with pillow python scripts/contact_sheet.py
