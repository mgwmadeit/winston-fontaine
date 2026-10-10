# What do our strategies make trading exactly ONE contract per trade (1 mini or 1 micro)?
#   NQ lane: ORB 5-min + Asia 15m engulfing + 60m VWAP 2-sigma fade      Gold lane: Asia 60m Donchian-55 breakout + 5m volume-spike fade
#   python one_contract.py
import numpy as np, pandas as pd
import lab
from kron import MNQ
from published import orb2
from run_published import load
import evalfarm as ef

SPECS = {"NQ mini (NQ)": ("NQ", 20.0, 0.25, 2.25), "NQ micro (MNQ)": ("NQ", 2.0, 0.25, 0.62),
         "Gold mini (GC)": ("GC", 100.0, 0.10, 2.25), "Gold micro (MGC)": ("GC", 10.0, 0.10, 0.82)}
LAB = {"NQ": [("ASIA engulf", "engulfing", 15, "ASIA", ("atr", .10), (2.0, 0)), ("VWAP fade", "vwap_2sigma_break_FADE", 60, "NY", ("atr", .10), (0.0, 60))],
       "GC": [("Asia breakout", "donchian55_break", 60, "ASIA", ("atr", .10), (0.0, 0)), ("Spike fade", "volume_spike3x_FADE", 5, "AFTER10_AM", ("fix", 8.0), (0.0, 0))]}


def lab_points(sym, fam, tf, ses, stop, ex):
    """re-run one lab strategy and return per-trade points (1 contract)"""
    lab.SYM = sym
    m, lv = lab.build_sym(sym)
    o, h, l, c = (m[k].values.astype(np.float64) for k in ("Open", "High", "Low", "Close"))
    mt = m.index; mt_ns = mt.asi8
    off = "30min" if tf in (30, 60) else "0min"
    b = m.resample(f"{tf}min", offset=off).agg(Open=("Open", "first"), High=("High", "max"), Low=("Low", "min"), Close=("Close", "last"), Volume=("Volume", "sum")).dropna()
    ct = b.index + pd.Timedelta(minutes=tf)
    b["tod_close"] = ct.hour * 60 + ct.minute; b.loc[b.tod_close == 0, "tod_close"] = 1440
    b["tday"] = (b.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    tp = (b.High + b.Low + b.Close) / 3
    g = b.assign(pv=tp * b.Volume, pv2=tp * tp * b.Volume).groupby("tday")
    cv = g.Volume.cumsum(); b["vwap"] = g.pv.cumsum() / cv; b["vsd"] = np.sqrt((g.pv2.cumsum() / cv - b.vwap ** 2).clip(lower=0))
    b = b.join(lv, on="tday")
    s = lab.signals(b, tf)[fam]
    ent_all = np.minimum(np.searchsorted(mt_ns, ct.asi8), len(mt) - 1)
    valid = (mt_ns[ent_all] - ct.asi8) < 5 * 60e9
    a, z, flat_tod, nextday = lab.SESSIONS[ses]
    todc = b.tod_close.values % 1440
    inwin = ((todc >= a) & (todc <= z)) if a < z else ((todc >= a) | (todc <= z))
    cdate = ct.tz_localize(None).normalize()
    fdate = cdate + pd.to_timedelta(np.where((nextday is not None) & (todc >= (nextday or 0)), 1, 0), unit="D")
    flat_dt = (fdate + pd.Timedelta(minutes=flat_tod)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    flat_all = np.searchsorted(mt_ns, flat_dt.asi8, side="right") - 1
    sv = s.fillna(0).values.astype(np.int64)
    idx = np.where(valid & inwin & (sv != 0) & ~pd.isna(flat_dt))[0]
    sd = np.full(len(idx), stop[1]) if stop[0] == "fix" else np.nan_to_num(b.atr.values[idx] * stop[1])
    ei, pts, q = lab.sim(ent_all[idx], sv[idx].astype(np.float64), sd, ex[0], ex[1], flat_all[idx],
                         b.tday.values[idx].astype("datetime64[D]").astype(np.int64), o, h, l, c, 2, 1.0, 1e12)   # qty never limits: we only use points
    k = ei >= 0
    d = (mt[ei[k]] + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    return pd.DataFrame({"date": d, "pts": pts[k], "risk_pts": sd[k]})


def main():
    # make lab.build work for any symbol
    def build_sym(sym):
        lab.load_orig = getattr(lab, "load_orig", lab.load)
        lab.load = lambda name, _s=sym: lab.load_orig(_s)
        try: return lab.build()
        finally: lab.load = lab.load_orig
    lab.build_sym = build_sym
    pts = {"NQ": {}, "GC": {}}
    nq = load("NQ"); o = orb2(nq, MNQ, mode="breakout", atr_stop=0.10)
    o["date"] = pd.to_datetime(o["date"]); o["pts"] = (o.exit - o.entry) * o.side; o["risk_pts"] = (o.entry - o.stop).abs()
    pts["NQ"]["ORB"] = o[["date", "pts", "risk_pts"]]
    for sym in ("NQ", "GC"):
        for name, fam, tf, ses, stop, ex in LAB[sym]:
            pts[sym][name] = lab_points(sym, fam, tf, ses, stop, ex)
    days = pd.Index(sorted(set(pd.to_datetime(load("NQ").index.date))))
    recent = pd.Timestamp("2026-04-01")
    for spec, (sym, pv, tick, fee) in SPECS.items():
        print(f"\n================ 1 x {spec}  (${pv:g} per point, fees + 1 tick slippage per trade) ================")
        allday = pd.Series(0.0, index=days)
        for name, df in pts[sym].items():
            pnl = df.pts * pv - tick * pv - 2 * fee
            daily = pnl.groupby(df.date).sum().reindex(days, fill_value=0); allday += daily
            eq = daily.cumsum(); dd = (eq.cummax() - eq).max()
            yr = {y: f"${v:+,.0f}" for y, v in daily.groupby(daily.index.year).sum().items()}
            print(f"  {name:14s} {len(df):4d} trades  win {100*(pnl>0).mean():4.1f}%  avg risk ${df.risk_pts.median()*pv:,.0f}/trade  "
                  f"total ${pnl.sum():+,.0f}  last 6 mo ${daily[daily.index >= recent].sum():+,.0f}  max DD ${dd:,.0f}  {yr}")
        eq = allday.cumsum(); dd = (eq.cummax() - eq).max(); months = allday.resample("ME").sum()
        print(f"  {'LANE TOTAL':14s} total ${allday.sum():+,.0f} | per month avg ${months.mean():+,.0f} (best ${months.max():+,.0f}, worst ${months.min():+,.0f}, "
              f"{(months > 0).mean()*100:.0f}% green months) | worst day ${allday.min():+,.0f} | max drawdown ${dd:,.0f} | last 6 mo ${allday[allday.index >= recent].sum():+,.0f}")
        # Topstep 50K eval with this fixed size
        F = ef.FIRMS["Topstep 50K"]; res = [ef.run_account(allday.values, F, s) for s in range(20, len(days) - 40)]
        cost = np.array([x[0] for x in res]); paid = np.array([x[1] for x in res]); ps = np.array([x[2] for x in res])
        print(f"  Topstep 50K eval at this size: pass {ps.mean()*100:.0f}% | get paid {(paid>0).mean()*100:.0f}% | net per eval ${(paid-cost).mean():+,.0f}")


if __name__ == "__main__":
    main()
