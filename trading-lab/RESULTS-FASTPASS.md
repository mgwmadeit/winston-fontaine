# Fast-pass research (2026-10-10): pass Topstep 50K in 2-4 days?  Code: bot\fastpass.py, results bot\fastpass_results.csv, fastpass_honest.csv
## CRITICAL CORRECTION: the ORB was overstated
published.orb2 (and propfarm's old strat_orb) only counted a CLOSE beyond the stop on the 5-min entry bar, so it missed stop wicks inside the first 5 minutes.
With 1-minute-accurate stops: ORB 10% ATR = +15.8R train / +2.5R test / -2.3R last 6 mo (was +124.8 / +29.9 / +29.4).
Best accurate ORB = 15% ATR stop: +41.9R / +5.5R / +12.4R (PF ~1.1, thin). Every result built on orb2 (RESULTS-v4-ORB, eval farm, one_contract, PROP-PLAN) is too optimistic.
The lab.py strategies (Asia engulf, VWAP fade, gold) were always 1-min accurate.
propfarm.py strat_orb FIXED -> 1-min stops, 15% ATR (backup: propfarm_backup_pre_orbfix.py).

## Fast-pass results (Topstep 50K, consistency 50% -> fastest = 2 days of ~$1,500)
- Exits tested: hold, 2R/4R targets, chandelier trail 1.5x/2.5x, lock 40-60% of open profit, half off at 1R/1.5R + trail/lock, reversal entry, $1,550 daily cap.
- Best: ORB(15%) + Asia + VWAP + gold(half), $1,000-1,250 risk, half off at 1R + trail 2x, cap $1,550 -> pass <=4 days ~18-20%, ever ~27-29%, blow <=4 days ~53-62%.
- ORB one-trade daily bracket ($1,250 risk, 15% stop, +$1,550 target): day win 47%, pass <=4d 27.5%, ever 35%.
- Profit lock raises the win rate (33% -> ~52%) but barely changes the pass rate.
- PURE COIN FLIP benchmark at $1,500/day with a $1,550 cap: pass <=4 days 41.5%, ever 49%. Fast passing = winning 2 days before losing 2.
- For 70-80% in 2-4 days you need a ~65-70% daily win rate at 1:1. Not found mechanically. Lil Fish: 5/10 passed, 16/26 blown overall = coin-flip math.
## Next leads
- Hunt for a 1:1 setup with 60%+ win rate as the single daily bracket (gold Asian-range break 1R had 53-63%; Asia engulf 1R ~54%).
- Lucid Pro: no consistency rule in the eval -> a 1-day pass is possible. Model its rules.
- Re-run the eval farm and one-contract numbers with the accurate ORB.
