# ICT (Inner Circle Trader) models, coded from his own videos (trading\ict-yt\):
#  SILVER BULLET (tRq1hyGGtl4): 60-min windows 03-04, 10-11, 14-15 ET. First fair value gap (FVG) that forms in the window -> enter on the
#     retrace into it, stop beyond the swing that made it, target the nearest old high/low (liquidity). Must offer >= 10 handles (NQ).
#  2022 MODEL (L-ReMHiavPM, ep 2-4): from 8:30 ET price raids an old high/low (pre-session liquidity), then a market structure shift
#     (close through the last swing) with displacement leaving an FVG -> enter on the retrace into the FVG, stop beyond the raid, target the
#     opposite liquidity (other side of the pre-session range) or 2R.
#  OTE: same raid + shift, but enter at the 62-79% (0.705) retracement of the displacement leg.
# 1-minute accurate fills (stop checked first), fees + slippage, $200 risk per trade.  python ict.py
import numpy as np, pandas as pd, itertools
from run_published import load

SPEC = {"NQ": dict(pv=2.0, tick=0.25, cost=2.24, frame=10.0), "GC": dict(pv=10.0, tick=0.10, cost=2.64, frame=3.0)}
TR, TE = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-04-01")
RISK = 200.0


def day_groups(m, tf):
    b = m if tf == 1 else m.resample(f"{tf}min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    t = b.index; tod = (t.hour * 60 + t.minute).values
    return b, tod


def walk(H, L, C, j0, side, entry, stop, tgt, jend):
    """from bar j0 (fill bar) to jend; stop first. returns exit price"""
    for j in range(j0, jend + 1):
        if side > 0:
            if L[j] <= stop: return stop
            if j > j0 and H[j] >= tgt: return tgt
        else:
            if H[j] >= stop: return stop
            if j > j0 and L[j] <= tgt: return tgt
    return C[jend]


def trade_result(sym, side, entry, stop, exitp):
    S = SPEC[sym]; rp = abs(entry - stop)
    q = int(RISK // (rp * S["pv"]))
    if q < 1: return None
    return (((exitp - entry) * side - (S["tick"] if exitp == stop else 0)) * S["pv"] - S["cost"]) * q / RISK


def silver_bullet(sym, b, tod, windows=((180, 240), (600, 660), (840, 900)), entry_at="edge", target="liquidity", need_frame=True, lookback=60):
    S = SPEC[sym]; H, L, O, C = (b[k].values for k in ("High", "Low", "Open", "Close")); t = b.index
    out = []
    dates = t.normalize()
    for ws, we in windows:
        idx = np.flatnonzero((tod >= ws) & (tod < we))
        if not len(idx): continue
        # group by date
        brk = np.flatnonzero(np.diff(dates[idx].asi8) != 0) + 1
        for grp in np.split(idx, brk):
            if len(grp) < 5: continue
            done = False
            for i in grp:
                if i < 6 or done: continue
                bull = L[i] > H[i - 2]; bear = H[i] < L[i - 2]
                if not (bull or bear): continue
                side = 1 if bull else -1
                gap_hi, gap_lo = (L[i], H[i - 2]) if bull else (L[i - 2], H[i])
                swing = L[i - 4:i].min() if bull else H[i - 4:i].max()          # the swing that launched the displacement
                entry = gap_hi if (entry_at == "edge" and bull) else (gap_lo if entry_at == "edge" else (gap_hi + gap_lo) / 2)
                stop = swing - S["tick"] if bull else swing + S["tick"]
                if (entry - stop) * side <= 2 * S["tick"]: continue
                prior = slice(max(0, i - lookback), i - 2)
                liq = H[prior].max() if bull else L[prior].min()                  # nearest old high (long) / old low (short)
                if target == "liquidity":
                    tgt = liq
                    if (tgt - entry) * side <= 0: continue
                else:
                    tgt = entry + side * 2 * abs(entry - stop)
                if need_frame and abs(liq - entry) < S["frame"]: continue        # must offer >= 10 handles (NQ) / $3 (gold)
                done = True
                # fill: retrace into the gap while still inside the window
                fill = None
                for j in range(i + 1, min(grp[-1] + 1, len(H))):
                    if (side > 0 and H[j] >= tgt) or (side < 0 and L[j] <= tgt): break
                    if (side > 0 and L[j] <= entry) or (side < 0 and H[j] >= entry): fill = j; break
                if fill is None: break
                jend = min(fill + 240 // max(1, int((t[1] - t[0]).total_seconds() // 60)), len(H) - 1)
                r = trade_result(sym, side, entry, stop, walk(H, L, C, fill, side, entry, stop, tgt, jend))
                if r is not None: out.append((t[fill].tz_localize(None).normalize(), ws, r))
    return pd.DataFrame(out, columns=["date", "window", "R"])


def model_2022(sym, b, tod, start=510, end=660, ref=(360, 510), ote=False, target="opposite"):
    """raid of the pre-session (6:00-8:30) high/low after 8:30, then MSS + FVG (or OTE) entry."""
    S = SPEC[sym]; H, L, O, C = (b[k].values for k in ("High", "Low", "Open", "Close")); t = b.index
    dates = t.normalize(); out = []
    for d in np.unique(dates):
        di = np.flatnonzero(dates == d)
        r_idx = di[(tod[di] >= ref[0]) & (tod[di] < ref[1])]; w_idx = di[(tod[di] >= start) & (tod[di] < end)]
        if len(r_idx) < 10 or len(w_idx) < 10: continue
        RH, RL = H[r_idx].max(), L[r_idx].min()
        state = None
        for k, i in enumerate(w_idx):
            if state is None:
                if H[i] > RH: state = dict(side=-1, ext=H[i], ei=i)        # raided buy-side -> look for shorts
                elif L[i] < RL: state = dict(side=1, ext=L[i], ei=i)
                continue
            side = state["side"]
            if side < 0 and H[i] > state["ext"]: state["ext"], state["ei"] = H[i], i
            if side > 0 and L[i] < state["ext"]: state["ext"], state["ei"] = L[i], i
            ei = state["ei"]
            if i - ei < 2: continue
            seg = slice(max(di[0], ei - 10), ei)                          # last swing before the raid extreme
            if seg.stop - seg.start < 2: continue
            swing = L[seg].min() if side < 0 else H[seg].max()
            mss = (C[i] < swing) if side < 0 else (C[i] > swing)
            if not mss: continue
            # displacement leg = raid extreme -> this bar
            leg_lo = L[ei:i + 1].min() if side < 0 else H[ei:i + 1].max()
            if ote:
                entry = leg_lo + 0.705 * (state["ext"] - leg_lo) if side < 0 else leg_lo - 0.705 * (leg_lo - state["ext"])
            else:
                fvg = None
                for q in range(ei + 2, i + 1):
                    if side < 0 and H[q] < L[q - 2]: fvg = (H[q], L[q - 2])
                    if side > 0 and L[q] > H[q - 2]: fvg = (H[q - 2], L[q])
                if fvg is None: break
                entry = fvg[0] if side < 0 else fvg[1]
            stop = state["ext"] + side * -1 * S["tick"] * -1 if False else (state["ext"] + S["tick"] if side < 0 else state["ext"] - S["tick"])
            tgt = (RL if side < 0 else RH) if target == "opposite" else entry + side * 2 * abs(entry - stop)
            if (tgt - entry) * side <= 0 or abs(entry - stop) <= 2 * S["tick"]: break
            fill = None
            for j in range(i + 1, min(w_idx[-1] + 1, len(H))):
                if (side > 0 and H[j] >= tgt) or (side < 0 and L[j] <= tgt): break
                if (side > 0 and L[j] <= entry) or (side < 0 and H[j] >= entry): fill = j; break
            if fill is None: break
            jend = min(di[-1], len(H) - 1)
            r = trade_result(sym, side, entry, stop, walk(H, L, C, fill, side, entry, stop, tgt, jend))
            if r is not None: out.append((pd.Timestamp(d).tz_localize(None), start, r))
            break
    return pd.DataFrame(out, columns=["date", "window", "R"])


def score(df):
    if df.empty: return "no trades"
    per = np.where(df.date < TR, "train", np.where(df.date < TE, "test", "recent")); s = []
    for p in ("train", "test", "recent"):
        x = df.R[per == p]; w = x[x > 0].sum(); l = -x[x < 0].sum()
        s.append(f"{p}: {len(x):4d}tr {100*(x>0).mean() if len(x) else 0:4.1f}% {x.sum():+7.1f}R PF {w/l if l else 0:4.2f}")
    return " | ".join(s)


if __name__ == "__main__":
    rows = []
    for sym in ("NQ", "GC"):
        m = load(sym)
        for tf in (1, 5):
            b, tod = day_groups(m, tf)
            for ent, tgt, fr in itertools.product(("edge", "mid"), ("liquidity", "2R"), (True, False)):
                df = silver_bullet(sym, b, tod, entry_at=ent, target=tgt, need_frame=fr)
                print(f"{sym} {tf}m SILVER BULLET entry={ent:4s} target={tgt:9s} 10-handle rule={fr!s:5s} | {score(df)}")
                for w, g in df.groupby("window"):
                    rows.append((sym, tf, f"SB {w//60:02d}:00 {ent}/{tgt}/{fr}", g))
            for ote, tgt in itertools.product((False, True), ("opposite", "2R")):
                df = model_2022(sym, b, tod, ote=ote, target=tgt)
                print(f"{sym} {tf}m 2022 MODEL {'OTE 0.705' if ote else 'FVG entry':9s} target={tgt:8s}            | {score(df)}")
            df = model_2022(sym, b, tod, start=120, end=300, ref=(1200 - 1440, 120), target="2R") if False else None
    print("\nSilver Bullet by window (NQ 1m, edge entry, liquidity target, 10-handle rule):")
    m = load("NQ"); b, tod = day_groups(m, 1); df = silver_bullet("NQ", b, tod)
    for w, g in df.groupby("window"): print(f"  {w//60:02d}:00-{w//60+1:02d}:00  {score(g)}")
