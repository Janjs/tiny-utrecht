"""Copy a rectangle from one drawn frame into another with a feathered edge.

usage: patch_region.py <from.png> <into.png> <out.png> x0 y0 x1 y1 [feather_px]
"""

import sys

from PIL import Image, ImageDraw, ImageFilter

src, dst, out, *nums = sys.argv[1:]
x0, y0, x1, y1 = map(int, nums[:4])
feather = int(nums[4]) if len(nums) > 4 else 8
a, b = Image.open(src).convert("RGB"), Image.open(dst).convert("RGB")
mask = Image.new("L", b.size, 0)
ImageDraw.Draw(mask).rectangle((x0 + feather, y0 + feather, x1 - feather, y1 - feather), fill=255)
Image.composite(a, b, mask.filter(ImageFilter.GaussianBlur(feather / 2))).save(out)
