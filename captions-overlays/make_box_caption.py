"""Recreate a TikTok "text box" caption (black text on a rounded white box).

Usage: python make_box_caption.py out.png "Scammers Be Like" [--x 135] [--y 1581] [--size 58]
Makes a transparent 1080x1920 PNG to overlay on a finished vertical video.
"""
import argparse

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("text")
ap.add_argument("--x", type=int, default=135, help="left edge of the box")
ap.add_argument("--y", type=int, default=1581, help="top edge of the box")
ap.add_argument("--size", type=int, default=58)
a = ap.parse_args()

font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", a.size)
pad_x, pad_y = int(a.size * 0.45), int(a.size * 0.40)
l, t, r, b = font.getbbox(a.text)
box = (a.x, a.y, a.x + (r - l) + 2 * pad_x, a.y + (b - t) + 2 * pad_y)

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle(box, radius=int(a.size * 0.22), fill=(255, 255, 255, 245))
d.text((a.x + pad_x - l, a.y + pad_y - t), a.text, font=font, fill=(22, 22, 22))
img.save(a.out)
print(a.out, box)
