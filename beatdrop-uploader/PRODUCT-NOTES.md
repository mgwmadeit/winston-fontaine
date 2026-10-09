# BeatDrop as a product: how it learns a producer automatically

Goal (Moses, 2026-10-05): the producer makes beats and BeatDrop does everything else, getting it right without them double-checking. Nothing like this is on the market yet.

## Onboarding: build the producer profile automatically
1. **Their channel**: pull every title (YouTube API). Learn which artists they already target, their title format, upload pace, and which videos got the most views (= the lanes worth doubling down on).
2. **Their socials**: read their Instagram captions and tags. Who they've worked with or posted.
3. **Their beat folder**: BPM, key, energy and tags in the filenames (e.g. "BFACE" = Babyface Ray), plus collaborators named in the filenames.
4. **Market research for each lane artist**: search "<artist> type beat" on YouTube and record the co-artists that rank (real pairings), typical BPMs, and how crowded the lane is.
5. Write profile.json (like Moses's) and show it to the producer ONCE to confirm the lanes. After that it runs on its own.

## Per beat (automatic)
- Sound fingerprint vs. their whole channel → skip re-uploads.
- Match the beat to a lane by BPM, key and sound similarity to their past uploads in each lane (the beats they already titled "50Droppin type beat" teach what that lane sounds like).
- Pick a pairing from profile.pairings, a name, and a photo (official music-video stills of the artist; reject guns, watermarks and UI screenshots).
- Render, then schedule 2/day.

## Learning loop
- Every week, re-read the channel's view counts: lanes that grow get more uploads, dead lanes get fewer.
- Every month, re-run the market research so pairings follow who's hot (e.g. 50Droppin right now).

## Still to solve before selling
- Google app verification (for other people's channels) + a quota increase.
- A photo picker that verifies the face is the right artist (right now Claude checks, and Moses has the final say).
- Hosting: a small desktop app (folder watcher) + a cloud dashboard. Subscription through Payhip.
