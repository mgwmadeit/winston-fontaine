"""Recreate a TikTok/IG-style burned caption (white condensed bold text, dark outline + soft shadow, inline emoji).

Usage: python make_reel_caption.py out.png "line 1" "line 2 with {cat}" [--y 217] [--size 50]
Emoji placeholders: {cat} = cat face, {weary} = weary face, {laugh} = tears of joy.
Makes a transparent 1080x1920 PNG to overlay on a finished vertical video.
"""
import argparse

from PIL import Image, ImageDraw, ImageFilter, ImageFont

EMOJI = {"{cat}": "\U0001F431", "{weary}": "\U0001F629", "{laugh}": "\U0001F602"}
W, H = 1080, 1920

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("lines", nargs="+")
ap.add_argument("--y", type=int, default=217, help="top of the first line")
ap.add_argument("--size", type=int, default=50)
ap.add_argument("--gap", type=int, default=46, help="extra px between line tops beyond the font size")
a = ap.parse_args()

font = ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf", a.size)
try:
    font.set_variation_by_name("Bold Condensed")
except Exception:
    pass
emo = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", int(a.size * 0.78))

def split(line):
    parts, i = [], 0
    while i < len(line):
        hit = next((k for k in EMOJI if line.startswith(k, i)), None)
        if hit:
            parts.append(("e", EMOJI[hit])); i += len(hit)
        else:
            j = min([line.find(k, i) for k in EMOJI if line.find(k, i) >= 0] + [len(line)])
            parts.append(("t", line[i:j])); i = j
    return parts

text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
emoji_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dt, de = ImageDraw.Draw(text_layer), ImageDraw.Draw(emoji_layer)
y = a.y
for line in a.lines:
    parts = split(line)
    widths = [(font if k == "t" else emo).getlength(s) for k, s in parts]
    x = (W - sum(widths)) / 2
    for (k, s), w in zip(parts, widths):
        if k == "t":
            dt.text((x, y), s, font=font, fill="white", stroke_width=3, stroke_fill=(20, 20, 20))
        else:
            de.text((x, y + a.size * 0.08), s, font=emo, embedded_color=True)
        x += w
    y += a.size + a.gap

shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
alpha = text_layer.split()[3].point(lambda v: int(v * 0.55))
shadow.putalpha(alpha)
shadow = shadow.filter(ImageFilter.GaussianBlur(4))
out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
out.alpha_composite(shadow, (2, 3))
out.alpha_composite(text_layer)
out.alpha_composite(emoji_layer)
out.save(a.out)
print("saved", a.out)
