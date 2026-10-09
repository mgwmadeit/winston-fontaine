"""
Sound-based duplicate check: is a beat already on the channel (under any title)?
Compares harmony (chroma) of a 30s slice of each beat against the first 100s of every channel video.

  python dedupe.py                 check every beat in queue.json
  python dedupe.py file1.mp3 ...   check specific files
Fingerprints of channel videos are cached in channel_fp.npz.
"""
import os, sys, json, glob
import numpy as np, librosa

HERE = os.path.dirname(os.path.abspath(__file__))
SR, HOP = 11025, 2048           # ~5.4 frames/sec
# Verdict (calibrated on known re-uploads Slezi / Flint Boy / BT Flow = 0.99-1.00 on every slice):
# >= 0.97 on all slices = DUPLICATE, 0.90-0.97 = MAYBE (listen), below = new

def fp(path, offset=0.0, duration=None):
    y, _ = librosa.load(path, sr=SR, mono=True, offset=offset, duration=duration)
    c = librosa.feature.chroma_cens(y=y, sr=SR, hop_length=HOP)
    return (c / (np.linalg.norm(c, axis=0, keepdims=True) + 1e-9)).astype(np.float32)

def best_match(q, ref):
    """Best mean cosine similarity of query q (12xN) slid along ref (12xM), allowing key shifts of 0 only."""
    n, m = q.shape[1], ref.shape[1]
    if m < n: q, n = q[:, :m], m
    sims = q.T @ ref                          # N x M frame similarities
    best = 0.0
    for lag in range(0, m - n + 1):
        s = np.trace(sims[:, lag:lag + n]) / n
        if s > best: best = s
    return best

def channel_fps():
    cache = os.path.join(HERE, "channel_fp.npz")
    data = dict(np.load(cache, allow_pickle=True)) if os.path.exists(cache) else {}
    changed = False
    for f in glob.glob(os.path.join(HERE, "channel_audio", "*.mp3")):
        vid = os.path.splitext(os.path.basename(f))[0]
        if vid not in data:
            try: data[vid] = fp(f, 0, 100); changed = True
            except Exception as e: print("skip", vid, e)
    if changed: np.savez(cache, **data)
    return data

def titles():
    p = os.path.join(HERE, "channel_ids.json")
    return json.load(open(p, encoding="utf-8-sig")) if os.path.exists(p) else {}

def check(files):
    ref, names = channel_fps(), titles()
    print(f"comparing against {len(ref)} channel videos")
    report = []
    for f in files:
        dur = librosa.get_duration(path=f)
        q = fp(f, min(20, dur / 4), 30)
        top, vid = max((best_match(q, r), vid) for vid, r in ref.items())
        if top >= 0.90:   # confirm on two more slices: a real re-upload matches ~1.00 everywhere
            more = [best_match(fp(f, off, 15), ref[vid]) for off in (min(45, dur / 2), min(70, dur * 0.7))]
            top = min([top] + more)
        flag = "DUPLICATE" if top >= 0.97 else ("MAYBE" if top >= 0.90 else "new")
        line = f"{flag:9s} {top:.2f}  {os.path.basename(f)}  ~ {names.get(vid, vid)}"
        print(line, flush=True); report.append({"file": f, "score": round(float(top), 3), "match": vid, "flag": flag})
    json.dump(report, open(os.path.join(HERE, "dedupe_report.json"), "w"), indent=1)
    return report

if __name__ == "__main__":
    files = sys.argv[1:] or [it["file"] for it in json.load(open(os.path.join(HERE, "queue.json"), encoding="utf-8"))]
    check(files)
