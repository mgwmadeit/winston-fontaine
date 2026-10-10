# 1) Our real ORB (v4: 5-min breakout, 10% ATR stop, hold to close, skip quiet opens) by period incl. the last 6 months
# 2) Do lab survivors ADD to it?  (a) as a second strategy (portfolio)  (b) as a filter on ORB days
import os, numpy as np, pandas as pd
from kron import MNQ
from published import orb2, rth
from run_published import load
HERE = os.path.dirname(os.path.abspath(__file__))
TRAIN_END, TEST_END = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-04-01")
per = lambda d: np.where(d < TRAIN_END, "train", np.where(d < TEST_END, "test", "recent"))

nq = load("NQ")
orb = orb2(nq, MNQ, mode="breakout", atr_stop=0.10)
orb["date"] = pd.to_datetime(orb["date"])
r = rth(nq); v5 = r[(r.index.hour == 9) & (r.index.minute < 35)].groupby(r[(r.index.hour == 9) & (r.index.minute < 35)].index.date).Volume.sum()
v5.index = pd.to_datetime(v5.index); rvol = v5 / v5.rolling(14).mean().shift()
orb["rvol"] = orb.date.map(rvol)
orb["per"] = per(orb.date)

def line(name, R, dates):
    out = [f"{name:44s}"]
    for p in ("train", "test", "recent"):
        x = R[per(dates) == p]; w = x[x > 0].sum(); l = -x[x < 0].sum()
        eq = np.cumsum(x); dd = (np.maximum.accumulate(eq) - eq).max() if len(x) else 0
        out.append(f"{p}: {len(x):4d}tr {x.sum():+7.1f}R PF {w/l if l else 0:4.2f} DD {dd:4.1f}R")
    print(" | ".join(out))

print("OUR ORB (1 trade/day, stop-order entry):")
line("ORB v4 all days", orb.R.values, orb.date)
k = orb.rvol >= 1
line("ORB v4 busy opens only (rvol>=1)", orb.R.values[k], orb.date[k])
rec = orb[orb.per == "recent"]
print("\nLast 6 months by month:", rec.groupby(rec.date.dt.to_period("M")).R.sum().round(1).to_dict())

# (a) portfolio: daily R of ORB + each survivor; keep ones that improve R/DD in EVERY period
tr = pd.read_parquet(os.path.join(HERE, "lab_trades.parquet")); tr["date"] = pd.to_datetime(tr["date"])
surv = pd.read_csv(os.path.join(HERE, "lab_survivors.csv")).set_index("id")
surv = surv[~surv.family.str.startswith("RANDOM")]
od = orb[orb.rvol >= 1].groupby("date").R.sum()
days = pd.Index(sorted(set(nq.index.date))).map(pd.Timestamp)
od = od.reindex(days, fill_value=0)

def score(daily):
    out = {}
    for p in ("train", "test", "recent"):
        x = daily[per(daily.index) == p].values; eq = np.cumsum(x); dd = (np.maximum.accumulate(eq) - eq).max()
        out[p] = (x.sum(), dd, x.sum() / dd if dd else 0)
    return out

base = score(od)
print("\nBASE (ORB busy opens):", {p: f"{v[0]:+.1f}R dd {v[1]:.1f} ratio {v[2]:.2f}" for p, v in base.items()})
rows = []
for sid, mrow in surv.iterrows():
    sd = tr[tr.id == sid].groupby("date").R.sum().reindex(days, fill_value=0)
    corr = np.corrcoef(od.values, sd.values)[0, 1]
    comb = score(od + 0.5 * sd)                                   # add the survivor at HALF size
    better = all(comb[p][2] > base[p][2] for p in base)
    rows.append(dict(id=sid, family=mrow.family, tf=mrow.tf, session=mrow.session, stop=mrow.stop, exit=mrow.exit, corr=round(corr, 2),
                     better_all=better, **{f"{p}_R": round(comb[p][0], 1) for p in base}, **{f"{p}_ratio": round(comb[p][2], 2) for p in base}))
A = pd.DataFrame(rows).sort_values("recent_ratio", ascending=False)
A.to_csv(os.path.join(HERE, "lab_addon_portfolio.csv"), index=False)
print(f"\n(a) Survivors that improve ORB's return/drawdown in ALL 3 periods (added at half size): {A.better_all.sum()} of {len(A)}")
print(A[A.better_all].head(25).to_string(index=False))

# (b) filters: take the ORB trade only if survivor family X fired the SAME direction earlier that morning (NY sessions)
print("\n(b) ORB filtered by 'same-direction signal earlier that day' (survivors in NY/NYAM, deduped by family+tf):")
fr = []
o2 = orb[orb.rvol >= 1].copy()
for (fam, tf), g in surv[surv.session.isin(["NY", "NYAM"])].groupby(["family", "tf"]):
    sid = g.index[0]; t = tr[tr.id == sid]
    # survivor signal must have ENTERED before the ORB entry (signal bar closed before -> no peeking)
    mm = pd.merge_asof(o2.sort_values("time")[["time"]].reset_index(), t.sort_values("ts")[["ts", "side"]].rename(columns={"ts": "time", "side": "sside"}),
                       on="time", direction="backward", allow_exact_matches=False)
    mm = mm[(mm.time.dt.date == pd.to_datetime(mm.time).dt.date)]
    sig_day = t.assign(d=t.ts.dt.date).set_index("ts")
    keep = pd.Series(False, index=o2.index)
    for _, rr in mm.iterrows():
        prior = t[(t.ts < rr.time) & (t.ts.dt.date == rr.time.date())]
        if len(prior) and prior.side.iloc[-1] == o2.loc[rr["index"], "side"]: keep[rr["index"]] = True
    if keep.sum() < 60: continue
    x = o2[keep]
    vals = {p: x[x.per == p].R.sum() for p in ("train", "test", "recent")}
    basev = {p: o2[o2.per == p].R.sum() for p in ("train", "test", "recent")}
    avg_up = all(x[x.per == p].R.mean() > o2[o2.per == p].R.mean() for p in vals)
    fr.append(dict(filter=f"{fam} tf{tf}", kept=len(x), of=len(o2), avgR_better_all=avg_up, **{p: round(v, 1) for p, v in vals.items()}))
F = pd.DataFrame(fr).sort_values("recent", ascending=False)
print("ORB busy-opens base:", {p: round(o2[o2.per == p].R.sum(), 1) for p in ("train", "test", "recent")})
print(F.to_string(index=False))
