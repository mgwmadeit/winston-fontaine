# Saves the channel's titles and flags planned beat names that are already used.
import json, sys
import beatdrop as b

titles = b.channel_titles(b.youtube())
json.dump(titles, open(b.P("channel_titles.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(titles), "videos on the channel")
for name in sys.argv[1:]:
    hits = [t for t in titles if name.upper() in t.upper()]
    print(f"{name}: {'CLASH ' + hits[0] if hits else 'ok'}")
