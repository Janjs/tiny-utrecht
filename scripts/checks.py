"""Automatic checks for teacher frames.

soft_share: share of small pixel steps; photo shading has many (see SOFT_MAX in teacher.py).

flat_share: share of pixels whose 3x3 neighbourhood is flat. Pixel art is mostly
flat fills; a photo with a filter over it is not (tiny.london: redraws 0.42-0.55,
half-copies 0.18-0.35).

usage: checks.py <image.png> [...]
"""

import sys

import numpy as np
from PIL import Image, ImageFilter


def flat_share(img: str | Image.Image, tol: int = 6) -> float:
    img = Image.open(img) if isinstance(img, str) else img
    a = np.asarray(img.convert("RGB"), dtype=np.int16)
    h, w, _ = a.shape
    centre = a[1:-1, 1:-1]
    flat = np.ones((h - 2, w - 2), dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nb = a[1 + dy : h - 1 + dy, 1 + dx : w - 1 + dx]
            flat &= (np.abs(nb - centre) <= tol).all(axis=2)
    return float(flat.mean())


def soft_share(img: str | Image.Image) -> float:
    """Share of neighbouring-pixel steps that are small (3-12 levels): smooth photo shading.
    Pixel art is flat areas with hard steps between them, so it scores lower."""
    img = Image.open(img) if isinstance(img, str) else img
    a = np.asarray(img.convert("L"), dtype=np.int16)
    d = np.concatenate([np.abs(np.diff(a, axis=0)).ravel(), np.abs(np.diff(a, axis=1)).ravel()])
    return float(((d >= 3) & (d <= 12)).mean())


def blank_share(img: Image.Image) -> float:
    """Share of the view inside large near-white flat areas (holes the model left blank)."""
    a = np.asarray(img.convert("RGB"), dtype=np.int16)
    white = (a.min(axis=2) > 225) & (a.max(axis=2) - a.min(axis=2) < 14)
    big = Image.fromarray(white.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(21))
    return float((np.asarray(big) > 127).mean())


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(f"flat {flat_share(p):.3f}  soft {soft_share(p):.3f}  {p}")
