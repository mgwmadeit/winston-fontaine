# SPEC: Zen Model, gold, London (sweep of previous 1H candle + inverse FVG)
Market: GC (micro MGC)
Source: Zen Trades PDFs ("The Zen Model", setup rating guide, pre-trade checklist)

## Entry rules
1. 5-minute candles, New York time. Only consider sweeps on candles starting between 2:00 AM and 5:00 AM ET. One trade per day max.
2. Reference = the previous COMPLETED clock-hour (1H) candle's high and low.
3. SWEEP: a 5-min candle trades below the reference low (-> look for LONGS) or above the reference high (-> SHORTS). Track the extreme price reached after the sweep.
4. Within the next 60 minutes, find a fair value gap formed IN the sweep direction (for longs: a bearish gap = candle high < the high-to-low of the candle two bars earlier, i.e. high[t] < low[t-2]; zone = high[t]..low[t-2]).
5. INVERSE FVG confirmation: a later 5-min candle whose BODY (min of open/close for longs) closes completely beyond the far edge of that gap, AND whose range is at least 1.2x the average range of the last 20 candles (clean momentum).
6. DISCOUNT rule: for longs, the entry (gap top) must be at or below the midpoint between the sweep extreme and the reference high (mirror for shorts).
7. Entry: limit order at the flipped gap edge (gap top for longs), must fill within the next 30 candles (5-min) and before the target is touched.

## Exit rules
- Stop: 1 tick beyond the sweep extreme.
- Target (test all three): (a) the opposite side of the reference 1H candle, (b) 1R, (c) 2R.
- Time exit: close after 240 minutes if still open.

## Researcher's claimed results (bot\zen.py, $200 risk, whole contracts)
- target 1R: TRAIN 42 trades 66.7% +9.3R | TEST 15 trades 80% +7.6R | RECENT 12 trades 66.7% +2.9R
- target ref: +7.6 / +13.2 / +1.7R. target 2R: +2.6 / +15.1 / +5.0R.

## Known doubts
- 1 promising pocket out of 96 variants tested -> could be multiple-testing luck. Very small samples.
- The same setup WITHOUT the momentum filter loses in training.
