"""Overlay for side-by-side stream clips (e.g. the Cuffem FaceTime layout):
wipes the source creator's top caption + bottom strip, then adds our white caption box
(with emoji) and our KICK strip. Usage: python overlay_splitscreen.py "caption" out.png
"""
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
caption, out = sys.argv[1], sys.argv[2]
CAP_WIPE = (440, 522)    # source caption band (y)
STRIP_WIPE = (1396, 1520)  # source kick strip band (y)

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rectangle([0, CAP_WIPE[0], W, CAP_WIPE[1]], fill=(0, 0, 0, 255))
d.rectangle([0, STRIP_WIPE[0], W, STRIP_WIPE[1]], fill=(0, 0, 0, 255))

black_font = "C:/Windows/Fonts/ariblk.ttf"
f = ImageFont.truetype(black_font, 46)
ef = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 46)

# split caption into text + trailing emoji (anything outside basic latin)
text = "".join(ch for ch in caption if ord(ch) < 0x2000).strip()
emoji = "".join(ch for ch in caption if ord(ch) >= 0x2000)
tw = d.textlength(text, font=f)
ew = d.textlength(emoji, font=ef) + (12 if emoji else 0)
pad = 32
box_w, box_h = tw + ew + 2 * pad, 96
x0, y0 = (W - box_w) / 2, 418
d.rounded_rectangle([x0 + 5, y0 + 7, x0 + box_w + 5, y0 + box_h + 7], 24, fill=(0, 0, 0, 90))
d.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], 24, fill=(255, 255, 255, 255))
d.text((x0 + pad, y0 + 18), text, font=f, fill=(0, 0, 0, 255), stroke_width=1, stroke_fill=(0, 0, 0, 255))
if emoji:
    d.text((x0 + pad + tw + 12, y0 + 16), emoji, font=ef, embedded_color=True)

# our strip (same look as make_overlay.py), inside IG safe area
sh, sy = 90, 1410
d.rectangle([0, sy, W, sy + sh], fill=(0, 0, 0, 255))
kf = ImageFont.truetype(black_font, 54)
uf = ImageFont.truetype(black_font, 34)
kick, url = "KICK", "KICK.COM/WINSTONFONTAINE"
kw, uw = d.textlength(kick, font=kf), d.textlength(url, font=uf)
sx = 40 + (W - 140 - 40 - (kw + 24 + uw)) / 2
d.text((sx, sy + 12), kick, font=kf, fill=(83, 252, 24, 255))
d.text((sx + kw + 24, sy + 27), url, font=uf, fill=(255, 255, 255, 255))
img.save(out)
print("saved", out)

