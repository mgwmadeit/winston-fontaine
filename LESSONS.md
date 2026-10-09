# Lessons + QC Checklist

## Before every Generate
1. Source person is slim/athletic (Genjutsu copies body size; prompts can't override it).
2. Source has no thrown objects or chugging from bottles (they turn into spills and stains).
3. Burned-in captions, watermarks and KICK bars are cropped or delogo'd; readable signs are blurred.
4. References: master sheet (+ cap photo if wearing a cap) (+ Winston-in-the-fit image). Never another person's body.
5. Prompt covers hair, braid, cap, glasses, body, teeth, fit, setting and props.
6. Reference video thumbnail + duration verified; credit cost read off the button.

## After every Generate (before upscaling)
- Check 4+ frames for: hair, cap and logo, glasses, skin consistency (face vs. arms), body, outfit, pop-ins.
- If a must-have item is wrong, stop and offer a redo. Don't ship it quietly.

## Before sending a final
- `lipsync_check.py source final` → whole-frame + mouth lag ≈ 0 ms; correct with `adelay` if needed.
- Side-by-side mouth shapes on 6 words.
- **Transcribe the final audio** (faster-whisper) and compare to the original words. (The ElevenLabs voice swap passed the timing and pitch checks but came out unintelligible; only a transcript catches that.)
- Last line not cut off (video can be shorter than the audio → `tpad` to hold the last frame).
- ≥12 s (slow-motion if muted, or a beat-aligned loop found with audio autocorrelation).

## Costly mistakes (and the rule they created)
| Video | Mistake | Rule |
|---|---|---|
| #93/#95/#97 | Winston came out heavy (copied heavyset dancers) | Check the source body first |
| #102 | Wrong haircut, no cap | Pre-generate checklist; exact hair wording; cap reference photo |
| #105 | Garbled ElevenLabs voice + "trashy" grill | Always transcribe-check audio; keep the original voice by default; no grill |
| #103 | Drink splash stained the shirt | Skip sources with thrown or drunk props |
| #108 | Dark arms from the fit photo | Make a free Winston-in-the-fit image first |
