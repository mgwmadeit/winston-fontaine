"""Winston clip overlay: white caption box (black text) + Kick brand strip.
Usage: python make_overlay.py "caption text" out.png [box_top_y] [center|left] [font_size]
Use "|" in the caption to force a line break.

Everything stays inside Instagram Reels' safe area (1080x1920):
  top 250px = username/header, bottom 420px = caption/audio row,
  right ~140px from y~900 down = like/comment/share buttons.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
SAFE_TOP, SAFE_BOTTOM, RIGHT_RAIL = 250, H - 420, 140

caption = sys.argv[1]
out = sys.argv[2]
y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 300  # move down if it covers the face

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
black_font = "C:/Windows/Fonts/ariblk.ttf"

# --- caption box (chat-bubble style, like streamer clips) ---
align = sys.argv[4] if len(sys.argv) > 4 else "center"  # "left" tucks a small box beside his head
size = int(sys.argv[5]) if len(sys.argv) > 5 else 56
f = ImageFont.truetype(black_font, size)
max_w = W - 2 * RIGHT_RAIL - 80 if align == "center" else 480
lines = []
for part in caption.split("|"):
    cur = ""
    for w in part.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
lh = int(size * 1.3)
pad = int(size * 0.7)
box_w = max(d.textlength(l, font=f) for l in lines) + 2 * pad
box_h = lh * len(lines) + pad
x0 = (W - box_w) / 2 if align == "center" else 48
y0 = max(SAFE_TOP, min(y0, SAFE_BOTTOM - 110 - box_h))  # never under IG UI or the strip
d.rounded_rectangle([x0 + 6, y0 + 8, x0 + box_w + 6, y0 + box_h + 8], 26, fill=(0, 0, 0, 70))  # soft shadow
d.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], 26, fill=(255, 255, 255, 255))
for i, l in enumerate(lines):
    tw = d.textlength(l, font=f)
    tx = (W - tw) / 2 if align == "center" else x0 + pad
    d.text((tx, y0 + pad / 2 + i * lh), l, font=f, fill=(0, 0, 0, 255), stroke_width=1, stroke_fill=(0, 0, 0, 255))

# --- brand strip: sits just above IG's bottom caption area ---
sh = 90
sy = SAFE_BOTTOM - sh
d.rectangle([0, sy, W, sy + sh], fill=(0, 0, 0, 215))
kf = ImageFont.truetype(black_font, 54)
uf = ImageFont.truetype(black_font, 34)
kick = "KICK"
url = "KICK.COM/WINSTONFONTAINE"
kw = d.textlength(kick, font=kf)
uw = d.textlength(url, font=uf)
gap = 24
usable = W - RIGHT_RAIL  # keep text left of the button rail
sx = 40 + (usable - 40 - (kw + gap + uw)) / 2
d.text((sx, sy + 12), kick, font=kf, fill=(83, 252, 24, 255))
d.text((sx + kw + gap, sy + 27), url, font=uf, fill=(255, 255, 255, 255))

img.save(out)
print("saved", out, "box_y", y0)
