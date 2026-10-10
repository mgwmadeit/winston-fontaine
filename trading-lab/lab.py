# STRATEGY LAB: rebuilds Lil Fish's "10,000 strategies" test on REAL NQ futures data (Databento 1-min, Oct 2023 -> today).
# Every strategy = signal family x timeframe x session x stop x exit.  MNQ, $200 risk per trade, fees + slippage.
# Periods:  TRAIN Oct 2023-Sep 2025 | TEST Oct 2025-Mar 2026 | RECENT = last 6 months (Apr 2026 -> today)
#   python lab.py          -> writes lab_results.csv + lab_trades.parquet
import os, sys, time, numpy as np, pandas as pd
from numba import njit
from run_published import load

HERE = os.path.dirname(os.path.abspath(__file__))
SYM = sys.argv[1] if len(sys.argv) > 1 else "NQ"
PV, TICK, FEE, RISK = {"NQ": (2.0, 0.25, 0.62, 200.0), "GC": (10.0, 0.10, 0.82, 200.0)}[SYM]   # MNQ / MGC micros
COST = 2 * TICK * PV + 2 * FEE                         # per contract round trip
TRAIN_END, TEST_END = pd.Timestamp("2025-10-01").date(), pd.Timestamp("2026-04-01").date()

SESSIONS = {  # name: (entry window start, end in minutes of day ET, flat time minutes, flat next day if entry after this tod)
    "NYAM": (570, 690, 955, None), "NY": (570, 930, 955, None),
    "LON": (180, 480, 565, None), "ASIA": (1140, 120, 175, 1140),
    "AFTER10_AM": (600, 720, 955, None), "AFTER10_ALL": (600, 930, 955, None)}
STOPS = [("fix15", 15), ("fix40", 40), ("atr10", 0.10), ("atr25", 0.25)] if SYM == "NQ" else [("fix3", 3), ("fix8", 8), ("atr10", 0.10), ("atr25", 0.25)]
EXITS = [("1R", 1.0, 0), ("2R", 2.0, 0), ("hold", 0.0, 0), ("60min", 0.0, 60)]
TFS = [5, 15, 30, 60]


@njit(cache=True)
def sim(ent, side, sd, tmult, maxhold, flat, day, o, h, l, c, max_per_day, pv, risk):
    n = len(ent); out_i = np.full(n, -1); out_pts = np.zeros(n); out_q = np.zeros(n)
    last_exit, cur_day, cnt = -1, -1, 0
    for k in range(n):
        i = ent[k]
        if i <= last_exit or flat[k] < i or sd[k] <= 0: continue
        if day[k] == cur_day and cnt >= max_per_day: continue
        q = np.floor(risk / (sd[k] * pv))          # pv/risk passed in (numba caches globals as constants)
        if q < 1: continue
        s = side[k]; e = o[i]; stop = e - s * sd[k]
        tg = e + s * tmult * sd[k] if tmult > 0 else np.nan
        end = flat[k] if maxhold <= 0 else min(flat[k], i + maxhold - 1)
        ex, exi = c[end], end
        for j in range(i, end + 1):
            if s > 0:
                if l[j] <= stop: ex, exi = stop, j; break
                if tmult > 0 and h[j] >= tg: ex, exi = tg, j; break
            else:
                if h[j] >= stop: ex, exi = stop, j; break
                if tmult > 0 and l[j] <= tg: ex, exi = tg, j; break
        out_i[k] = i; out_pts[k] = (ex - e) * s; out_q[k] = q
        last_exit = exi
        if day[k] != cur_day: cur_day, cnt = day[k], 0
        cnt += 1
    return out_i, out_pts, out_q


def ema(x, n): return x.ewm(span=n, adjust=False).mean()

def rsi(x, n=14):
    d = x.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)

def cross_up(a, b): return (a > b) & (a.shift() <= b.shift())

