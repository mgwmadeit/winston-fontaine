# Alternates between the photos available for each artist so the same picture doesn't repeat back to back.
import os, re, beatdrop as b

items = b.load("queue.json", [])
counts = {}
for it in items:
    base = re.sub(r"-\d+$", "", os.path.splitext(os.path.basename(it["photo"]))[0])
    options = sorted(f for f in os.listdir(b.P("photos")) if re.fullmatch(re.escape(base) + r"(-\d+)?\.jpg", f))
    i = counts.get(base, 0); counts[base] = i + 1
    it["photo"] = b.P("photos", options[i % len(options)])
    print(it["name"], "->", os.path.basename(it["photo"]))
b.save("queue.json", items)
