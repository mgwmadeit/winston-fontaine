# Scores every lab strategy in 3 periods and picks survivors.  python lab_score.py
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
TRAIN_END, TEST_END = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-04-01")

meta = pd.read_csv(os.path.join(HERE, "lab_meta.csv"))
tr = pd.read_parquet(os.path.join(HERE, "lab_trades.parquet"))
tr["date"] = pd.to_datetime(tr["date"])
tr["per"] = np.where(tr.date < TRAIN_END, "train", np.where(tr.date < TEST_END, "test", "recent"))
weeks = {"train": 104, "test": 26, "recent": 27}

def agg(g):
    R = g.R.values; w = R[R > 0].sum(); ls = -R[R < 0].sum(); eq = np.cumsum(R)
    return pd.Series({"n": len(R), "win": (R > 0).mean() * 100, "totR": R.sum(), "avgR": R.mean(),
                      "pf": w / ls if ls else np.nan, "ddR": (np.maximum.accumulate(eq) - eq).max()})

st = tr.groupby(["id", "per"]).apply(agg).unstack("per")
st.columns = [f"{p}_{k}" for k, p in st.columns]
res = meta.set_index("id").join(st).fillna({c: 0 for c in st.columns if c.endswith(("_n", "_totR"))})
res["full_totR"] = res[["train_totR", "test_totR", "recent_totR"]].sum(axis=1)
res["trades_per_week"] = (res.train_n + res.test_n + res.recent_n) / 157
res["random"] = res.family.str.startswith("RANDOM")
res.to_csv(os.path.join(HERE, "lab_results.csv"))

# Survivors: picked on TRAIN only, then must ALSO be positive on unseen TEST and on the RECENT 6 months
pick = (res.train_n >= 100) & (res.train_avgR > 0.03) & (res.train_pf > 1.1)
surv = pick & (res.test_totR > 0) & (res.recent_totR > 0) & (res.test_n >= 15) & (res.recent_n >= 15)
print(f"{len(res)} strategies, {int(res[['train_n','test_n','recent_n']].sum().sum()):,} trades")
print(f"Positive over full 3 yrs: {(res.full_totR>0).mean()*100:.1f}%   | random controls positive: {(res[res.random].full_totR>0).mean()*100:.1f}%")
print(f"Good on TRAIN: {pick.sum()}  -> still good on TEST + RECENT: {surv.sum()}")
print(f"  random controls: good on train {(pick & res.random).sum()}/{res.random.sum()}, survived {(surv & res.random).sum()}")
real = res[~res.random]
print(f"  real strategies: good on train {(pick & ~res.random).sum()}/{len(real)}, survived {(surv & ~res.random).sum()}")
print("\nBY FAMILY (mean R per trade over full period, % of variants positive):")
fam = real.assign(full_avg=real.full_totR / (real.train_n + real.test_n + real.recent_n)).groupby("family").agg(
    variants=("full_totR", "size"), pos_pct=("full_totR", lambda x: (x > 0).mean() * 100), mean_avgR=("full_avg", "mean"),
    survivors=("full_totR", lambda x: surv[x.index].sum()))
print(fam.sort_values("mean_avgR", ascending=False).round(3).to_string())
for col in ("tf", "session", "stop", "exit"):
    print(f"\nBY {col.upper()}:", real.groupby(col).full_totR.apply(lambda x: f"{(x>0).mean()*100:.0f}% positive").to_dict())
cols = ["family", "tf", "session", "stop", "exit", "trades_per_week", "train_n", "train_win", "train_avgR", "train_pf", "test_totR", "test_pf", "recent_totR", "recent_pf", "full_totR"]
S = res[surv].sort_values("recent_totR", ascending=False)
S.to_csv(os.path.join(HERE, "lab_survivors.csv"))
print(f"\nTOP 40 SURVIVORS (sorted by last-6-month R):")
print(S[cols].head(40).round(2).to_string())
print("\nORB sanity check (orb5_break, tf5, NY, atr10, hold):")
print(res[(res.family == "orb5_break") & (res.tf == 5) & (res.session == "NY") & (res.stop == "atr10") & (res.exit == "hold")][cols].round(2).to_string())
