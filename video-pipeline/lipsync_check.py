"""Lip-sync check: does the generated face's mouth move in time with the source audio?

Usage: python lipsync_check.py <source_video> <generated_video>
Prints three checks (all lags in ms, + means the generated video is LATE):
  1. whole-frame motion: generated vs source
  2. mouth motion: generated mouth vs source mouth
  3. mouth vs audio: each video's mouth motion vs the speech loudness (should match each other)
"""
import subprocess
import sys

import cv2
import numpy as np

FPS = 50
CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def frames(path, w=360):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={FPS},scale={w}:-2,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    h = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", path], capture_output=True, text=True).stdout.split(",")[1])
    W0 = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width",
                             "-of", "csv=p=0", path], capture_output=True, text=True).stdout)
    hh = int(round(h * w / W0 / 2) * 2)
    return np.frombuffer(raw, np.uint8).reshape(-1, hh, w)


def mouth_signal(F):
    box, sig, found = None, [], 0
    for i, f in enumerate(F):
        if i % 2 == 0:
            faces = CASCADE.detectMultiScale(f, 1.1, 4, minSize=(50, 50))
            if len(faces):
                b = max(faces, key=lambda r: r[2] * r[3]).astype(float)
                box = b if box is None else 0.6 * box + 0.4 * b
                found += 1
        if box is None:
            sig.append(0.0)
            continue
        x, y, w, h = box
        roi = (slice(int(y + 0.62 * h), int(y + 0.95 * h)), slice(int(x + 0.25 * w), int(x + 0.75 * w)))
        prev = F[i - 1] if i else f
        sig.append(np.abs(f[roi].astype(float) - prev[roi].astype(float)).mean())
    return np.array(sig), found / max(1, len(F) // 2)


def whole_motion(F):
    return np.r_[0, np.abs(np.diff(F.astype(float), axis=0)).mean((1, 2))]


def audio_env(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-af", "highpass=f=200,lowpass=f=3500",
                          "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    hop = 16000 // FPS
    e = np.sqrt(np.add.reduceat(a[: len(a) // hop * hop] ** 2, np.arange(0, len(a) // hop * hop, hop)) / hop)
    return np.r_[0, np.maximum(np.diff(e), 0)]  # onsets of loudness = mouth opening moments


def z(x):
    x = np.convolve(x, np.ones(3) / 3, "same")
    return (x - x.mean()) / (x.std() + 1e-9)


def best_lag(a, b, maxlag=0.4):
    a, b = z(a), z(b)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    out = []
    for l in range(-int(maxlag * FPS), int(maxlag * FPS) + 1):
        x = a[max(0, -l): n - max(0, l)]
        y = b[max(0, l): n - max(0, -l)]
        out.append((float(np.mean(x * y)), l * 1000 // FPS))
    out.sort(reverse=True)
    peak, lag = out[0]
    runner = next((c for c, l in out if abs(l - lag) > 60), 0.0)
    return lag, round(peak, 3), round(runner, 3)


if __name__ == "__main__":
    src, gen = sys.argv[1], sys.argv[2]
    S, G = frames(src), frames(gen)
    ms, fs = mouth_signal(S)
    mg, fg = mouth_signal(G)
    aud = audio_env(src)
    print(f"face found: source {fs:.0%}, generated {fg:.0%}")
    print("1. whole-frame motion  gen vs source : lag %s ms (peak %s vs next %s)" % best_lag(whole_motion(S), whole_motion(G)))
    print("2. mouth motion        gen vs source : lag %s ms (peak %s vs next %s)" % best_lag(ms, mg))
    ls = best_lag(aud, ms)
    lg = best_lag(aud, mg)
    print("3. mouth vs audio      source        : lag %s ms (peak %s vs next %s)" % ls)
    print("                       generated     : lag %s ms (peak %s vs next %s)" % lg)
    print("   => generated vs source difference : %d ms" % (lg[0] - ls[0]))
