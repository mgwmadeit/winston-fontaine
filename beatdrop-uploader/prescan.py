# Fingerprints every beat in the beat folders against the channel once, so future weeks only pick new beats.
# Writes prescan.json: {file: {"aligned": n, "match": video_title, "duplicate": bool}}
import os, json, glob
import fingerprint as fpx
from beatdrop import BEAT_DIRS, DUP_ALIGNED, P, save

names = json.load(open(P("channel_ids.json"), encoding="utf-8-sig"))
H, T, V, ids = fpx.build_index()
out = {}
for d in BEAT_DIRS:
    for f in sorted(glob.glob(os.path.join(d, "*.mp3"))):
        try:
            top, _ = fpx.best_match(f, H, T, V)
            v, c = top[0] if top else (None, 0)
            out[f] = {"aligned": c, "match": names.get(ids[v], ids[v]) if v is not None else None, "duplicate": c >= DUP_ALIGNED}
        except Exception as e:
            out[f] = {"error": str(e)}
        print(("DUP " if out[f].get("duplicate") else "new ") + os.path.basename(f), flush=True)
save("prescan.json", out)
dups = [f for f, r in out.items() if r.get("duplicate")]
print(f"done: {len(out)} beats scanned, {len(dups)} already on the channel")
