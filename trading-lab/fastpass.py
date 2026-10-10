# FAST-PASS LAB: can the bot pass a Topstep 50K in 2-4 days?
# Entry: 9:30 ORB (5-min opening range, breakout on 1-min bars, stop = 10% of 14-day ATR). Optional reversal if the first break fails.
# Exits tested: hold to close, fixed targets, chandelier trailing stop, profit LOCK (keep X% of the best open profit), partial + runner.
# Daily cap (Topstep 50% consistency -> fastest pass = 2 days of ~$1,500) + daily loss stop.
#   python fastpass.py
import numpy as np, pandas as pd, itertools
from numba import njit
from run_published import load

PV, TICK, FEE = 2.0, 0.25, 0.62                       # MNQ (sizing is by $ risk, so the instrument is just the price path)
TARGET, DD, CONS, MIN_DAYS = 3000, 2000, 0.50, 2


@njit(cache=False)
def trade(h, l, c, start, side, entry, sd, tgtR, mode, k, lock_at, lock_f, part_R, part_f, capR):
    """walks 1-min bars from start; returns (R, exit_index). side +1 long / -1 short. R excludes costs."""
    stop = entry - side * sd
    best = entry
    realized = 0.0; left = 1.0; took_part = False
    n = len(h)
    for j in range(start, n):
        hi = h[j]; lo = l[j]
        adverse = lo if side > 0 else hi
        fav = hi if side > 0 else lo
        # stop first (conservative)
        if (side > 0 and adverse <= stop) or (side < 0 and adverse >= stop):
            return realized + left * (stop - entry) * side / sd, j
        # targets: daily cap, hard target, partial
        favR = (fav - entry) * side / sd
        if capR > 0 and favR >= capR:
            return realized + left * capR, j
        if tgtR > 0 and favR >= tgtR:
            return realized + left * tgtR, j
        if part_R > 0 and not took_part and favR >= part_R:
            realized += part_f * part_R; left -= part_f; took_part = True
        # update trailing stop with this bar's extreme (applies from the next bar)
        if (side > 0 and hi > best) or (side < 0 and lo < best):
            best = hi if side > 0 else lo
        mfeR = (best - entry) * side / sd
        if mode == 1:                                   # chandelier: trail k * stop-distance behind the best price
            ns = best - side * k * sd
            if (side > 0 and ns > stop) or (side < 0 and ns < stop): stop = ns
        elif mode == 2 and mfeR >= lock_at:             # LOCK: keep lock_f of the best open profit
            ns = entry + side * lock_f * mfeR * sd
            if (side > 0 and ns > stop) or (side < 0 and ns < stop): stop = ns
        elif mode == 3:                                 # both: chandelier + lock
            ns = best - side * k * sd
            if mfeR >= lock_at:
                ns2 = entry + side * lock_f * mfeR * sd
                if (side > 0 and ns2 > ns) or (side < 0 and ns2 < ns): ns = ns2
            if (side > 0 and ns > stop) or (side < 0 and ns < stop): stop = ns
    return realized + left * (c[n - 1] - entry) * side / sd, n - 1


