# Raising the eval pass rate (2026-10-10): code bot\eval_opt.py, output bot\eval_opt_results.csv
Topstep 50K rules (+$3,000, $2,000 EOD trailing, 50% consistency, $85/mo). Our real daily results, an eval started on every day (708 starts).
Research (Track360, NexusFi, TradeZella, CurvedTrading guides): most evals die on the drawdown, not the target. People who pass risk a small slice of the room.

| Sizing | Pass in 2 mo | 4 mo | 1 yr | Median days | Fees per PASS |
|---|---|---|---|---|---|
| $400 fixed | 33% | 35% | 35% | 16 | $292 |
| $200 fixed (farm lane A) | 45% | 57% | 58% | 27 | $272 |
| $150 fixed | 40% | 64% | 67% | 35 | $282 |
| **$100 fixed** | 26% | **66%** | **94%** | 66 | $333 |
| **$100 fixed, NQ + gold half** | 32% | **73%** | **94%** | 58 | $309 |
| room-% sizing (10-25% of room) | worse than fixed | | | | |
| start $100 -> step up after +$750/1,000 | worse (trailing floor follows you) | | | | |

Takeaways
1. 90%+ pass is real with $100 risk/trade (about 1 MNQ on the ORB), but it takes ~3 months. Fees per pass are about the same (~$270-330) at every size, so the high pass rate doesn't cost more, it just takes longer.
2. Fast AND 80% is not possible with this edge. That needs a stronger strategy, not better sizing.
3. Don't size up after a cushion on a trailing drawdown. Keep size fixed until funded.
4. Farm now has lane S (SAFE): $100 risk, NQ + gold (gold half size), to prove it live.
5. Best plan: run several $100 evals staggered (start a new one every 2-3 weeks) so passes arrive steadily.
