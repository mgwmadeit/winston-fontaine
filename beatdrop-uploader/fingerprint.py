"""
Exact-recording duplicate check (Shazam-style landmark fingerprints).
Picks spectral peaks, hashes peak pairs (freq1, freq2, time gap), and counts hashes that line up at one
consistent time offset. The same recording (even re-encoded by YouTube, with a tag on top) lines up
hundreds of times; a different beat in the same key lines up only by chance.

  python fingerprint.py              check queue.json against the channel
  python fingerprint.py a.mp3 ...    check specific files
"""
import os, sys, json, glob, collections
import numpy as np, librosa
from scipy.ndimage import maximum_filter

HERE = os.path.dirname(os.path.abspath(__file__))
SR, NFFT, HOP = 11025, 1024, 256
FAN, DT_MAX = 6, 64

def hashes(path, offset=0.0, duration=None):
    y, _ = librosa.load(path, sr=SR, mono=True, offset=offset, duration=duration)
    S = np.abs(librosa.stft(y, n_fft=NFFT, hop_length=HOP))
    S = librosa.amplitude_to_db(S, ref=np.max)
    peaks = (S == maximum_filter(S, size=(25, 25))) & (S > -45)
    f_idx, t_idx = np.nonzero(peaks)
    order = np.argsort(t_idx); f_idx, t_idx = f_idx[order], t_idx[order]
    out = []
    for i in range(len(t_idx)):
        for j in range(i + 1, min(i + 1 + FAN, len(t_idx))):
            dt = t_idx[j] - t_idx[i]
            if 0 < dt <= DT_MAX:
                out.append(((int(f_idx[i]) << 16) | (int(f_idx[j]) << 6) | int(dt), int(t_idx[i])))
    return out

def build_index():
    cache = os.path.join(HERE, "channel_index.npz")
    files = sorted(glob.glob(os.path.join(HERE, "channel_audio", "*.mp3")))
    if os.path.exists(cache):
        d = np.load(cache, allow_pickle=True)
        if int(d["n"]) == len(files): return d["h"], d["t"], d["v"], list(d["ids"])
    H, T, V, ids = [], [], [], []
    for k, f in enumerate(files):
        try: hs = hashes(f, 0, 100)
        except Exception as e: print("skip", f, e); hs = []
        ids.append(os.path.splitext(os.path.basename(f))[0])
        for h, t in hs: H.append(h); T.append(t); V.append(k)
    H, T, V = np.array(H, np.int64), np.array(T, np.int32), np.array(V, np.int32)
    o = np.argsort(H); H, T, V = H[o], T[o], V[o]
    np.savez(cache, h=H, t=T, v=V, ids=np.array(ids), n=len(files))
    return H, T, V, ids

def best_match(path, H, T, V):
    dur = librosa.get_duration(path=path)
    q = hashes(path, 0, min(dur, 120))
    qh = np.array([h for h, _ in q], np.int64); qt = np.array([t for _, t in q], np.int32)
    lo, hi = np.searchsorted(H, qh, "left"), np.searchsorted(H, qh, "right")
    votes = collections.Counter()
    for i in range(len(qh)):
        for k in range(lo[i], hi[i]):
            votes[(int(V[k]), int(T[k]) - int(qt[i]))] += 1
    per_video = collections.Counter()
    for (v, off), c in votes.items():                     # allow +-1 frame of jitter
        per_video[v] = max(per_video[v], c + votes.get((v, off + 1), 0) + votes.get((v, off - 1), 0))
    top = per_video.most_common(2)
    return top, len(qh)

if __name__ == "__main__":
    names = {}
    p = os.path.join(HERE, "channel_ids.json")
    if os.path.exists(p): names = json.load(open(p, encoding="utf-8-sig"))
    files = sys.argv[1:] or [it["file"] for it in json.load(open(os.path.join(HERE, "queue.json"), encoding="utf-8"))]
    H, T, V, ids = build_index()
    print(f"index: {len(ids)} channel videos, {len(H)} hashes")
    for f in files:
        top, n = best_match(f, H, T, V)
        (v1, c1), (v2, c2) = (top + [(None, 0), (None, 0)])[:2]
        print(f"{c1:5d} aligned (next best {c2:4d}, {n} hashes)  {os.path.basename(f)}  ~ {names.get(ids[v1], ids[v1]) if v1 is not None else '-'}", flush=True)
