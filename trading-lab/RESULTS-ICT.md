# ICT (Inner Circle Trader) models vs 3 years of data (2026-10-11). Code: bot\ict.py. Transcripts: trading\ict-yt\
Videos: Silver Bullet (tRq1hyGGtl4, 1.58M views), 2022 Mentorship ep 2-4, FVG core content, OTE primer, Judas swing, NY killzone.
Coded mechanically: FVG = 3-candle gap; stop beyond the swing that launched it; liquidity = nearest old high/low in the prior 60 min; 10-handle (NQ) / $3 (gold) framework rule; 1-min accurate fills, $200 risk, fees.
## Silver Bullet (03-04, 10-11, 14-15 ET), 16 variants per market (1m/5m x edge/mid entry x liquidity/2R target x 10-handle rule)
- NQ 1m: ALL lose in training (-60 to -192R), test/recent about flat to negative. NQ 5m: all lose (PF 0.70-0.97).
- Gold 1m: all lose badly (-270 to -396R train). Gold 5m: all lose.
- By window (NQ 1m): 3 AM -98R/+9R/-20R; 10 AM -8R/-12R/+17R; 2 PM -85R/-1R/-7R. No window holds up.
## 2022 model (raid of the 6:00-8:30 range after 8:30 -> MSS -> FVG entry) / OTE 0.705
- NQ: few trades, ~flat (-0.3R to +11R train, mixed after). Not an edge.
- Gold 1m FVG entry: train -41R, test +16R, recent +15R (2R target): only works in the 2025-26 gold trend. NOT robust.
## Verdict
As mechanical rules, ICT's models don't hold up on NQ or gold. ICT says the key is knowing the "draw on liquidity" (daily bias), which is discretionary and can't be coded from his rules.
His strongest statement ("every trading day this forms") is true: FVGs form daily. Trading every one loses after costs.
