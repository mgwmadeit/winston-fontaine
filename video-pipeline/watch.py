"""Download a video, transcribe its audio, and grab still frames.

Usage:  python watch.py <video URL or local file> [--frames N] [--model base]
Output: a folder under ./videos/ with video, transcript.txt, and frames/.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import numpy as np
from faster_whisper import WhisperModel

HERE = Path(__file__).parent
OUT_ROOT = HERE / "videos"


def slug(text):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")[-60:] or "video"


def download(url, out_dir):
    subprocess.run(
        # Video+audio merged (YouTube serves them separately); cap at 720p to keep downloads small.
        ["yt-dlp", "-f", "bv*[height<=720]+ba/b[height<=720]/b", "--merge-output-format", "mp4",
         "-q", "--no-progress", "-o", str(out_dir / "video.%(ext)s"), url],
        check=True,
    )
    return next(out_dir.glob("video.*"))


def grab_frames(video, out_dir, count):
    frames = out_dir / "frames"
    frames.mkdir(exist_ok=True)
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True).stdout.strip() or 0)
    every = max(dur / count, 1)
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(video),
         "-vf", f"fps=1/{every},scale=640:-1", str(frames / "frame_%02d.jpg")],
        check=True,
    )
    return dur


def load_audio(video):
    # Decode with ffmpeg directly; faster-whisper's PyAV decoder breaks on some versions.
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(video), "-ac", "1",
         "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def transcribe(video, out_dir, model_size):
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(load_audio(video), vad_filter=True)
    lines = []
    for s in segments:
        m, sec = divmod(int(s.start), 60)
        lines.append(f"[{m:02d}:{sec:02d}] {s.text.strip()}")
    text = "\n".join(lines) or "(no speech detected)"
    (out_dir / "transcript.txt").write_text(text, encoding="utf-8")
    return text, info.language


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--model", default="base")  # tiny/base/small/medium
    a = p.parse_args()

    out_dir = OUT_ROOT / slug(a.source)
    out_dir.mkdir(parents=True, exist_ok=True)

    src = Path(a.source)
    existing = list(out_dir.glob("video.*"))
    video = src if src.exists() else existing[0] if existing else download(a.source, out_dir)
    dur = grab_frames(video, out_dir, a.frames)
    text, lang = transcribe(video, out_dir, a.model)

    print(f"\nFolder: {out_dir}\nLength: {dur:.0f}s  Language: {lang}\n")
    print(text)


if __name__ == "__main__":
    sys.exit(main())
