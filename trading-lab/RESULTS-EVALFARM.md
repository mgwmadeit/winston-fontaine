# Eval Farm Calculator (2026-10-09): does buying evals pay at Moses's firms?
Code: bot\evalfarm.py (prices editable at the top). Output: bot\evalfarm_results.csv.
Method: real daily P&L of our strategies (NQ, Oct 2023 -> Oct 9 2026). Start an eval on EVERY trading day (708 starts), apply the firm's
target / trailing EOD drawdown / 50% consistency / min days / monthly fee, then funded: 5 good days -> payout (50% of profit, capped, split), up to 3 payouts.
Rules are from public 2026 guides and are APPROXIMATE (Topstep 50K $85/mo per Moses, Lucid Flex 25K $100 / 50K $136, TPT 25K $150 / 50K $170 + $130 PRO activation). Check them on the firm sites.
The funded-stage model is simplified, so treat the $ amounts as rough rankings, not promises.

## Bot rules
- Topstep: bots allowed through the TopstepX API (ProjectX, ~$29/mo). The bot must run on Moses's OWN computer (no VPS).
- Lucid: bots allowed (through Tradovate). No HFT or microscalping.
- Take Profit Trader: funded PRO accounts BAN automation, so TPT = manual (Telegram alerts) only.

## Results (3 years of starts; last-6-months starts in brackets)
| Strategy | Firm | Risk/trade | Pass % | Days to pass | Paid % | Net $ per eval |
|---|---|---|---|---|---|---|
| ORB + Asia engulf + VWAP fade | Topstep 50K | $400 | 33% [49%] | 15 | 23% | +$1,302 [+$1,703] |
| ORB + Asia engulf + VWAP fade | Topstep 50K | $200 | 52% [71%] | 26 | 41% | +$1,090 [+$1,543] |
| ORB + Asia engulf + VWAP fade | Lucid Flex 50K | $200 | 52% [71%] | 26 | 39% | +$924 [+$1,644] |
| After-10 only (late ORB + VWAP fade) | Topstep 50K | $600-800 | 34-37% | 9-10 | 20-23% | +$907 to +$1,080 |
| After-10 only | TPT 25K (manual) | $200 | 64% [77%] | 20 | 54% | +$283 |
| ORB only | Topstep 50K | $300 | 18% [25%] | 19 | 14% | +$354 |
| Lucid Flex 25K with ORB only | any | any | <=10% | | | LOSES |

## Takeaways
1. **Best: Topstep 50K + the 3-strategy combo (ORB + night Asia engulfing + 60-min VWAP fade) at $200-400 risk.** About 1 in 2-3 evals pass in 3-5 weeks.
2. **Lil Fish's "pass or blow in 1 day" (big size) does NOT fit our strategies.** At $800-1000 risk, the pass rate drops to 6-10%. Moderate size wins.
3. **After-10 only is viable** (late ORB + VWAP fade). Good for days Moses is at work.
4. The ORB alone passes too slowly. The add-ons (more trades, uncorrelated) are what make farming work.
5. HONEST CAVEAT: the add-ons were picked partly because they were positive in the last 6 months, so the [last 6m] numbers are flattering. The 3-year numbers are the fairer guide. Paper trade first.
