"""
BeatDrop: MosesGotWater's YouTube type-beat uploader.

  python beatdrop.py scan              list beats not uploaded yet (writes new_beats.json)
  python beatdrop.py photos            download a thumbnail photo for each queued beat that needs one
  python beatdrop.py render [N]        render videos for the next N queued beats (default 2)
  python beatdrop.py upload [N]        render + upload the next N queued beats (default 2), public
  python beatdrop.py status            show the queue

queue.json holds the planned uploads (title, artists, name, file, ...). Claude fills it each week;
daily runs just take the next 2. Done items move to done.json.
"""
import json, os, re, subprocess, sys, urllib.parse, urllib.request, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)
BEAT_DIRS = [r"C:\Users\moses\Desktop\2024", r"C:\Users\moses\Desktop"]
FONT = "C\\:/Windows/Fonts/impact.ttf"
FONT2 = "C\\:/Windows/Fonts/arialbd.ttf"
CONTACT = "IG: @mosesgotwater | Email: mosesgotwater@gmail.com"
DUP_ALIGNED = 200   # fingerprint.py: re-uploads score 1,200-2,100 aligned hashes, different beats ~10-25
MAIN_PROD = "MosesGotWater"   # title + thumbnail credit; item["prod"] (with collabs) goes in the description
# Goes in every description once the site is public (Moses is reviewing it first). Fill in to turn it on.
WEBSITE = "https://mgwmadeit.com"   # his domain, connected 2026-10-05
os.makedirs(P("photos"), exist_ok=True); os.makedirs(P("renders"), exist_ok=True)

