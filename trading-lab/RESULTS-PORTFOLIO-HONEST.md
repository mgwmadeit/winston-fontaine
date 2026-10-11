# #1 All-robust portfolio + #2 more markets: HONEST out-of-sample test (2026-10-11). Code: bot\portfolio_all.py, lab.py ES
Selection on TRAIN only (Oct 2023-Sep 2025): groups with >=10/16 settings positive in train, best-train setting PF>=1.15, >=100 trades.
201 strategies (NQ 137, GC 40, ES 24). RANDOM controls selected the same way: 12.
| | TRAIN (picked) | TEST unseen (Oct25-Mar26) | RECENT unseen (Apr-Oct26) |
| ALL 201 | +12,186R (+23.6R/day) | +1,960R (+15.3/day) | -1,478R (-10.7/day) |
| NQ 137 | +9,442R | +1,649R | -781R |
| GC 40 | +1,655R | -85R | -329R |
| ES 24 | +1,089R | +396R | -368R |
| RANDOM 12 | +765R (~64R each) | +139R (~12 each) | -99R (~-8 each) |
Per strategy, the real picks ~= the random picks -> train-only mass selection finds LUCK/regime fit (2024 trend regime), not lasting edges.
ES lab (15,104 strategies): 11.5% positive (random 5.8%), 38 survivors vs 1 random.
## Consequences
- The 5 farm strategies were chosen using all 3 periods (look-ahead selection bias), so their backtests are optimistic. The LIVE PAPER farm is the only honest test.
- Didn't buy YM/RTY/CL/6E ($15-19): mass search in more markets = more lucky patterns.
- The money engine = prop payout structure (+EV even for a coin flip). Strategies just need to not be bad.
- Adopt the researcher vs AUDITOR split: the auditor rebuilds strategies from plain-English specs, tests on locked data + random controls, and only promotes what beats luck. Then live paper before real money.