def prep():
    m = load("NQ")
    tod = m.index.hour * 60 + m.index.minute
    r = m[(tod >= 570) & (tod < 960)]
    D = r.groupby(r.index.date).agg(H=("High", "max"), L=("Low", "min"), C=("Close", "last"))
    pc = D.C.shift(); tr = pd.concat([D.H - D.L, (D.H - pc).abs(), (D.L - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().shift()
    days = []
    for d, g in r.groupby(r.index.date):
        if len(g) < 380 or np.isnan(atr.get(d, np.nan)): continue
        h, l, c, o = (g[x].values.astype(np.float64) for x in ("High", "Low", "Close", "Open"))
        days.append(dict(date=pd.Timestamp(d), o=o, h=h, l=l, c=c, orh=h[:5].max(), orl=l[:5].min(), sd=0.10 * atr[d]))
    return days


def day_pnl(dd, risk, ex, cap, rev, loss_stop):
    """$ result of one day: ORB (+ optional reversal), with the day's profit cap and loss stop."""
    h, l, c, o = dd["h"], dd["l"], dd["c"], dd["o"]; sd = dd["sd"]
    if sd < 8 * TICK: return 0.0
    cost_R = (2 * FEE + 2 * TICK * PV) / (sd * PV)     # fees + slippage per contract, in R
    day, trades = 0.0, 0
    side, i = 0, -1
    for j in range(5, 360):                             # first break of the opening range (no new entries after 15:30)
        up, dn = h[j] > dd["orh"], l[j] < dd["orl"]
        if up and dn: return 0.0
        if up or dn: side, i = (1 if up else -1), j; break
    while side != 0 and trades < (2 if rev else 1):
        entry = max(dd["orh"] + TICK, o[i]) if side > 0 else min(dd["orl"] - TICK, o[i])
        capR = (cap - day) / risk if cap else 0.0
        R, xi = trade(h, l, c, i, side, entry, sd, ex["tgt"], ex["mode"], ex["k"], ex["lock_at"], ex["lock_f"], ex["part_R"], ex["part_f"], capR)
        day += (R - cost_R) * risk; trades += 1
        if not rev or R > 0 or day <= -loss_stop or xi >= 330: break
        # reversal: stopped out -> take the opposite break of the range later in the day
        side = -side; i = -1
        for j in range(xi + 1, 360):
            if (side > 0 and h[j] > dd["orh"]) or (side < 0 and l[j] < dd["orl"]): i = j; break
        if i < 0: break
    return day


def evaluate(pnl, horizons=(2, 3, 4, 5, 10)):
    """start an eval on every day; returns pass % within each horizon, blow % within 4 days, median days to pass."""
    n = len(pnl); res = []
    for s in range(n - 12):
        bal = peak = 0.0; best = 0.0; nd = 0; out = None
        for i in range(s, min(n, s + 40)):
            p = pnl[i]
            if p == 0: continue
            nd += 1; bal += p; best = max(best, p)
            if bal <= peak - DD: out = ("blow", nd); break
            peak = max(peak, bal)
            if bal >= TARGET and best <= CONS * bal and nd >= MIN_DAYS: out = ("pass", nd); break
        res.append(out or ("open", nd))
    res = np.array(res, dtype=object)
    pas = np.array([r[0] == "pass" for r in res]); d = np.array([r[1] for r in res])
    out = {f"pass<={h}d": round(100 * (pas & (d <= h)).mean(), 1) for h in horizons}
    out["blow<=4d"] = round(100 * np.array([(r[0] == "blow") and r[1] <= 4 for r in res]).mean(), 1)
    out["pass_ever"] = round(100 * pas.mean(), 1); out["med_days"] = float(np.median(d[pas])) if pas.any() else np.nan
    return out


EXITS = {
    "hold to close":            dict(tgt=0., mode=0, k=0., lock_at=0., lock_f=0., part_R=0., part_f=0.),
    "target 2R":                dict(tgt=2., mode=0, k=0., lock_at=0., lock_f=0., part_R=0., part_f=0.),
    "target 4R":                dict(tgt=4., mode=0, k=0., lock_at=0., lock_f=0., part_R=0., part_f=0.),
    "trail 1.5x stop":          dict(tgt=0., mode=1, k=1.5, lock_at=0., lock_f=0., part_R=0., part_f=0.),
    "trail 2.5x stop":          dict(tgt=0., mode=1, k=2.5, lock_at=0., lock_f=0., part_R=0., part_f=0.),
    "lock 50% after +1R":       dict(tgt=0., mode=2, k=0., lock_at=1., lock_f=.5, part_R=0., part_f=0.),
    "lock 60% after +1.5R":     dict(tgt=0., mode=2, k=0., lock_at=1.5, lock_f=.6, part_R=0., part_f=0.),
    "lock 40% after +1R":       dict(tgt=0., mode=2, k=0., lock_at=1., lock_f=.4, part_R=0., part_f=0.),
    "trail 2.5x + lock 50%@2R": dict(tgt=0., mode=3, k=2.5, lock_at=2., lock_f=.5, part_R=0., part_f=0.),
    "half off @1R + trail 2x":  dict(tgt=0., mode=1, k=2., lock_at=0., lock_f=0., part_R=1., part_f=.5),
    "half off @1.5R + lock 50%":dict(tgt=0., mode=2, k=0., lock_at=1.5, lock_f=.5, part_R=1.5, part_f=.5),
}

if __name__ == "__main__":
    days = prep()
    dates = pd.Index([d["date"] for d in days])
    rows = []
    for (ename, ex), risk, cap, rev in itertools.product(EXITS.items(), (300, 500, 750, 1000), (0, 1500), (False, True)):
        pnl = np.array([day_pnl(d, risk, ex, cap, rev, loss_stop=risk * 1.2) for d in days])
        e = evaluate(pnl)
        rows.append(dict(exit=ename, risk=risk, cap=cap or "none", reversal=rev, avg_day=round(pnl.mean()), **e))
    df = pd.DataFrame(rows); df.to_csv("fastpass_results.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
    print(f"{len(days)} days. Topstep 50K: +$3,000, $2,000 trailing, 50% consistency (fastest = 2 days)\n")
    print(df.sort_values("pass<=4d", ascending=False).head(30).to_string(index=False))
    print("\nBEST PER EXIT STYLE (by pass within 4 days):")
    print(df.loc[df.groupby("exit")["pass<=4d"].idxmax()].sort_values("pass<=4d", ascending=False).to_string(index=False))
