# Second opinion on a suspected duplicate. Finds the best alignment by harmony (chroma), then compares the
# full sound texture (log-mel spectrogram) at that alignment. The same recording scores ~0.9+; a different
# beat in the same key usually scores far lower.
import sys, numpy as np, librosa
from dedupe import SR, HOP

def feats(path, off, dur):
    y, _ = librosa.load(path, sr=SR, mono=True, offset=off, duration=dur)
    ch = librosa.feature.chroma_cens(y=y, sr=SR, hop_length=HOP)
    ch /= np.linalg.norm(ch, axis=0, keepdims=True) + 1e-9
    mel = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=SR, hop_length=HOP, n_mels=64))
    return ch, mel

def texture_score(beat, clip):
    rch, rmel = feats(clip, 0, 100)
    out = []
    for off in (15, 40):
        qch, qmel = feats(beat, off, 15)
        n = qch.shape[1]
        if rch.shape[1] <= n: break
        sims = qch.T @ rch
        lag = int(np.argmax([np.trace(sims[:, l:l + n]) / n for l in range(rch.shape[1] - n)]))
        a, b = qmel.flatten(), rmel[:, lag:lag + n].flatten()
        out.append(float(np.corrcoef(a, b)[0, 1]))
    return max(out) if out else 0.0

if __name__ == "__main__":
    s = texture_score(sys.argv[1], sys.argv[2])
    print(f"texture {s:.2f} ->", "SAME BEAT" if s >= 0.85 else "different beats")