def load(name, default):
    try:
        with open(P(name), encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError: return default

def save(name, data):
    with open(P(name), "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(line, flush=True)
    with open(P("beatdrop.log"), "a", encoding="utf-8") as f: f.write(line + "\n")

def youtube():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    c = Credentials.from_authorized_user_file(P("token.json"))
    if not c.valid:
        c.refresh(Request()); open(P("token.json"), "w").write(c.to_json())
    return build("youtube", "v3", credentials=c)

def channel_titles(yt):
    up = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    titles, tok = [], None
    while True:
        r = yt.playlistItems().list(part="snippet", playlistId=up, maxResults=50, pageToken=tok).execute()
        titles += [i["snippet"]["title"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok: return titles

def scan():
    used = {d["file"] for d in load("done.json", []) + load("queue.json", [])}
    out = []
    for d in BEAT_DIRS:
        for f in sorted(os.listdir(d)):
            full = os.path.join(d, f)
            if f.lower().endswith(".mp3") and full not in used:
                out.append({"file": full, "modified": datetime.datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d")})
    save("new_beats.json", out)
    print(f"{len(out)} beats not queued or uploaded yet -> new_beats.json")

def fetch_photo(item):
    """Grab a large photo of the first artist from Bing image results."""
    dest = P("photos", re.sub(r"[^a-z0-9]+", "-", item["artists"][0].lower()) + ".jpg")
    if os.path.exists(dest): return dest
    q = urllib.parse.quote(item["artists"][0] + " rapper")
    req = urllib.request.Request(f"https://www.bing.com/images/search?q={q}&qft=+filterui:imagesize-large&form=IRFLTR",
                                 headers={"User-Agent": "Mozilla/5.0"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    for m in re.findall(r'murl&quot;:&quot;(.*?)&quot;', page)[:30]:
        url = html.unescape(m)
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read()
            if len(data) < 40_000: continue
            tmp = dest + ".dl"; open(tmp, "wb").write(data)
            # normalize to jpg, and reject small images
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", tmp], capture_output=True, text=True).stdout.strip()
            w, h = (int(x) for x in probe.split(",")[:2]) if "," in probe else (0, 0)
            if min(w, h) < 500: os.remove(tmp); continue
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-frames:v", "1", "-q:v", "2", dest], check=True)
            os.remove(tmp); return dest
        except Exception:
            continue
    raise RuntimeError("no usable photo for " + item["artists"][0])

def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019").replace("%", "\\%")

def prod_lines(prod):
    """'MosesGotWater x Slajidi' -> ['PROD. MOSESGOTWATER', 'x SLAJIDI'] so long credits never run off the frame."""
    parts = [p.strip().upper() for p in re.split(r"\s+x\s+", prod, flags=re.I)]
    return ["PROD. " + parts[0]] + ["x " + p for p in parts[1:]]

def render(item):
    out = P("renders", re.sub(r"[^A-Za-z0-9]+", "_", item["name"]).strip("_") + ".mp4")
    thumb = out[:-4] + "_thumb.jpg"
    if os.path.exists(out) and os.path.exists(thumb): return out, thumb
    photo = item.get("photo") or fetch_photo(item)
    # Moses's style: just the artist photo, full frame. No blur, no text (title/BPM/key live in the title + description).
    # Tall/square photos are cropped toward the top so heads don't get cut off.
    vf = "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080:(iw-1920)/2:(ih-1080)*0.2,setsar=1[v]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", photo, "-filter_complex", vf,
                    "-map", "[v]", "-frames:v", "1", "-q:v", "3", "-s", "1280x720", thumb], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", item["file"]],
                         capture_output=True, text=True).stdout.strip()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "1", "-t", dur, "-i", photo, "-i", item["file"],
                    "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage",
                    "-crf", "28", "-r", "1", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", out], check=True)
    return out, thumb

def title_of(item):
    # collab producers go in the description only (Moses's rule); the title credits him alone
    # no year in the title (Moses, 2026-10-05); the year lives in the description's first line + tags
    t = f'(FREE) {" x ".join(a.upper() for a in item["artists"])} TYPE BEAT "{item["name"].upper()}" | Prod {MAIN_PROD}'
    return t[:100]

def description(item):
    """Same layout as his best-performing uploads (Cha-Cha Slide, Biggest Bully, ARP), keywords up top."""
    yr = datetime.date.today().year
    arts = " x ".join(item["artists"])
    tags = " ".join("#" + re.sub(r"[^a-z0-9]", "", a.lower()) + "typebeat" for a in item["artists"])
    return (f'{arts} Type Beat {yr} "{item["name"]}" | Detroit Type Beat {yr}\n\n'
            f"FREE FOR NON PROFIT | MUST CREDIT: prod by mosesgotwater or MGW\n"
            f"*Releasing without a lease will result in a copyright strike*\n"
            f"(SPOTIFY, APPLE MUSIC, TIDAL, YOUTUBE ETC ALL NEED A LEASE)\n"
            f"Buy/Free Download This Beat : DM me on IG or email\n\n"
            f"BPM - {item['bpm']} | Key - {item['key']}\n"
            f"Produced by {item['prod']}\n\n"
            f"Dm on Ig for faster response.\n"
            f"📸 Instagram: https://www.instagram.com/mosesgotwater\n"
            f"📬 Email: mosesgotwater@gmail.com\n"
            + (f"🖥 Website: {WEBSITE}\n" if WEBSITE else "")
            + f"\n{tags} #detroittypebeat #typebeat\n")

LANE_TAGS = ["detroit type beat", "detroit type beat {yr}", "free detroit type beat", "michigan type beat", "type beat {yr}",
             "free type beat", "313 mafia type beat", "ybn lil bro type beat", "50droppin type beat", "happydranker type beat",
             "veeze type beat", "babyface ray type beat", "mosesgotwater", "prod mosesgotwater"]

def tags_of(item):
    """Tags in the order YouTube weighs them: exact artist combos first, then each artist, then the lane."""
    yr = datetime.date.today().year
    arts = [a for a in item["artists"] if a.lower() != "detroit"]
    lower = [a.lower() for a in arts]
    base = [" x ".join(lower) + " type beat"]
    for a in lower:
        base += [f"{a} type beat", f"{a} type beat {yr}", f"free {a} type beat", a]
    base += [t.format(yr=yr) for t in LANE_TAGS] + [f"{item['name'].lower()} type beat"]
    out, total = [], 0
    for t in dict.fromkeys(base):          # dedupe, keep order
        if total + len(t) + 3 > 490: break  # YouTube caps tags at 500 characters
        out.append(t); total += len(t) + 3
    return out

def upload(n=2):
    from googleapiclient.http import MediaFileUpload
    queue = load("queue.json", []); done = load("done.json", [])
    if not queue: log("queue empty, nothing to upload"); return
    yt = youtube()
    import fingerprint as fpx
    H, T, V, ids = fpx.build_index()
    sent = 0
    for item in list(queue):
        if sent >= n: break
        top, _ = fpx.best_match(item["file"], H, T, V)
        if top and top[0][1] >= DUP_ALIGNED:   # exact same recording is already on the channel
            item["reason"] = f"already on channel (video {ids[top[0][0]]}, {top[0][1]} aligned hashes)"
            save("skipped.json", load("skipped.json", []) + [item]); queue.remove(item); save("queue.json", queue)
            log(f"SKIPPED duplicate {item['name']}: {item['reason']}"); continue
        sent += 1
        video, thumb = render(item)
        body = {"snippet": {"title": title_of(item), "description": description(item), "tags": tags_of(item), "categoryId": "10"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
        req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(video, chunksize=-1, resumable=True))
        res = None
        while res is None: _, res = req.next_chunk()
        vid = res["id"]
        try: yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb)).execute()
        except Exception as e: log(f"thumbnail failed for {vid}: {e}")
        item.update(video_id=vid, uploaded=datetime.datetime.now().isoformat(timespec="minutes"))
        done.append(item); queue.remove(item)
        save("queue.json", queue); save("done.json", done)
        log(f"UPLOADED https://youtu.be/{vid}  {body['snippet']['title']}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    if cmd == "scan": scan()
    elif cmd == "photos":
        for it in load("queue.json", []): print(it["artists"][0], "->", fetch_photo(it))
    elif cmd == "render":
        for it in load("queue.json", [])[:n]: print(render(it))
    elif cmd == "upload": upload(n)
    else:
        q = load("queue.json", []); print(f"{len(q)} queued, {len(load('done.json', []))} done")
        for it in q: print(" -", title_of(it))
