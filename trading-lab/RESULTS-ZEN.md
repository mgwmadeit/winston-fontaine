# Zen Trades "Zen Model" (3 PDFs in trading\pdfs\, text in *.txt) vs 3 years of data (2026-10-11). Code: bot\zen.py
Model: sweep of a 1H/4H high/low -> inverse FVG (body close through a gap formed in the sweep direction) on 1-5 min -> retest entry in discount/premium
-> target liquidity. Claims ~75-80% win rate. Grading: A+ to C (sweep, FVG delivery, clean momentum, obvious target, singular gap, right side of range, bonus SMT).
96 variants tested (NQ/GC x 1m/5m x 1H/4H sweep x NY AM/London x target ref/1R/2R x momentum filter on/off).
- NQ: no edge. 1 of 48 variants positive in all 3 periods (5m, 1H sweep, London, 2R, momentum: +2.6/+3.7/~+R, tiny).
- GOLD 1m: loses (mostly -50 to -138R train).
- GOLD 5m, sweep of the previous 1H candle, LONDON 2-5 AM ET, momentum filter ON: positive in ALL 3 periods for ALL 3 targets
  (1R: 67%/80%/67% win, +9.3/+7.6/+2.9R; ref: +7.6/+13.2/+1.7R; 2R: +2.6/+15.1/+5.0R). Small samples (42/15/12 trades).
  That's the only place the 75-80% claim shows up. 1 pocket out of 96 tests = possibly luck -> sent to the AUDITOR (specs\ZEN_GOLD_LONDON.md).
- Without the momentum filter, the same pocket loses in training -> the "clean momentum" checklist item matters.
Verdict: WATCH (gold London 5m with momentum only); everything else FAIL.
