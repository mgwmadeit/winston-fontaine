"""Lip sync check for a Genjutsu render against its motion source.

Usage: python lipsync_check.py SOURCE.mp4 RENDER.mp4 [--audio AUDIO_FILE]
  SOURCE  = the motion clip uploaded to Genjutsu (has the real audio)
  RENDER  = the raw Genjutsu output (or a finished video to re-check)
  --audio = the audio used in the final (default: SOURCE's audio)

Prints:
  1. audio lag of RENDER's audio track vs SOURCE (should be 0 ms)
  2. whole-frame motion lag of RENDER vs SOURCE
  3. mouth-region motion vs audio lag for SOURCE and RENDER
  4. the audio shift to apply: positive = delay audio (adelay), negative = trim audio start (atrim start)
Goal: RENDER mouth-vs-audio lag == SOURCE mouth-vs-audio lag (within ~20 ms).
Needs ffmpeg on PATH + numpy.
"""
import argparse
import subprocess
import numpy as np

FPS, W, H = 24, 48, 86


def frames(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(float)


def audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def envelope(a):
    hop = 16000 // FPS
    n = len(a) // hop
    return np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1))


def lag_ms(x, y, rng=12):
    """ms that x lags behind y (sub-frame, parabolic peak)."""
    n = min(len(x), len(y))
    x = x[:n] - x[:n].mean()
    y = y[:n] - y[:n].mean()
    c = {L: np.dot(x[max(0, L):n + min(0, L)], y[max(0, -L):n - max(0, L)]) / (n - abs(L)) for L in range(-rng, rng + 1)}
    L = max(c, key=c.get)
    y0, y1, y2 = c.get(L - 1, 0), c[L], c.get(L + 1, 0)
    den = y0 - 2 * y1 + y2
    d = 0.5 * (y0 - y2) / den if den else 0
    return round((L + d) / FPS * 1000)


def motion(v, box=None):
    if box:
        r0, r1, c0, c1 = box
        v = v[:, r0:r1, c0:c1]
    return np.abs(np.diff(v, axis=0)).mean((1, 2))


ap = argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("render")
ap.add_argument("--audio")
a = ap.parse_args()

src_v, ren_v = frames(a.source), frames(a.render)
src_a = audio(a.source)
fin_a = audio(a.audio) if a.audio else src_a
try:
    ren_a = audio(a.render)
    e1, e2 = np.maximum(np.diff(envelope(ren_a)), 0), np.maximum(np.diff(envelope(src_a)), 0)
    print("render audio vs source audio lag:", lag_ms(e1, e2), "ms")
except Exception:
    print("render has no audio track")
print("render motion vs source motion lag:", lag_ms(motion(ren_v), motion(src_v)), "ms (+ = render late)")

# mouth region: try a grid of face-height bands, keep the one where SOURCE motion tracks speech best
env = envelope(fin_a)[1:]
best = None
for r0 in range(10, 70, 6):
    for c0 in range(0, 36, 6):
        box = (r0, r0 + 18, c0, c0 + 14)
        m = motion(src_v, box)
        n = min(len(m), len(env))
        corr = np.corrcoef(m[:n], env[:n])[0, 1]
        if best is None or corr > best[0]:
            best = (corr, box)
box = best[1]
s_l = lag_ms(motion(src_v, box), envelope(src_a)[1:])
r_l = lag_ms(motion(ren_v, box), env)
print(f"mouth box {box} (corr {best[0]:.2f}): source mouth-vs-audio {s_l} ms | render mouth-vs-audio {r_l} ms")
shift = r_l - s_l
if abs(shift) <= 20:
    print("LIP SYNC OK (within 20 ms of the source)")
elif shift < 0:
    # lips move earlier than in the source -> the sound is late -> pull the audio earlier
    print(f"lips lead the sound by {-shift} ms -> trim audio start: atrim=start={-shift/1000:.3f}")
else:
    print(f"lips trail the sound by {shift} ms -> delay audio: adelay={shift}:all=1")
