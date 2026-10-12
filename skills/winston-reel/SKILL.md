---
name: winston-reel
description: Moses's full pipeline for turning an Instagram/TikTok reel into a Winston Fontaine video (Higgsfield Genjutsu motion transfer) with perfect lip sync, his caption style and the KICK strip. Use whenever Moses sends a reel link or says "do this one", "replace X with Winston", "put Leche in it", "add the kick strip", or asks to fix lip sync on a Winston video.
---

# Winston reel pipeline

Project root: `C:\Users\moses\auratar`. Read the newest `history\LOG.md` entries first.
Refresh PATH in every PowerShell call:
`$env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')`

Moses's rules: finish the whole reel without check-ins (feedback-reels-no-ask), but ASK before any single gen over ~60 credits, anything over 30s, or anything risky. Plain, short replies. Never rename his files. Number new files after the highest number in `videos\`.

## 1. Download
- `yt-dlp -o src.%(ext)s <url>` into `sources\ig-<CODE>\`.
- If it's age-restricted ("isn't available to everyone"), open the reel in a Claude-in-Chrome tab (IG is logged in there), then run JS: find `"video_versions":[{..."url":"..."}` in `document.scripts`, `fetch(url)` -> blob -> `<a download>`. The file lands as a `.tmp` in `C:\Users\moses\Downloads`; move it to `src.mp4`. Close that tab afterwards (a second tab hides the Higgsfield tab).
- Transcribe: faster-whisper `WhisperModel('small', device='cpu', compute_type='float32')`, feeding raw f32le PCM from ffmpeg (passing the mp4 path errors with this av version).
- Contact sheet: `ffmpeg -i src.mp4 -vf "fps=1,scale=160:-1,tile=8x6" -frames:v 1 sheet.jpg`.

## 2. Decide and prep (free)
- Genjutsu takes 4-30s and costs about 3.05 credits/sec at 480p. Final videos must be at least 12s.
- Avoid shaky/blurry running shots (they deform). Check that the source bodies are slim/athletic.
- Crop away the burned caption, KICK bars and watermarks (`crop`), and use `delogo` for small corner tags. Find coordinates with a `drawgrid=w=100:h=100` frame.
- Trim to end right after the punchline (use the word timestamps). Re-encode `-crf 20-21` so the file stays under 10MB (Chrome upload limit).

## 3. Character references (in `characters\` and `set\`)
- Winston = `00-master.png` + `set\MASTER-SET-v2.png` (navy MGW cap, cream cable-knit, light-blue collar). ALWAYS attach MASTER-SET-v2 when the source has a durag, wig, bald head or no hat; without it the cap gets dropped (#114).
- Rashawn Leche (Flick's character, permission given) = `characters\leche\LECHE-REF-SHEET.png`: jet-black blunt bowl cut, eyebrow slit, gold grill, white ribbed tank, muscular, light skin.
- New outfit from a photo: never attach another person's body. Make a FREE preview first (Higgsfield image, Seedream 5.0 lite with Unlimited ON = 0 credits), framed like the clip, fully dressed (pants!), and QC the whole image.
- Full look checklist: `memory\feedback-pre-generate-checklist.md`.

## 4. Genjutsu (Claude in Chrome, tab on higgsfield.ai)
- The tab is usually HIDDEN, so media never loads. Workarounds:
  - Upload the clip on `https://higgsfield.ai/upscale-video` (file input -> wait about 20s, DON'T press Upscale).
  - Then on `https://higgsfield.ai/ai/video?model=genjutsu` open "Add a reference video", click the `All` button via JS (`[...document.querySelectorAll('button')].find(x=>x.innerText.trim()==='All').click()`). The newest upload is the first tile, with a blank thumbnail. Uploading inside the Genjutsu picker opens an "Edit reference" dialog that hangs; don't use it.
  - Remove the old video/media with JS `.click()` on buttons whose label includes "Remove video" or "Remove media".
  - Character images CAN be uploaded in the picker's own file input.
- Prompt template: name each person by clothing and position, say what to REMOVE (hat/wig/beard), give the full Winston look (and Leche's if used), "LIP SYNC: keep each man's exact mouth movements... timing", and "keep everyone else and the background unchanged" (or describe the new setting).
- Typing in the prompt box freezes the CDP for about 30s but works; verify the text with JS (`[contenteditable=true]`).
- GENERATE: a real click often does nothing. Use a JS guard: check that the prompt starts correctly and the button shows the expected credits, then `button.click()`. Verify "Processing" appears and that there's only ONE new job (no double charge).
- Wait with background `sleep 300` (not polling). Find the result: JS for the newest `hf_<date>_*.mp4` in `video` srcs, and download from `https://d8j0ntlcm91z4.cloudfront.net/user_3C8fRa7vIIxwZ16VSLLmtozaqYr/<file>`.

## 5. QC (never skip)
- Contact sheet + 3 full-size frames: hair, cap, glasses, braid, outfit, body, hands, other people unchanged.
- Glitch scan: frame-diff spikes; tile the frames around each spike and compare with the source.
- LIP SYNC: `python -I scripts\lipsync_check.py SOURCE.mp4 RAW.mp4` -> apply the suggested `atrim`/`adelay`, render, then re-run it on the FINAL with `--audio FINAL.mp4` until it says "LIP SYNC OK".
- Transcribe the final and compare it to the source words.
- If a must-have is missing (cap, hair, deformed body), tell Moses and offer a redo; don't ship silently.

## 6. Finish (free)
- Upscale locally: `scale=1080:1920:flags=lanczos,unsharp=5:5:0.6` (+ night eq `contrast=1.04:saturation=1.08:gamma=1.03`). Skip the paid upscale unless asked.
- For landscape/square sources: put the clip in a vertical 1080x1920 frame with a blurred fill (`split`, `scale+boxblur`, `overlay`), like the original layout.
- Captions:
  - TikTok multi-line white box: `set\make_tiktok_lines_caption.py out.png "line1" "line2" --y 300 --width 800` (emoji placeholders `{laugh}` `{rofl}`; Moses usually wants NO emojis).
  - Single-line box: `make_box_caption.py`. Outlined text: `make_reel_caption.py`.
- KICK strip (KICK | KICK.COM/WINSTONFONTAINE): `set\overlay-kick-strip-only.png` (bottom, y about 1410). For the TOP, overlay at `0:-1150`. Keep it off faces and props.
- Audio = the source audio, shifted per lipsync_check. Save as `videos\NNN-WINSTON-<TITLE>-FINAL.mp4` and send it with SendUserFile.

## 7. Save everything
- Add to `history\LOG.md` (what, files, credits, lessons) and add a line to `HOME.md`.
- Put new lessons in memory + `history\claude-memory-backup\`.
- Copy new scripts to `portfolio\` and commit (`git -c user.name="MosesGotWater" -c user.email="mgwmadeit@gmail.com" commit`), then push.
- New repeatable workflow? Save or update a skill in `C:\Users\moses\.claude\skills\` (Moses's rule).
