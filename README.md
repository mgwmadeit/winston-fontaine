# MosesGotWater: AI Influencer + Music Automation Portfolio

Tools, prompts and workflows behind **Winston Fontaine**, an AI influencer (albino, old-money, Miami-penthouse streamer) built to grow the music of producer/rapper **MosesGotWater** (IG @mosesgotwater).
Built with Claude Code + Higgsfield (Genjutsu motion transfer, Nano Banana image models, ByteDance upscale), ElevenLabs, ffmpeg, Python and OpenCV.

## What's in here

| Folder | What it does |
|---|---|
| `video-pipeline/` | `watch.py` downloads a reel/YouTube clip, transcribes it locally (faster-whisper) and pulls frames. `lipsync_check.py` measures lip sync between the AI video and the original (whole-frame motion, mouth motion via OpenCV face tracking, mouth vs. speech loudness). `neutralize_red.py` removes red props (party cups) from sources before motion transfer. `clean_vtt.py` cleans subtitles. |
| `captions-overlays/` | `make_overlay.py`: branded caption box + KICK strip inside Instagram's safe area. `make_reel_caption.py`: rebuilds a TikTok/IG burned-in caption (condensed bold, outline, color emoji) so a meme's caption can be matched exactly. `overlay_splitscreen.py`: split-screen layouts. `GRADE.txt`: house color grade. |
| `beatdrop-uploader/` | **BeatDrop**: a YouTube type-beat uploader. Scans the beat folders, picks titles from BPM/key/vibe, renders a 1080p video + thumbnail, schedules uploads through the YouTube Data API. `fingerprint.py`/`prescan.py` are Shazam-style landmark audio fingerprinting that keeps the same beat from being uploaded twice (re-uploads scored 500+ aligned hashes vs. a max of 85 for different beats). |
| `PROMPTS.md` | The Genjutsu / image prompt library, plus what each prompt fixed. |
| `LESSONS.md` | The pre-generate checklist and QC rules, learned the hard way (and what each mistake cost). |

## The reel pipeline (how a Winston video gets made)
1. **Grab the reel** (yt-dlp; age-restricted reels are pulled from the logged-in browser via the page's `video_versions` URL).
2. **Check the source before spending credits**: body type (Genjutsu copies the source person's build), props that get thrown or spilled, burned-in captions, watermarks and signs.
3. **Prep with ffmpeg**: cut the best 12-17s by word timestamps, crop away captions, KICK bars and watermarks (`crop`/`delogo`), blur readable signs.
4. **References**: Winston's master sheet + a cap photo + outfit/grill refs. Outfits come from a free Nano Banana image of *Winston* wearing the fit, never a photo of another person's body.
5. **Genjutsu motion transfer** at 480p with a structured prompt (background → motion lock → identity → hair → cap → glasses → teeth → outfit → props).
6. **QC every frame** against the checklist, then **ByteDance upscale** to 1080p.
7. **Finish in ffmpeg**: 9:16 layout, caption overlay, loudness -14 LUFS, slow down or beat-aligned loop to reach ≥12s.
8. **Verify**: `lipsync_check.py` (target ≈0 ms), a side-by-side check of mouth shapes on specific words, and a Whisper transcript of the final audio compared to the original.

## Results (Oct 2026)
About 20 finished Winston videos (#91–#110), including the first crossover with **Rashawn Leche** (@slavenameflick's AI character, with permission). Lip sync verified at 0–30 ms on every talking clip.

*Credentials (YouTube OAuth tokens, API keys) are deliberately not included.*
