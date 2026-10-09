# Pulls title/description/tags from (1) Moses's most-viewed uploads and (2) top-ranking videos in his lane,
# and writes seo_research.json + prints the most common tags.
import json, subprocess, collections
import beatdrop as b

yt = b.youtube()
up = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
ids, tok = [], None
while True:
    r = yt.playlistItems().list(part="contentDetails", playlistId=up, maxResults=50, pageToken=tok).execute()
    ids += [i["contentDetails"]["videoId"] for i in r["items"]]; tok = r.get("nextPageToken")
    if not tok: break
own = []
for k in range(0, len(ids), 50):
    r = yt.videos().list(part="snippet,statistics", id=",".join(ids[k:k + 50])).execute()
    own += [{"title": v["snippet"]["title"], "views": int(v["statistics"].get("viewCount", 0)),
             "tags": v["snippet"].get("tags", []), "description": v["snippet"]["description"]} for v in r["items"]]
own.sort(key=lambda v: -v["views"])

lane = []
for q in ["50droppin type beat", "ybn lil bro type beat", "313 mafia type beat"]:
    out = subprocess.run(["yt-dlp", "--skip-download", "--print", "%(title)s\t%(view_count)s\t%(tags)j",
                          f"ytsearch12:{q}"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                         env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}).stdout or ""
    for line in out.splitlines():
        t, v, tags = line.split("\t", 2)
        lane.append({"q": q, "title": t, "views": int(v) if v.isdigit() else 0, "tags": json.loads(tags) if tags.startswith("[") else []})

json.dump({"own_top": own[:15], "lane": lane}, open(b.P("seo_research.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("OWN TOP 5:")
for v in own[:5]: print(f"  {v['views']:6d}  {v['title']}\n         tags({len(v['tags'])}): {', '.join(v['tags'][:25])}\n         desc: {v['description'][:300]!r}")
c = collections.Counter(t.lower() for v in lane for t in v["tags"])
print("\nLANE TAGS (top 40):", ", ".join(f"{t}({n})" for t, n in c.most_common(40)))
