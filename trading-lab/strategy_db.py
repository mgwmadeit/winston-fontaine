# STRATEGY MEMORY DATABASE: every strategy we've tested, with its verdict, in one table (trading\STRATEGY-DB.csv).
# The research loop reads this first so nothing gets re-tested and new ideas build on what worked (seb.ai's "remembers every mistake" idea).
#   python strategy_db.py        -> rebuilds STRATEGY-DB.csv from the lab files + the hand-tested list below
import os, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "STRATEGY-DB.csv")

MANUAL = [  # name, market, source, verdict, key numbers, file
    ("K-Ron method (sweep + SMT, setup D)", "NQ", "@kroyces", "FAIL", "3 yrs -66R, 1/12 quarters positive", "RESULTS-v3-3years.md"),
    ("ORB 5-min 10% ATR (OLD 5-min stop check)", "NQ", "Zarattini paper", "INVALID", "+184R was inflated by the lenient entry-bar stop rule", "RESULTS-FASTPASS.md"),
    ("ORB 5-min, 1-min accurate, 15% ATR, hold", "NQ", "Zarattini paper", "THIN EDGE", "+42R / +5.5R / +12R, PF ~1.1", "RESULTS-FASTPASS.md"),
    ("DMC market-open call", "NQ", "Dumb Money Concepts", "FAIL", "47% right (claimed 90%)", "RESULTS-DMC.md"),
    ("Chermane ICT midnight open", "NQ", "Chermane Trades", "FAIL", "~break-even; 70% claim really ~55%", "RESULTS-CHERMANE.md"),
    ("Max Options 15-min ORB", "NQ", "Max Options Trading", "WEAK", "his way ~break-even", "RESULTS-MAX.md"),
    ("TheTradingLama fibs 0.786/0.236", "NQ", "@thetradinglama", "FAIL", "no reliable edge (public version)", "RESULTS-LAMA.md"),
    ("BPC VWAP rejection/overextension", "NQ", "BPC Trades", "FAIL", "loses on 3 yrs", "PROP-PLAN.md"),
    ("After-10 IB breakout / VWAP pullback", "NQ", "classic", "FAIL", "loses on 3 yrs", "PROP-PLAN.md"),
    ("Tom one-hourly-candle reversal", "GC", "@itstomtrades", "FAIL", "31% win, -263R train, -62R last 6 mo", "RESULTS-TOMTRADES-GOLD.md"),
    ("Asian range 20-03 breakout (1R)", "GC", "gold_lab", "ROBUST-ISH", "4/6 settings positive all periods, 53-63% win at 1R", "RESULTS-TOMTRADES-GOLD.md"),
    ("Supply/demand zones + EMA 8/20 cross", "NQ/GC", "Moses", "MIXED", "NQ 15m hold +14/+9/-3R few trades; gold loses", "RESULTS-MONEY-ENGINE.md"),
    ("Opening relative-volume filter on ORB", "NQ", "order flow study", "HELPS", "skip quiet opens, consistent in both periods", "RESULTS-ORDERFLOW.md"),
    ("Prop payout structure (eval farming)", "any", "Lil Fish", "MONEY ENGINE", "+$300-850 net/eval even at a near-zero edge", "RESULTS-MONEY-ENGINE.md"),
    ("ICT Silver Bullet (3 windows, FVG retrace)", "NQ/GC", "ICT YouTube", "FAIL", "all 32 variants lose; NQ 1m -60 to -192R train", "RESULTS-ICT.md"),
    ("ICT 2022 model (raid -> MSS -> FVG) / OTE", "NQ/GC", "ICT YouTube", "FAIL", "NQ ~flat; gold +16/+15R only in 2025-26, -41R train", "RESULTS-ICT.md"),
    ("Mass-selected portfolio (201 lab strategies, train-only pick)", "NQ/GC/ES", "lab", "FAIL", "unseen: +1,960R then -1,478R; real picks ~= random picks (luck)", "RESULTS-PORTFOLIO-HONEST.md"),
]


def lab_rows(path, market):
    if not os.path.exists(path): return []
    r = pd.read_csv(path); r = r[~r.random]
    rows = []
    for (fam, tf, ses), g in r.groupby(["family", "tf", "session"]):
        k = int(((g.train_totR > 0) & (g.test_totR > 0) & (g.recent_totR > 0)).sum())
        b = g.sort_values("full_totR", ascending=False).iloc[0]
        verdict = "ROBUST" if k >= 7 else ("PROMISING" if k >= 4 else ("FAIL" if (g.full_totR > 0).mean() < 0.3 else "WEAK"))
        rows.append((f"{fam} {tf}m {ses}", market, "lab (auto)", verdict,
                     f"{k}/16 settings positive in all 3 periods; best {b.stop}/{b.exit}: {b.train_totR:+.0f}/{b.test_totR:+.0f}/{b.recent_totR:+.0f}R", os.path.basename(path)))
    return rows


if __name__ == "__main__":
    rows = MANUAL + lab_rows(os.path.join(HERE, "lab_results.csv"), "NQ") + lab_rows(os.path.join(HERE, "lab_results_GC.csv"), "GC")
    df = pd.DataFrame(rows, columns=["strategy", "market", "source", "verdict", "numbers", "file"])
    order = {"MONEY ENGINE": 0, "ROBUST": 1, "ROBUST-ISH": 2, "THIN EDGE": 3, "HELPS": 4, "PROMISING": 5, "MIXED": 6, "WEAK": 7, "FAIL": 8, "INVALID": 9}
    df = df.sort_values(["verdict", "market"], key=lambda c: c.map(order) if c.name == "verdict" else c)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} strategies in the memory DB -> {os.path.abspath(OUT)}")
    print(df.verdict.value_counts().to_string())
    print(df[df.verdict.isin(["ROBUST", "ROBUST-ISH", "THIN EDGE", "MONEY ENGINE"])].to_string(index=False))
