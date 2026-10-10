# Tom Gratwicke (@itstomtrades) "ONE HOURLY CANDLE" reversal, coded from his videos (nKy15N79BXM, zFe98gsfbUk, IG reels):
#  1. mark the previous hourly candle's high/low
#  2. the new hourly candle breaks it and overextends ~20 min in one direction without a 50% pullback
#  3. around the halfway point of the hour (min 22-52) wait for a 1-min shift (break of the last micro low/high)
#  4. entry = limit at 50% of the breaking move, stop = beyond the swing extreme, target = 50% of the hourly extension
#  Sessions: 2nd hour of Asia -> 3rd/4th hour of London (~20:00-07:00 ET). He trades gold (and USDJPY).
#   python tom.py            -> gold (MGC) results + NQ (MNQ) check, by period / hour / variant
import os, sys, numpy as np, pandas as pd
from run_published import load

INST = {"GC": dict(pv=10.0, tick=0.10, fee=0.82, name="MGC micro gold ($10/pt)"),
        "NQ": dict(pv=2.0, tick=0.25, fee=0.62, name="MNQ micro Nasdaq ($2/pt)")}
RISK = 200.0
TRAIN_END, TEST_END = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-04-01")
SESSION = list(range(20, 24)) + list(range(0, 7))          # his window, ET hours


