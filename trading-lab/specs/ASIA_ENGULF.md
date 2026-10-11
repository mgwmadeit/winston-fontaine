# SPEC: Asia session engulfing candle (farm strategy "ASIA" / PHANTOM)
Market: NQ (micro MNQ)
Source: researcher's 15,000-strategy lab (engulfing, 15-min, ASIA)

## Entry rules
1. 15-minute candles starting on the quarter hour, New York time. Only candles that CLOSE between 7:00 PM and 2:00 AM ET count.
2. Signal on a candle's CLOSE: bullish engulfing = this candle closes above its open, the previous candle closed below its open, this close > previous open, and this open < previous close. Bearish = the mirror image.
3. Enter in the signal's direction at the open of the next 1-minute bar.
4. Max 2 trades per trading day (the day starts at 6 PM ET), and no new trade while one is open.

## Exit rules
- Stop: 10% of the 14-day average daily range of the regular session (9:30-4:00 ET true range), measured from entry.
- Target: 2x the stop distance (2R).
- Time exit: close at 2:55 AM ET if still open.

## Researcher's claimed results (lab, $200 risk, whole-contract sizing)
- 12 of 16 stop/exit variants positive in all 3 periods. This variant: TRAIN +37R, TEST +20R, RECENT +31R.

## Known doubts
- Picked AFTER seeing all 3 periods (look-ahead selection bias). The 201-strategy honest test showed train-only picks behave like random ones.
