# Where the money is (2026-10-10). Code: bot\portfolio_daily.py, bot\sd_ema.py
## All robust strategies together (1-min accurate), 1 micro each, Oct 2023 - Oct 2026
NQ ORB 15% $3.7/day, NQ Asia engulf $9.6, NQ VWAP fade $5.4, NQ Asia supertrend -$2.6 (drop it), GC Asia breakout $2.8, GC spike fade $5.3, GC NYAM supertrend $2.5.
All 7: $27/day per micro-set, 44% green days, max DD $4.7K. To average $500/day you'd need ~20 micros each, with a ~$94K drawdown. Not prop-account sized.
## Moses's supply/demand + EMA 8/20 (coded: base before a >1.5-2.5x ATR impulse, first return, 5m EMA 8/20 cross)
NQ 15m zones, hold: +14R / +9R / -3R (70/15/14 trades). Gold loses. Few trades, not convincing (zone rules are subjective).
## THE MONEY ENGINE = prop payout structure (net $ per eval bought, our 6 strategies vs a zero-edge coin flip at the same daily size)
| size | Topstep ours | Topstep coin | LucidDaily ours | LucidDaily coin |
| x2 micros | +$362 | +$393 | +$402 | +$226 |
| x3 | +$392 | +$587 | +$429 | +$298 |
| x5 | +$378 | +$244 | +$458 | +$330 |
The structure is a free option (you lose the fee; the firm eats the drawdown; you withdraw the upside). Positive even for a coin flip. Our strategies add a bit on LucidDaily.
Plan: volume eval farming (~10/week, ~+$400 average each, high variance), bot on every account staggered, withdraw ASAP, buy evals only on sale, firms = LucidDaily + Topstep (+ FundedNext to model).
Caveats: simplified payout and drawdown models (Lucid funded drawdown trails intraday; my model trails end-of-day), firm fine print, account limits.
Bot rules: Topstep = TopstepX API from own PC; Lucid = allowed via Tradovate/API, no HFT/microscalping; FundedNext = allowed, no latency abuse/cross-person copying (third-party sources; confirm on the official pages).

## Firm comparison (2026-10-10, bot\firms_compare.py; fee x1.3 for resets; P(pass) x avg funded payout - fee)
| firm | size | pass | avg funded payout | NET/eval (ours) | NET/eval (coin flip) |
| FundedNext Rapid 50K ($150, no challenge consistency) | x3 | 42% | $2,153 | +$710 | +$372 |
| FundedNext Rapid 50K | x5 | 44% | $2,397 | +$854 | +$458 |
| FundedNext Rapid 25K ($80) | x2 | 46% | $1,163 | +$429 | +$182 |
| Topstep 50K ($85) | x3 | 31% | $1,928 | +$479 | +$453 |
| LucidDaily 50K ($150) | x3 | 31% | $2,061 | +$435 | +$523 |
| FundedNext Legacy 50K ($165) | x2 | 26% | $1,453 | +$169 | +$170 |
PICK for $100/week: FundedNext Rapid 25K (1/wk), move to Rapid 50K after payouts. Funded Rapid has 40% consistency + small payout caps ($800/$1,500).
Sources: fundednext.com legacy/terms, helpfutures.fundednext.com, pipback, damnpropfirms, tradetanto.
