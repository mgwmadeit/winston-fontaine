# Moses's strategy: SUPPLY & DEMAND zones + EMA 8/20 cross confirmation.
#   Zone = the "base" candle right before an impulse candle (impulse body > k x ATR) on the zone timeframe (15m / 60m).
#   Demand = base before a big UP move, supply = base before a big DOWN move. Zone = base high..low. Fresh zones only (first return).
#   Entry: price comes back into the zone, then a 5-min EMA 8 crosses EMA 20 in the zone's direction (within N bars of touching it).
#   Stop: beyond the far side of the zone (+buffer). Target: the impulse extreme ("to the highs / to the lows") or 2R / hold to close.
#   python sd_ema.py
import numpy as np, pandas as pd, itertools
from run_published import load

SPEC = {"NQ": (2.0, 0.25, 2.24), "GC": (10.0, 0.10, 2.64)}           # micro $/pt, tick, round-trip cost
TR, TE = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-04-01")


def run(sym, ztf=15, k=2.0, window=12, target="impulse", max_age_h=48, risk=200.0):
    pv, tick, cost = SPEC[sym]
    m = load(sym)
    z = m.resample(f"{ztf}min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    rng = (z.High - z.Low); atr = rng.rolling(14).mean().shift()
    body = (z.Close - z.Open)
    m5 = m.resample("5min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    e8, e20 = m5.Close.ewm(span=8, adjust=False).mean(), m5.Close.ewm(span=20, adjust=False).mean()
    up_x = ((e8 > e20) & (e8.shift() <= e20.shift())).values; dn_x = ((e8 < e20) & (e8.shift() >= e20.shift())).values
    H5, L5, C5 = m5.High.values, m5.Low.values, m5.Close.values; T5 = m5.index
    zones = []
    for i in range(15, len(z) - 1):
        if np.isnan(atr.iloc[i]): continue
        if abs(body.iloc[i + 1]) > k * atr.iloc[i] and rng.iloc[i] < atr.iloc[i]:        # small base, then impulse
            d = 1 if body.iloc[i + 1] > 0 else -1
            zones.append((z.index[i + 1] + pd.Timedelta(minutes=ztf), d, z.High.iloc[i], z.Low.iloc[i], z.High.iloc[i + 1] if d > 0 else z.Low.iloc[i + 1]))
    out = []; busy_until = -1
    t5_ns = T5.asi8
    for born, d, zh, zl, ext in zones:
        j0 = int(np.searchsorted(t5_ns, born.value)); jmax = int(np.searchsorted(t5_ns, (born + pd.Timedelta(hours=max_age_h)).value))
        touch = -1
        for j in range(j0, min(jmax, len(T5))):                       # first return into the zone
            if (d > 0 and L5[j] <= zh) or (d < 0 and H5[j] >= zl): touch = j; break
            if (d > 0 and H5[j] > ext) and False: pass
        if touch < 0 or touch <= busy_until: continue
        if (d > 0 and L5[touch] < zl - (zh - zl)) or (d < 0 and H5[touch] > zh + (zh - zl)): continue   # blew straight through
        ent = -1
        for j in range(touch, min(touch + window, len(T5) - 1)):
            if (d > 0 and up_x[j]) or (d < 0 and dn_x[j]): ent = j + 1; break
            if (d > 0 and C5[j] < zl) or (d < 0 and C5[j] > zh): break            # zone failed before the cross
        if ent < 0: continue
        entry = m5.Open.values[ent]; buf = 2 * tick
        stop = zl - buf if d > 0 else zh + buf
        rp = (entry - stop) * d
        if rp <= 4 * tick: continue
        tgt = ext if target == "impulse" else (entry + d * 2 * rp if target == "2R" else None)
        if tgt is not None and (tgt - entry) * d <= rp * 0.5: tgt = entry + d * rp      # impulse too close -> use 1R
        q = int(risk // (rp * pv))
        if q < 1: continue
        ex = None; endj = min(ent + 78 * 2, len(T5) - 1)
        for j in range(ent, endj + 1):
            if (d > 0 and L5[j] <= stop) or (d < 0 and H5[j] >= stop): ex = stop; break
            if tgt is not None and ((d > 0 and H5[j] >= tgt) or (d < 0 and L5[j] <= tgt)): ex = tgt; break
        if ex is None: ex = C5[endj]; j = endj
        busy_until = j
        out.append((T5[ent].tz_localize(None).normalize(), ((ex - entry) * d * pv - cost) * q / risk))
    return pd.DataFrame(out, columns=["date", "R"])


def score(df):
    per = np.where(df.date < TR, "train", np.where(df.date < TE, "test", "recent")); s = []
    for p in ("train", "test", "recent"):
        x = df.R[per == p]; w = x[x > 0].sum(); l = -x[x < 0].sum()
        s.append(f"{p}: {len(x):4d}tr {100*(x>0).mean() if len(x) else 0:4.1f}% {x.sum():+6.1f}R PF {w/l if l else 0:4.2f}")
    return " | ".join(s)


if __name__ == "__main__":
    for sym, ztf, k, tgt in itertools.product(("NQ", "GC"), (15, 60), (1.5, 2.5), ("impulse", "2R", "hold")):
        df = run(sym, ztf, k, target=tgt)
        print(f"{sym} zones {ztf:2d}m impulse>{k}xATR target {tgt:7s} | {score(df)}")
