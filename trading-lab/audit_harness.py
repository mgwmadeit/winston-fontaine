# AUDIT HARNESS: the neutral toolbox the strategy-auditor agent uses. It contains NO strategy logic, only data, fills, costs, random controls, scoring.
#   from audit_harness import load_1m, bars, fill_and_exit, cost_R, random_controls, score, PERIODS
import numpy as np, pandas as pd
from run_published import load

SPECS = {"NQ": dict(pv=2.0, tick=0.25, fee=0.62), "GC": dict(pv=10.0, tick=0.10, fee=0.82), "ES": dict(pv=5.0, tick=0.25, fee=0.62)}   # micros
PERIODS = {"TRAIN": ("2023-10-01", "2025-10-01"), "TEST": ("2025-10-01", "2026-04-01"), "RECENT": ("2026-04-01", "2026-10-12"), "FORWARD": ("2026-10-12", "2100-01-01")}


def load_1m(sym):
    """1-min bars (New York time, roll days removed): Open High Low Close Volume"""
    return load(sym)


def bars(m1, minutes, offset="0min"):
    """resample to N-minute bars; index = bar START time (the bar is only known at start + N minutes)"""
    return m1.resample(f"{minutes}min", offset=offset).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()


def fill_and_exit(m1, entry_time, side, stop, target=None, exit_time=None, limit=None, expire_time=None):
    """1-MINUTE accurate trade. side +1/-1. Market entry at the first 1-min bar at/after entry_time (its open), or a LIMIT that must be touched
    before expire_time. Stop checked first in every bar (incl. the fill bar for limits). Exit at target/stop or the close of the bar at exit_time.
    Returns dict(entry, exit, entry_ts, exit_ts) or None if not filled."""
    idx = m1.index; i = int(idx.searchsorted(pd.Timestamp(entry_time)))
    if i >= len(m1): return None
    H, L, O, C = m1.High.values, m1.Low.values, m1.Open.values, m1.Close.values
    if limit is None:
        entry = O[i]; start = i
    else:
        end_f = int(idx.searchsorted(pd.Timestamp(expire_time))) if expire_time is not None else len(m1)
        start = None
        for j in range(i, min(end_f, len(m1))):
            if (side > 0 and L[j] <= limit) or (side < 0 and H[j] >= limit): start = j; break
        if start is None: return None
        entry = limit
    last = int(idx.searchsorted(pd.Timestamp(exit_time), side="right")) - 1 if exit_time is not None else len(m1) - 1
    last = max(last, start)
    for j in range(start, last + 1):
        if (side > 0 and L[j] <= stop) or (side < 0 and H[j] >= stop): return dict(entry=entry, exit=stop, entry_ts=idx[start], exit_ts=idx[j], stopped=True)
        if target is not None and j > start and ((side > 0 and H[j] >= target) or (side < 0 and L[j] <= target)):
            return dict(entry=entry, exit=target, entry_ts=idx[start], exit_ts=idx[j], stopped=False)
    return dict(entry=entry, exit=C[last], entry_ts=idx[start], exit_ts=idx[last], stopped=False)


def cost_R(sym, side, entry, stop, exit_, stopped):
    """result in R after fees + 1 tick slippage on stops, assuming risk = 1R = |entry - stop| (fractional contracts, so no rounding luck)"""
    S = SPECS[sym]; risk = abs(entry - stop)
    if risk <= 0: return 0.0
    gross = (exit_ - entry) * side - (S["tick"] if stopped else 0)
    per_contract_cost_pts = 2 * S["fee"] / S["pv"] + S["tick"]       # fees both sides + 1 tick of slippage, in points
    return (gross - per_contract_cost_pts) / risk


def random_controls(m1, trades, sym, n=200, seed=0):
    """n random strategies with the same number of trades, side mix, stop distance and holding time, at random times in the same sessions.
    trades: DataFrame with entry_ts, side, risk_pts, hold_min. Returns array (n, periods) of total R per period."""
    rng = np.random.default_rng(seed); idx = m1.index
    tod = (idx.hour * 60 + idx.minute).values
    allowed = set(((pd.DatetimeIndex(trades.entry_ts).hour * 60 + pd.DatetimeIndex(trades.entry_ts).minute) // 30).tolist())
    pool = np.flatnonzero(np.isin(tod // 30, list(allowed)))
    out = np.zeros((n, len(PERIODS)))
    for k in range(n):
        picks = rng.choice(pool, size=len(trades), replace=False)
        for (_, t), p in zip(trades.iterrows(), picks):
            side = 1 if rng.random() < (trades.side > 0).mean() else -1
            e = m1.Open.values[p]; st = e - side * t.risk_pts
            r = fill_and_exit(m1, idx[p], side, st, None, idx[p] + pd.Timedelta(minutes=int(t.hold_min)))
            if r is None: continue
            R = cost_R(sym, side, r["entry"], st, r["exit"], r["stopped"])
            for pi, (a, b) in enumerate(PERIODS.values()):
                if pd.Timestamp(a, tz=idx.tz) <= idx[p] < pd.Timestamp(b, tz=idx.tz): out[k, pi] += R
    return out


def score(df, rand=None):
    """df: DataFrame with entry_ts (tz-aware) and R. Prints and returns per-period stats (+ random 95th percentile if given)."""
    rows = []
    for pi, (name, (a, b)) in enumerate(PERIODS.items()):
        tz = df.entry_ts.dt.tz
        x = df[(df.entry_ts >= pd.Timestamp(a, tz=tz)) & (df.entry_ts < pd.Timestamp(b, tz=tz))].R
        if not len(x): continue
        eq = x.cumsum(); w = x[x > 0].sum(); l = -x[x < 0].sum()
        row = dict(period=name, trades=len(x), win_pct=round(100 * (x > 0).mean(), 1), total_R=round(x.sum(), 1), PF=round(w / l, 2) if l else None,
                   max_dd_R=round((eq.cummax() - eq).max(), 1))
        if rand is not None: row["random_95pct_R"] = round(np.percentile(rand[:, pi], 95), 1); row["beats_luck"] = row["total_R"] > row["random_95pct_R"]
        rows.append(row)
    out = pd.DataFrame(rows); print(out.to_string(index=False)); return out
