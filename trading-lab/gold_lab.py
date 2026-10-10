# GOLD-SPECIFIC session strategies (MGC micro gold, $200 risk, fees + 1 tick stop slippage), scored train / test / last 6 months.
#   A. Opening-range breakout at gold's own key opens: Asia 20:00, London 03:00, COMEX 08:20, NY 09:30 ET
#   B. Asian-range breakout: range 20:00-03:00 ET, trade the first break during London/NY
#   C. Fade versions of both (Tom-style snap-back)
#   python gold_lab.py
import numpy as np, pandas as pd, itertools
from run_published import load

PV, TICK, FEE, RISK = 10.0, 0.10, 0.82, 200.0
TRAIN_END, TEST_END = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-04-01")

m = load("GC")
t = m.index; tod = (t.hour * 60 + t.minute).values
tday = (t + pd.Timedelta(hours=6)).normalize().tz_localize(None)
O, H, L, C = (m[k].values for k in ("Open", "High", "Low", "Close"))
# daily ATR (full session) known before the day
D = m.assign(td=tday).groupby("td").agg(h=("High", "max"), l=("Low", "min"), c=("Close", "last"))
pc = D.c.shift(); tr = pd.concat([D.h - D.l, (D.h - pc).abs(), (D.l - pc).abs()], axis=1).max(axis=1)
ATR = tr.rolling(14).mean().shift()
day_ids = pd.Index(tday)
groups = pd.Series(np.arange(len(m))).groupby(tday).agg(["min", "max"])


def minute_index(lo, hi, start_tod, length):
    """indices in [lo,hi] whose tod is in [start, start+length) (handles midnight wrap)"""
    tt = tod[lo:hi + 1]; end = (start_tod + length) % 1440
    sel = (tt >= start_tod) & (tt < start_tod + length) if start_tod + length <= 1440 else (tt >= start_tod) | (tt < end)
    return lo + np.flatnonzero(sel)


def sim(i, side, stop, tgt, last):
    """walk from bar i (entry bar, stop-only on entry bar) to last; returns exit price"""
    for j in range(i, last + 1):
        if side > 0:
            if L[j] <= stop: return stop - TICK, j
            if j > i and tgt is not None and H[j] >= tgt: return tgt, j
        else:
            if H[j] >= stop: return stop + TICK, j
            if j > i and tgt is not None and L[j] <= tgt: return tgt, j
    return C[last], last


def run(kind, start, length, trade_until, mode="break", stop_k=0.10, rr=None, flat=None, min_range_atr=0.0):
    out = []
    for td, (lo, hi) in groups.iterrows():
        a = ATR.get(td, np.nan)
        if np.isnan(a): continue
        rng_idx = minute_index(lo, hi, start, length)
        if len(rng_idx) < length * 0.6: continue
        rh, rl = H[rng_idx].max(), L[rng_idx].min()
        if rh - rl < min_range_atr * a: continue
        after = np.arange(rng_idx[-1] + 1, hi + 1)
        tt = tod[after]
        ok = after[np.isin(tt, trade_until)] if isinstance(trade_until, np.ndarray) else after
        if len(ok) == 0: continue
        last = ok[-1] if flat is None else after[np.flatnonzero(np.isin(tod[after], flat))[0]] if np.isin(tod[after], flat).any() else hi
        for i in ok:
            up, dn = H[i] > rh, L[i] < rl
            if up and dn: break
            if not (up or dn): continue
            brk = 1 if up else -1
            side = brk if mode == "break" else -brk
            entry = (max(rh + TICK, O[i]) if up else min(rl - TICK, O[i])) if mode == "break" else C[i]
            sd = stop_k * a if mode == "break" else max(stop_k * a, abs((H[i] if up else L[i]) - entry) + TICK)
            stop = entry - side * sd
            tgt = entry + side * rr * sd if rr else None
            q = int(RISK // (sd * PV))
            if q < 1: break
            ex, j = sim(i, side, stop, tgt, max(last, i))
            pnl = ((ex - entry) * side * PV - 2 * FEE) * q
            out.append((td, side, pnl / RISK)); break
    return pd.DataFrame(out, columns=["date", "side", "R"])


def score(df):
    if df.empty: return None
    per = np.where(df.date < TRAIN_END, "train", np.where(df.date < TEST_END, "test", "recent"))
    r = {}
    for p in ("train", "test", "recent"):
        x = df.R[per == p]; w = x[x > 0].sum(); l = -x[x < 0].sum()
        r[p] = (len(x), x.sum(), w / l if l else 0, (x > 0).mean() * 100 if len(x) else 0)
    return r


if __name__ == "__main__":
    rows = []
    rng = lambda a, b: np.array([x % 1440 for x in range(a, b)])
    OPENS = {"Asia 20:00": (1200, rng(1200, 1200 + 360), rng(180, 181)), "London 03:00": (180, rng(180, 180 + 300), rng(955, 956)),
             "COMEX 08:20": (500, rng(500, 500 + 220), rng(955, 956)), "NY 09:30": (570, rng(570, 570 + 300), rng(955, 956))}
    for (name, (st, until, flat)), ln, mode, sk, rr in itertools.product(OPENS.items(), (5, 15, 30, 60), ("break", "fade"), (0.10, 0.20), (None, 1.0, 2.0)):
        r = score(run(name, st, ln, until, mode=mode, stop_k=sk, rr=rr, flat=flat))
        if r: rows.append(dict(setup=f"{name} ORB{ln} {mode}", stop=sk, target=rr or "hold", **{f"{p}_{k}": v for p in r for k, v in zip(("n", "R", "pf", "win"), r[p])}))
    # Asian range (20:00-03:00) breakout / fade during London + NY
    for mode, sk, rr in itertools.product(("break", "fade"), (0.10, 0.20), (None, 1.0, 2.0)):
        r = score(run("AsiaRange", 1200, 420, rng(180, 660), mode=mode, stop_k=sk, rr=rr, flat=rng(955, 956)))
        if r: rows.append(dict(setup=f"Asian range 20-03 {mode}", stop=sk, target=rr or "hold", **{f"{p}_{k}": v for p in r for k, v in zip(("n", "R", "pf", "win"), r[p])}))
    R = pd.DataFrame(rows)
    R["all3"] = (R.train_R > 0) & (R.test_R > 0) & (R.recent_R > 0)
    R.to_csv("gold_lab_results.csv", index=False)
    pd.set_option("display.width", 250)
    print(f"{len(R)} gold session setups tested; positive in all 3 periods: {R.all3.sum()}")
    print(R.sort_values(["all3", "train_R"], ascending=False).head(30).round(2).to_string(index=False))
    g = R.groupby("setup").all3.sum().sort_values(ascending=False)
    print("\nsettings positive in all 3 periods, per setup (out of 6):\n" + g.head(15).to_string())