def supertrend(b, n=10, m=3.0):
    hl2 = (b.High + b.Low) / 2; tr = pd.concat([b.High - b.Low, (b.High - b.Close.shift()).abs(), (b.Low - b.Close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean().values; up0 = (hl2 - m * atr).values; dn0 = (hl2 + m * atr).values; cl = b.Close.values
    trend = np.ones(len(b)); up = up0.copy(); dn = dn0.copy()
    for i in range(1, len(b)):
        up[i] = max(up0[i], up[i - 1]) if cl[i - 1] > up[i - 1] else up0[i]
        dn[i] = min(dn0[i], dn[i - 1]) if cl[i - 1] < dn[i - 1] else dn0[i]
        trend[i] = 1 if cl[i] > dn[i - 1] else (-1 if cl[i] < up[i - 1] else trend[i - 1])
    return pd.Series(trend, index=b.index)


def build():
    m = load(SYM)
    t = m.index; tod = t.hour * 60 + t.minute
    tday = (t + pd.Timedelta(hours=6)).normalize().tz_localize(None)          # trading day (18:00 ET starts the next one)
    m = m.assign(tod=tod, tday=tday)
    rth = m[(m.tod >= 570) & (m.tod < 960)]
    D = rth.groupby(rth.index.date).agg(O=("Open", "first"), H=("High", "max"), L=("Low", "min"), C=("Close", "last"))
    D.index = pd.to_datetime(D.index)
    pc = D.C.shift(); tr = pd.concat([D.H - D.L, (D.H - pc).abs(), (D.L - pc).abs()], axis=1).max(axis=1)
    lv = pd.DataFrame({"pdh": D.H.shift(), "pdl": D.L.shift(), "pdc": pc, "atr": tr.rolling(14).mean().shift(), "rth_open": D.O})
    on = m[(m.tod < 570) | (m.tod >= 1080)].groupby("tday").agg(onh=("High", "max"), onl=("Low", "min"))
    lv = lv.join(on, how="outer")
    for N in (5, 15, 30, 60):
        f = rth[rth.tod < 570 + N].groupby(rth[rth.tod < 570 + N].index.date).agg(h=("High", "max"), l=("Low", "min"))
        f.index = pd.to_datetime(f.index); lv[f"or{N}h"], lv[f"or{N}l"] = f.h, f.l
    return m, lv


def signals(b, tf):
    """Every family: name -> side series (+1 long, -1 short, 0 none) evaluated at bar close."""
    C, H, L, O, V = b.Close, b.High, b.Low, b.Open, b.Volume
    S = {}
    def both(name, longc, shortc, fade=True):
        s = longc.astype(int) - shortc.astype(int)
        S[name] = s
        if fade: S[name + "_FADE"] = -s
    for f_, s_ in ((9, 21), (20, 50)): both(f"ema{f_}x{s_}", cross_up(ema(C, f_), ema(C, s_)), cross_up(ema(C, s_), ema(C, f_)))
    r = rsi(C)
    both("rsi30_70_revert", cross_up(r, pd.Series(30, index=r.index)), cross_up(pd.Series(70, index=r.index), r), fade=False)
    both("rsi20_80_revert", cross_up(r, pd.Series(20, index=r.index)), cross_up(pd.Series(80, index=r.index), r), fade=False)
    both("rsi55_45_momo", cross_up(r, pd.Series(55, index=r.index)), cross_up(pd.Series(45, index=r.index), r), fade=False)
    mid = C.rolling(20).mean(); sdv = C.rolling(20).std()
    both("bollinger_break", cross_up(C, mid + 2 * sdv), cross_up(mid - 2 * sdv, C))
    for n in (20, 55):
        both(f"donchian{n}_break", C > H.shift().rolling(n).max(), C < L.shift().rolling(n).min(), fade=(n == 20))
    st = supertrend(b); both("supertrend_flip", (st == 1) & (st.shift() == -1), (st == -1) & (st.shift() == 1))
    macd = ema(C, 12) - ema(C, 26); sig = ema(macd, 9); both("macd_cross", cross_up(macd, sig), cross_up(sig, macd), fade=False)
    vw, vsd = b.vwap, b.vsd
    both("vwap_cross", cross_up(C, vw), cross_up(vw, C))
    both("vwap_2sigma_break", cross_up(C, vw + 2 * vsd), cross_up(vw - 2 * vsd, C))
    va = V.rolling(20).mean(); rng = H - L; ra = rng.rolling(20).mean()
    for k in (2, 3):
        spike = (V > k * va) & (rng > 1.5 * ra)
        both(f"volume_spike{k}x", spike & (C > O), spike & (C < O), fade=(k == 3))
    mom_h, mom_l = H.shift(), L.shift(); inside = (H.shift() < H.shift(2)) & (L.shift() > L.shift(2))
    both("inside_bar_break", inside & (C > H.shift(2)), inside & (C < L.shift(2)), fade=False)
    both("engulfing", (C > O) & (C.shift() < O.shift()) & (C > O.shift()) & (O < C.shift()),
         (C < O) & (C.shift() > O.shift()) & (C < O.shift()) & (O > C.shift()))
    both("pdh_pdl_break", cross_up(C, b.pdh), cross_up(b.pdl, C), fade=False)
    both("pdh_pdl_sweep_reclaim", (H > b.pdh) & (C < b.pdh), (L < b.pdl) & (C > b.pdl), fade=False)
    S["pdh_pdl_sweep_reclaim"] = -S["pdh_pdl_sweep_reclaim"]          # sweep above PDH -> short
    rthb = (b.tod_close > 570) & (b.tod_close <= 960)
    both("onh_onl_break", rthb & cross_up(C, b.onh), rthb & cross_up(b.onl, C), fade=False)
    both("onh_onl_sweep_reclaim", rthb & (H > b.onh) & (C < b.onh), rthb & (L < b.onl) & (C > b.onl), fade=False)
    S["onh_onl_sweep_reclaim"] = -S["onh_onl_sweep_reclaim"]
    for N in (5, 15, 30, 60):
        if N < tf: continue
        ok = rthb & (b.tod_close >= 570 + N)
        both(f"orb{N}_break", ok & (C > b[f"or{N}h"]), ok & (C < b[f"or{N}l"]), fade=False)
        if N in (15, 30):
            both(f"orb{N}_sweep_fade", ok & (H > b[f"or{N}h"]) & (C < b[f"or{N}h"]), ok & (L < b[f"or{N}l"]) & (C > b[f"or{N}l"]), fade=False)
            S[f"orb{N}_sweep_fade"] = -S[f"orb{N}_sweep_fade"]
    first = b.tod_close == 570 + tf
    gap = (b.rth_open - b.pdc) / b.atr
    both("gap_go", first & (gap > 0.1), first & (gap < -0.1))
    both("first_bar_color", first & (C > O), first & (C < O))
    up3 = (C > O) & (C.shift() > O.shift()) & (C.shift(2) > O.shift(2)); dn3 = (C < O) & (C.shift() < O.shift()) & (C.shift(2) < O.shift(2))
    both("three_bar_momo", up3 & ~up3.shift(fill_value=False), dn3 & ~dn3.shift(fill_value=False))
    big = rng > 2.5 * ra
    both("big_bar", big & (C > O), big & (C < O))
    for seed in range(3):                                           # RANDOM controls: what pure luck looks like
        rs = np.random.default_rng(seed + tf); p = min(0.5, tf / 390 * 3)
        x = rs.random(len(b)); S[f"RANDOM_{seed}"] = pd.Series(np.where(x < p / 2, 1, np.where(x > 1 - p / 2, -1, 0)), index=b.index)
    return S


def main():
    t0 = time.time()
    m, lv = build()
    o, h, l, c = (m[k].values.astype(np.float64) for k in ("Open", "High", "Low", "Close"))
    mt = m.index; mt_ns = mt.asi8
    rows, trades, sid = [], [], 0
    for tf in TFS:
        off = "30min" if tf in (30, 60) else "0min"
        b = m.resample(f"{tf}min", offset=off).agg(Open=("Open", "first"), High=("High", "max"), Low=("Low", "min"),
                                                    Close=("Close", "last"), Volume=("Volume", "sum")).dropna()
        ct = b.index + pd.Timedelta(minutes=tf)
        b["tod_close"] = ct.hour * 60 + ct.minute
        b.loc[b.tod_close == 0, "tod_close"] = 1440
        b["tday"] = (b.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
        tp = (b.High + b.Low + b.Close) / 3
        g = b.assign(pv=tp * b.Volume, pv2=tp * tp * b.Volume).groupby("tday")
        cv = g.Volume.cumsum(); b["vwap"] = g.pv.cumsum() / cv; b["vsd"] = np.sqrt((g.pv2.cumsum() / cv - b.vwap ** 2).clip(lower=0))
        b = b.join(lv, on="tday")
        sigs = signals(b, tf)
        ent_all = np.searchsorted(mt_ns, ct.asi8)
        valid = ent_all < len(mt)
        ent_all = np.minimum(ent_all, len(mt) - 1)
        valid &= (mt_ns[ent_all] - ct.asi8) < 5 * 60e9
        todc = b.tod_close.values % 1440
        for sname, (a, z, flat_tod, nextday) in SESSIONS.items():
            inwin = ((todc >= a) & (todc <= z)) if a < z else ((todc >= a) | (todc <= z))
            base = valid & inwin
            cdate = ct.tz_localize(None).normalize()
            fdate = cdate + pd.to_timedelta(np.where((nextday is not None) & (todc >= (nextday or 0)), 1, 0), unit="D")
            flat_dt = (fdate + pd.Timedelta(minutes=flat_tod)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
            flat_all = np.searchsorted(mt_ns, flat_dt.asi8, side="right") - 1
            day_all = b.tday.values.astype("datetime64[D]").astype(np.int64)
            atr_all = b.atr.values
            for fam, s in sigs.items():
                sv = s.fillna(0).values.astype(np.int64)
                mask = base & (sv != 0) & ~pd.isna(flat_dt)
                if mask.sum() < 20: continue
                idx = np.where(mask)[0]
                ent = ent_all[idx]; side = sv[idx].astype(np.float64); flat = flat_all[idx]; day = day_all[idx]; atr = atr_all[idx]
                for stn, stv in STOPS:
                    sd = np.full(len(idx), float(stv)) if stn.startswith("fix") else np.nan_to_num(atr * stv)
                    for exn, tm, mh in EXITS:
                        ei, pts, q = sim(ent, side, sd, tm, mh, flat, day, o, h, l, c, 2, PV, RISK)
                        k = ei >= 0
                        if k.sum() < 10: continue
                        pnl = (pts[k] * PV - COST) * q[k]
                        dts = mt[ei[k]].date
                        rows.append(dict(id=sid, family=fam, tf=tf, session=sname, stop=stn, exit=exn))
                        trades.append(pd.DataFrame({"id": sid, "date": dts, "ts": mt[ei[k]], "side": side[k].astype(np.int8), "R": (pnl / RISK).astype(np.float32)}))
                        sid += 1
        print(f"tf {tf}: {sid} strategies so far ({time.time()-t0:.0f}s)", flush=True)
    meta = pd.DataFrame(rows); tr = pd.concat(trades, ignore_index=True)
    sfx = "" if SYM == "NQ" else "_" + SYM
    tr.to_parquet(os.path.join(HERE, f"lab_trades{sfx}.parquet"))
    meta.to_csv(os.path.join(HERE, f"lab_meta{sfx}.csv"), index=False)
    print("done", len(meta), "strategies,", len(tr), "trades", f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
