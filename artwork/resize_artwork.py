#!/usr/bin/env python3
"""Resize TheSignal.png into all needed artwork assets."""

from PIL import Image
import os

SRC = "/agent/work/podcast/artwork/TheSignal.png"
OUT = "/agent/work/podcast/artwork"

img = Image.open(SRC).convert("RGBA")

# --- Cover art (with text) ---
cover_3000 = img.resize((3000, 3000), Image.LANCZOS)
cover_3000.save(os.path.join(OUT, "cover-3000.png"), "PNG", optimize=True)
print("cover-3000.png (3000x3000)")

cover_1400 = img.resize((1400, 1400), Image.LANCZOS)
cover_1400.save(os.path.join(OUT, "cover-1400.png"), "PNG", optimize=True)
print("cover-1400.png (1400x1400)")

# --- Icon version (crop center, above the text) ---
# The Bitcoin symbol + waves occupy roughly the top 55% of the image
# Crop a square from the top-center that captures the icon without text
w, h = img.size
icon_bottom = int(h * 0.54)  # cut below the waves, above "THE SIGNAL"
icon_crop = img.crop((0, 0, w, icon_bottom))
# Make it square by padding or centering
icon_size = max(icon_crop.size)
icon_square = Image.new("RGBA", (icon_size, icon_size), (13, 17, 23, 255))
paste_x = (icon_size - icon_crop.width) // 2
paste_y = (icon_size - icon_crop.height) // 2
icon_square.paste(icon_crop, (paste_x, paste_y), icon_crop if icon_crop.mode == "RGBA" else None)

icon_512 = icon_square.resize((512, 512), Image.LANCZOS)
icon_512.save(os.path.join(OUT, "icon-512.png"), "PNG", optimize=True)
print("icon-512.png (512x512)")

icon_192 = icon_square.resize((192, 192), Image.LANCZOS)
icon_192.save(os.path.join(OUT, "icon-192.png"), "PNG", optimize=True)
print("icon-192.png (192x192)")

icon_32 = icon_square.resize((32, 32), Image.LANCZOS)
icon_32.save(os.path.join(OUT, "favicon.png"), "PNG", optimize=True)
print("favicon.png (32x32)")

print("\nAll assets:")
for f in sorted(os.listdir(OUT)):
    if f.endswith(('.png', '.svg')):
        fpath = os.path.join(OUT, f)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  {f:20s} {size_kb:>8.1f} KB")