def run(sym, win=(22, 52), min_ext=18, max_pull=0.5, hours=None, struct_n=2, max_hold=90, fill_until=59, min_rr=0.0, rr_cap=None, no_cost=False, range_ctx=False, stop_buf=0.0):
    I = INST[sym]; tick = I["tick"]
    m = load(sym)
    o, h, l, c = (m[k].values for k in ("Open", "High", "Low", "Close"))
    t = m.index
    hour_key = t.floor("60min")
    starts = np.flatnonzero(np.r_[True, hour_key[1:] != hour_key[:-1]])
    ends = np.r_[starts[1:], len(m)]
    out = []
    for k in range(1, len(starts)):
        s, e = starts[k], ends[k]; ps, pe = starts[k - 1], ends[k - 1]
        if e - s < 50 or pe - ps < 50: continue
        if hour_key[s] - hour_key[ps] != pd.Timedelta(hours=1): continue
        hr = hour_key[s].hour
        if hours is not None and hr not in hours: continue
        PH, PL = h[ps:pe].max(), l[ps:pe].min()
        if range_ctx:                               # his context: reversals only in a RANGE, sells in the upper half, buys in the lower half
            lb = max(0, s - 15 * 60); RH, RL = h[lb:s].max(), l[lb:s].min(); mid = (RH + RL) / 2
            trending = abs(c[s - 1] - c[lb]) > 0.6 * (RH - RL)
            if trending: continue
        mins = ((t[s:e] - hour_key[s]).total_seconds() // 60).astype(int)
        done = False
        for side in ((-1, 1) if not range_ctx else tuple(x for x in (-1, 1) if (x < 0 and o[s] > mid) or (x > 0 and o[s] < mid))):  # -1 = fade an UP extension (sell), +1 = fade a DOWN extension (buy)
            if done: break
            hh = h[s:e] if side < 0 else -l[s:e]   # mirror so the logic is always "extension up"
            ll = l[s:e] if side < 0 else -h[s:e]
            cc = c[s:e] if side < 0 else -c[s:e]
            lvl = PH if side < 0 else -PL
            run_hi, i_hi, leg_lo, i_lo, worst = -np.inf, -1, np.inf, -1, 0.0
            for j in range(len(hh)):
                mm = mins[j]
                if mm > win[1]: break
                if hh[j] > run_hi:                 # new extreme of the extension
                    if ll[:j + 1].size:
                        lo_idx = int(np.argmin(ll[:j + 1])); leg_lo, i_lo = ll[lo_idx], lo_idx
                    run_hi, i_hi = hh[j], j
                    seg_h = np.maximum.accumulate(hh[i_lo:j + 1]); full = run_hi - leg_lo   # deepest pullback during the leg vs the WHOLE leg
                    worst = float(((seg_h - ll[i_lo:j + 1])[1:]).max() / full) if j > i_lo and full > 0 else 0.0
                    continue
                if mm < win[0] or i_hi < struct_n or run_hi <= lvl: continue
                if mins[i_hi] - mins[i_lo] < min_ext or worst >= max_pull: continue
                struct_low = ll[i_hi - struct_n:i_hi].min()
                if cc[j] < struct_low:             # 1-min shift confirmed
                    brk_lo = ll[i_hi:j + 1].min()
                    entry = brk_lo + 0.5 * (run_hi - brk_lo)
                    stop = run_hi + tick + stop_buf * (run_hi - leg_lo)
                    tgt = run_hi - 0.5 * (run_hi - leg_lo)
                    if rr_cap: tgt = max(tgt, entry - rr_cap * (stop - entry))
                    if tgt >= entry or (entry - tgt) / (stop - entry) < min_rr: break
                    # wait for the pullback fill (limit) before the target is touched
                    filled = None
                    for f in range(j + 1, len(hh)):
                        if mins[f] > fill_until: break
                        if ll[f] <= tgt: break
                        if hh[f] >= entry: filled = f; break
                    if filled is None: break
                    gi = s + filled; risk_pts = stop - entry
                    qty = int(RISK // (risk_pts * I["pv"]))
                    if qty < 1: break
                    ex = None; exi = None
                    for q in range(gi, min(gi + max_hold, len(m))):
                        H = h[q] if side < 0 else -l[q]; Lq = l[q] if side < 0 else -h[q]
                        if q == gi:                    # fill bar: only the stop counts (conservative)
                            if H >= stop: ex, exi = stop, q; break
                            continue
                        if H >= stop: ex, exi = stop, q; break
                        if Lq <= tgt: ex, exi = tgt, q; break
                    if ex is None: exi = min(gi + max_hold, len(m)) - 1; ex = c[exi] if side < 0 else -c[exi]
                    pts = entry - ex                     # mirrored short logic: profit when price falls
                    slip = tick if ex == stop else 0
                    pnl = (pts * I["pv"] * qty) if no_cost else ((pts - slip) * I["pv"] - 2 * I["fee"]) * qty
                    out.append(dict(risk_pts=round(risk_pts, 2), time=t[gi], hour=hr, side="SELL" if side < 0 else "BUY", entry=abs(entry), stop=abs(stop), target=abs(tgt),
                                    rr=round((entry - tgt) / risk_pts, 2), qty=qty, R=round(pnl / RISK, 3),
                                    result="win" if ex == tgt else ("loss" if ex == stop else "time")))
                    done = True; break
                if hh[j] > run_hi: pass
    return pd.DataFrame(out)


def summary(tr, label):
    if tr.empty: print(f"{label}: no trades"); return
    tr = tr.copy(); tr["date"] = pd.to_datetime(tr.time.dt.tz_convert("America/New_York").dt.date)
    per = np.where(tr.date < TRAIN_END, "train", np.where(tr.date < TEST_END, "test", "recent"))
    s = [f"{label:42s}"]
    for p in ("train", "test", "recent"):
        x = tr[per == p]; w = x.R[x.R > 0].sum(); ls = -x.R[x.R < 0].sum()
        s.append(f"{p}: {len(x):4d}tr {100*(x.R>0).mean() if len(x) else 0:4.1f}% {x.R.sum():+6.1f}R PF {w/ls if ls else 0:4.2f}")
    print(" | ".join(s), f"| avg planned RR {tr.rr.mean():.2f}")


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    for sym in ("GC", "NQ"):
        print(f"\n===== {INST[sym]['name']}  (risk $200/trade, fees + stop slippage) =====")
        base = run(sym, hours=SESSION)
        summary(base, "HIS RULES, his hours (8PM-7AM ET)")
        base.to_csv(f"tom_trades_{sym}.csv", index=False)
        allh = run(sym, hours=None)
        summary(allh, "his rules, ALL 24 hours")
        if not allh.empty:
            g = allh.groupby("hour").agg(trades=("R", "size"), win=("R", lambda x: round(100 * (x > 0).mean(), 1)), totR=("R", "sum"), avgR=("R", "mean")).round(2)
            print("by hour (ET):\n" + g.T.to_string())
        for name, kw in [("window 30-45 min only", dict(win=(30, 45))), ("window 15-55", dict(win=(15, 55))),
                         ("extension >= 25 min", dict(min_ext=25)), ("extension >= 12 min", dict(min_ext=12)),
                         ("planned RR >= 1.5 only", dict(min_rr=1.5)), ("3-bar structure", dict(struct_n=3)),
                         ("hold max 45 min", dict(max_hold=45))]:
            summary(run(sym, hours=SESSION, **kw), name)
