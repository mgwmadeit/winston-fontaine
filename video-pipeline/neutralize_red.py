"""Turn strongly saturated red objects (e.g. a red party cup) neutral grey, leaving skin untouched.

Usage: python neutralize_red.py <input.mp4> <output.mp4>
"""
import subprocess
import sys

import numpy as np

src, out = sys.argv[1], sys.argv[2]
tmp = out + ".video.mp4"

probe = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
     "stream=width,height,r_frame_rate", "-of", "csv=p=0", src],
    capture_output=True, text=True, check=True).stdout.strip().split(",")
W, H, rate = int(probe[0]), int(probe[1]), probe[2]

dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", src, "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                        "-s", f"{W}x{H}", "-r", rate, "-i", "-", "-c:v", "libx264", "-crf", "18",
                        "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
frames = changed = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    f = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.int16)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    mask = (r > g + 70) & (r > b + 50) & (r > 110) & (g < 110)
    grey = ((r + g + b) / 3 * 0.55 + 40).astype(np.int16)
    for c in range(3):
        f[..., c] = np.where(mask, grey, f[..., c])
    changed += mask.mean()
    frames += 1
    enc.stdin.write(f.astype(np.uint8).tobytes())
enc.stdin.close()
enc.wait()
dec.wait()

subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-i", src, "-map", "0:v",
                "-map", "1:a?", "-c", "copy", out], check=True)
print(f"frames {frames}, avg % pixels changed {changed / max(frames, 1) * 100:.2f}")
