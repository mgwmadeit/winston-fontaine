# Strategy Lab: 15,136 strategies, ~10 million trades on REAL NQ data (2026-10-09)
Rebuilds Lil Fish's "10,000 strategies" test, but on Databento NQ futures 1-min data (he used free CFD data).
Data runs Oct 2023 to Oct 9 2026 (topped up today, $0.06). MNQ, $200 risk per trade, fees + slippage included.
Code: `bot\lab.py` (engine), `lab_score.py`, `lab_addon.py`. Output: `lab_results.csv`, `lab_survivors.csv`, `lab_addon_portfolio.csv`.

**Strategy recipe** = 46 signal families (EMA/MACD/RSI/Bollinger/Donchian/Supertrend/VWAP/volume spike/engulfing/inside bar/
PDH-PDL and ONH-ONL break or sweep/ORB 5-15-30-60/gap/first bar/3-bar momentum/big bar + FADE versions + RANDOM controls)
x 4 timeframes (5/15/30/60m) x 6 sessions (NY AM, NY all day, London, Asia, After-10 AM, After-10 all day)
x 4 stops (15pt, 40pt, 10% ATR, 25% ATR) x 4 exits (1R, 2R, hold to close, 60 min).

**Periods:** TRAIN Oct 2023-Sep 2025 (strategies picked here) | TEST Oct 2025-Mar 2026 (unseen) | RECENT = last 6 months, Apr-Oct 2026 (unseen).

## Headline results
- Only **31%** of strategies made money over 3 years. **18% of RANDOM coin-flip strategies also did** (pure luck).
- Picked on train, then still positive on test AND the last 6 months: **324 of 13,984 real strategies (2.3%)**, versus **7 of 1,152 random ones (0.6%)**. So real signals exist, but plenty of "winners" are luck. Only trust a strategy whose neighboring settings also work.
- Matches Lil Fish's findings: **NY AM is the best session, London is the worst, holding to the close beats quick targets, and tiny 15pt stops get eaten by fees** (only 17% of those are positive).

## OUR ORB: still working in the last 6 months
| | Train (2 yrs) | Test (6 mo) | Last 6 months |
|---|---|---|---|
| ORB v4, every day | +124.8R, PF 1.41 | +29.9R, PF 1.39 | **+29.4R, PF 1.38** |
| ORB v4, busy opens only | +101.2R, PF 1.60 | +17.3R, PF 1.41 | **+43.1R, PF 1.91, DD only 6.2R** |
Last 6 months by month: Apr -6.4, May +7.5, Jun +18.1, Jul -2.1, Aug +4.8, Sep +8.6, Oct (so far) -1.0.

## Add-ons that make the ORB better (robust: most neighboring settings work too)
Adding these at half size improved the ORB's return-to-drawdown in ALL 3 periods. They trade at different times, so their correlation with the ORB is about 0.
1. **ASIA session, 15-min ENGULFING candle (go with it)**, 7 PM-2 AM ET, flat by 2:55 AM. **12 of its 16 settings are positive in all 3 periods.** The most robust find. Night trades = bot only.
2. ASIA 15-min Donchian-20 breakout (7/16 settings) and ASIA 15-min Bollinger breakout (8/16).
3. NY 60-min **VWAP 2-sigma FADE** (price closes beyond 2 std of VWAP -> bet on the snap back), 7/16. Works **after 10 AM too (11/16 settings)**.
Filters ("only take the ORB if signal X agreed earlier") do NOT help once look-ahead is removed.

## After 10 AM only (when Moses wakes up late or is at work)
- After-10 is weaker than the open (27-32% of strategies positive vs 40% for NY AM). The edges are smaller (+0.07 to 0.16R per trade).
- Best after-10 options, all positive in all 3 periods:
  - **Late ORB:** price breaks the first 15-min range after 10 AM, 40pt stop, 2R target (about 8 trades/week, ~39% win rate, last 6 months +31.6R).
  - **60-min VWAP 2-sigma fade** (the most robust, 11/16 settings).
  - **60-min volume-spike breakout**, hold to close.
- Better answer: **let the bot take the 9:30 ORB automatically.** Then waking up late doesn't matter.

## Caveats
- 2 trades/day max per strategy, entry at the next bar open after the signal, stop is hit first if both stop and target fall in the same minute.
- Lab ORB results (2 trades/day, close-confirmed entry) are worse than our real ORB (1/day, stop-order entry). The details of execution matter.
- Next: test the add-ons in the eval / prop farm simulator, then paper-trade before real money.
