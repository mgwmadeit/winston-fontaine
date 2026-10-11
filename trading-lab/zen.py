# ZEN TRADES "Zen Model" (PDFs in trading\pdfs\): sweep of a 1H/4H high/low -> iFVG (inverse fair value gap) confirmation on 1-5 min ->
# entry on the retest of the flipped gap -> target = liquidity (session / prior-hour highs-lows). Claimed 75-80% win rate.
# Mechanical version:
#   1. SWEEP: price trades beyond the previous completed 1H (or 4H) candle's high/low.  Low swept -> longs; high swept -> shorts.
#   2. iFVG: after the sweep, find a gap that formed IN the sweep direction (bearish FVG on the way down for a long). When a bar's BODY closes
#      through that gap the other way -> inverse FVG confirmed (optional momentum: the closing bar's range >= 1.2x the 20-bar avg).
#   3. ENTRY: limit at the flipped gap edge on the retest; must be in DISCOUNT for longs (below the midpoint of sweep-extreme .. opposite end of
#      the reference candle), PREMIUM for shorts. Stop beyond the sweep extreme.
#   4. TARGET: the opposite side of the reference 1H/4H candle (liquidity) or the session high/low; also tested: 1R / 2R.
# 1-min accurate fills, fees, $200 risk.   python zen.py
import numpy as np, pandas as pd, itertools
from run_published import load
from ict import SPEC, walk, trade_result, score

def zen(sym, m, tf=1, ref_h=60, window=(570, 690), target="ref", momentum=True, discount=True, max_wait=60):
    b = m if tf == 1 else m.resample(f"{tf}min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    H, L, O, C = (b[k].values for k in ("High", "Low", "Open", "Close")); t = b.index
    rng = H - L; avg = pd.Series(rng).rolling(20).mean().values
    ref = m.resample(f"{ref_h}min").agg({"High": "max", "Low": "min"}).dropna()
    refH = ref.High.reindex(t, method="ffill").shift(ref_h // tf).values   # previous COMPLETED reference candle
    refL = ref.Low.reindex(t, method="ffill").shift(ref_h // tf).values
    tod = (t.hour * 60 + t.minute).values; day = t.normalize()
    out = []; i = 25; n = len(H); taken_day = None
    while i < n - 2:
        if not (window[0] <= tod[i] < window[1]) or day[i] == taken_day or np.isnan(refH[i]): i += 1; continue
        side = 1 if L[i] < refL[i] else (-1 if H[i] > refH[i] else 0)
        if side == 0: i += 1; continue
        RH, RL = refH[i], refL[i]; ext = L[i] if side > 0 else H[i]; gap = None; entry = None; done = False
        for j in range(i + 1, min(n - 1, i + max_wait)):
            if not (window[0] <= tod[j] < window[1] + 60): break
            if side > 0 and L[j] < ext: ext = L[j]
            if side < 0 and H[j] > ext: ext = H[j]
            if j >= i + 2:
                if side > 0 and H[j] < L[j - 2]: gap = (H[j], L[j - 2])          # bearish FVG formed on the way down
                if side < 0 and L[j] > H[j - 2]: gap = (H[j - 2], L[j])          # bullish FVG formed on the way up
            if gap is None: continue
            body_through = (min(O[j], C[j]) > gap[1]) if side > 0 else (max(O[j], C[j]) < gap[0])
            if not body_through: continue
            if momentum and not rng[j] >= 1.2 * avg[j]: gap = None; continue
            entry = gap[1] if side > 0 else gap[0]
            stop = ext - SPEC[sym]["tick"] if side > 0 else ext + SPEC[sym]["tick"]
            mid = (ext + (RH if side > 0 else RL)) / 2
            if discount and ((side > 0 and entry > mid) or (side < 0 and entry < mid)): break
            tgt = (RH if side > 0 else RL) if target == "ref" else entry + side * float(target[0]) * abs(entry - stop)
            if (tgt - entry) * side <= 0 or abs(entry - stop) < 2 * SPEC[sym]["tick"]: break
            fill = None
            for k in range(j + 1, min(n - 1, j + 30)):
                if (side > 0 and H[k] >= tgt) or (side < 0 and L[k] <= tgt): break
                if (side > 0 and L[k] <= entry) or (side < 0 and H[k] >= entry): fill = k; break
            if fill is None: break
            jend = min(n - 1, fill + 240 // tf)
            r = trade_result(sym, side, entry, stop, walk(H, L, C, fill, side, entry, stop, tgt, jend))
            if r is not None: out.append((t[fill].tz_localize(None).normalize(), r)); taken_day = day[i]
            done = True; break
        i = (j + 1) if done else i + 1
    return pd.DataFrame(out, columns=["date", "R"])


if __name__ == "__main__":
    for sym in ("NQ", "GC"):
        m = load(sym)
        for tf, ref_h, (wn, win), tgt, mom in itertools.product((1, 5), (60, 240), (("NY AM 9:30-11:30", (570, 690)), ("London 2-5", (120, 300))), ("ref", "1R", "2R"), (True, False)):
            df = zen(sym, m, tf, ref_h, win, tgt, mom)
            print(f"{sym} {tf}m sweep of prev {ref_h//60}H | {wn:16s} | target {tgt:3s} | momentum {str(mom):5s} | {score(df)}")
