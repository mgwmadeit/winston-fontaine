# Tom Gratwicke (@itstomtrades) gold strategy: tested (2026-10-10)
Sources: IG @itstomtrades (182K, "Trading Gold for 7+ Years", only bio link = YouTube @itstomtrades). 24 YouTube transcripts in trading\tomtrades-yt\
(incl. "the ONE candle strategy +$700k", "1H pattern", fractal shifts, live backtests, full 8.5h course) + 5 IG reels.
Data: Databento GC.v.0 (most-traded gold contract) 1-min, Oct 2023 -> Oct 9 2026, $3.87. Code: bot\tom.py, bot\lab.py GC.

## His strategy ("one hourly candle", claims 77% win rate, ~1:2 RR, $1.2M)
1. Mark the previous 1H candle high/low. 2. The new 1H candle breaks it and runs ~20 min one way with no 50% pullback.
3. Around the halfway point of the hour (min 22-52), wait for a 1-min market-structure shift.
4. Entry at 50% of the breaking move, stop beyond the swing extreme, target 50% of the hourly extension.
Hours: 2nd hour of Asia -> 3rd/4th hour of London (~8 PM-7 AM ET). Context: reversals only in ranges (sell the upper half, buy the lower half).
He drops to 5-SECOND charts and uses a lot of discretion (weekly/daily candle behavior, "Wednesday London").

## Mechanical test on gold (MGC, $200 risk, fees + slippage)
| Version | Train (2 yrs) | Test (6 mo) | Last 6 months |
|---|---|---|---|
| His rules, his hours | 801 tr, 31.5% win, -263R | 183 tr, 36.6%, +34R | 235 tr, 24.7%, -62R |
| Same, ZERO fees | -68R | +47R | -40R |
| + range-only context | -105R | +38R | -27R |
| + range + wider stop + 1R target | 51% win, -37R | +4R | 50% win, -6.5R |
- Not close to 77%. The median stop is only $1.40 on gold (1-min noise), so it gets knocked out constantly. It only made money during the Oct 2025-Mar 2026 gold mania.
- On NQ it loses in every period.
- His edge, if real, is discretionary (5-second entries, multi-timeframe "candle behavior"). It can't be automated from his rules.

## Gold lab (15,248 strategies on gold)
- Gold is harder than NQ: 11.8% of strategies were positive (NQ: 31%), and random controls were 3.7%. 56 survived all 3 periods; 0 random ones did.
- ROBUST gold setups:
  - **Asia session 60-min Donchian-55 breakout** (9/16 settings positive in all periods): FOLLOW the Asia move, the opposite of Tom's fade.
  - **Fade 3x volume spikes on 5-min after 10 AM** (7/16): Tom's "snap back" idea, but only after huge volume spikes.
  - London 30-min Supertrend-flip fade (6/16).
- Added to the NQ prop farm (Topstep 50K sim): correlation -0.07. Net per eval goes from +$1,090-1,302 to +$1,343-1,639. Pass rate is about the same.
- CAVEAT: gold profits are mostly in 2026 (2023 -3R, 2024 +13R, 2025 +22R, 2026 +52R), during gold's huge rally. Paper-test before real money.

## How to add it
- Paper farm: add gold (Yahoo GC=F free data) running the Asia Donchian-55 breakout + after-10 volume-spike fade at half size, as a 4th/5th shadow soldier.
- Topstep allows MGC/GC. Keep gold at half size until the paper results confirm it.
