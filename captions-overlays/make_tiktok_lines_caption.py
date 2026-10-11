"""Recreate a TikTok multi-line "text box" caption: centered lines, each on its own white rounded box
(boxes merge into one shape), heavy black text, inline color emoji.

Usage: python make_tiktok_lines_caption.py out.png "line 1" "line 2 {laugh}{rofl}{rofl}" [--y 170] [--width 905]
Emoji placeholders: {laugh} = tears of joy, {rofl} = rolling on the floor laughing, {cat} = cat face.
--width = pixel width of the widest line's text (font size is fitted to it).
Makes a transparent 1080x1920 PNG to overlay on a finished vertical video.
"""
import argparse

from PIL import Image, ImageDraw, ImageFont

EMOJI = {"{laugh}": "\U0001F602", "{rofl}": "\U0001F923", "{cat}": "\U0001F431"}
W, H = 1080, 1920

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("lines", nargs="+")
ap.add_argument("--y", type=int, default=170, help="top of the first box")
ap.add_argument("--width", type=int, default=905, help="text width of the widest line")
a = ap.parse_args()


def split(line):
    parts, i = [], 0
    while i < len(line):
        for k, v in EMOJI.items():
            if line.startswith(k, i):
                parts.append((True, v))
                i += len(k)
                break
        else:
            if parts and not parts[-1][0]:
                parts[-1] = (False, parts[-1][1] + line[i])
            else:
                parts.append((False, line[i]))
            i += 1
    return parts


def fonts(size):
    return (ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", size),
            ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", int(size * 0.8)))


def width(parts, f, e):
    return sum((e if emo else f).getlength(t) for emo, t in parts)


lines = [split(l) for l in a.lines]
size = 120
while size > 20:
    f, e = fonts(size)
    if max(width(p, f, e) for p in lines) <= a.width:
        break
    size -= 1

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
pad_x, line_h = int(size * 0.5), int(size * 1.26)
radius = int(size * 0.32)
for n, parts in enumerate(lines):
    w = width(parts, f, e)
    top = a.y + n * line_h
    d.rounded_rectangle((W / 2 - w / 2 - pad_x, top, W / 2 + w / 2 + pad_x, top + line_h + 2),
                        radius=radius, fill=(255, 255, 255, 255))
for n, parts in enumerate(lines):
    x = W / 2 - width(parts, f, e) / 2
    mid = a.y + n * line_h + line_h / 2
    for emo, t in parts:
        if emo:
            d.text((x, mid), t, font=e, embedded_color=True, anchor="lm")
            x += e.getlength(t)
        else:
            d.text((x, mid), t, font=f, fill=(0, 0, 0, 255), anchor="lm")
            x += f.getlength(t)
img.save(a.out)
print(a.out, "font", size)


