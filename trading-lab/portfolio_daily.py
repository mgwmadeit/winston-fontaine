# ALL robust strategies together (1-minute accurate), $ per day at 1 micro each, scaled up -> what makes $500-1,000/day and what it costs in drawdown.
# Then LucidDaily 50K: eval (+$3k, $2k trailing, 50% consistency) and FUNDED (daily payouts above $52,100, $2k intraday trailing locked at $50,100).
#   python portfolio_daily.py
import numpy as np, pandas as pd
import fastpass as fp, one_contract as oc, lab

MICRO = {"NQ": 2.0, "GC": 10.0}; COST = {"NQ": 2.24, "GC": 2.64}       # $/pt and round-trip cost per micro (fees + slippage)
NQ_LAB = [("NQ Asia engulf", "engulfing", 15, "ASIA", ("atr", .10), (2.0, 0)), ("NQ VWAP fade", "vwap_2sigma_break_FADE", 60, "NY", ("atr", .10), (0.0, 60)),
          ("NQ Asia supertrend", "supertrend_flip", 15, "ASIA", ("atr", .25), (1.0, 0))]
GC_LAB = [("GC Asia breakout", "donchian55_break", 60, "ASIA", ("atr", .10), (0.0, 0)), ("GC spike fade", "volume_spike3x_FADE", 5, "AFTER10_AM", ("fix", 8.0), (0.0, 0)),
          ("GC NYAM supertrend", "supertrend_flip", 15, "NYAM", ("atr", .10), (1.0, 0))]


def build():
    def build_sym(sym):
        lab.load_orig = getattr(lab, "load_orig", lab.load); lab.load = lambda name, _s=sym: lab.load_orig(_s)
        try: return lab.build()
        finally: lab.load = lab.load_orig
    lab.build_sym = build_sym
    days = fp.prep(); idx = pd.Index([d["date"] for d in days])
    S = {}
    ex = fp.EXITS["hold to close"]; rows = []
    for d in days:                                            # ORB, 15% ATR stop, 1-min accurate, 1 micro
        sd = d["sd"] * 1.5; h, l, c, o = d["h"], d["l"], d["c"], d["o"]; side, i = 0, -1
        for j in range(5, 360):
            up, dn = h[j] > d["orh"], l[j] < d["orl"]
            if up and dn: break
            if up or dn: side, i = (1 if up else -1), j; break
        if side == 0: rows.append(0.0); continue
        entry = max(d["orh"] + .25, o[i]) if side > 0 else min(d["orl"] - .25, o[i])
        R, _ = fp.trade(h, l, c, i, side, entry, sd, 0., 0, 0., 0., 0., 0., 0., 0.)
        rows.append(R * sd * MICRO["NQ"] - COST["NQ"])
    S["NQ ORB 15%"] = pd.Series(rows, index=idx)
    for sym, L in (("NQ", NQ_LAB), ("GC", GC_LAB)):
        for name, fam, tf, ses, stop, ext in L:
            df = oc.lab_points(sym, fam, tf, ses, stop, ext)
            pnl = df.pts * MICRO[sym] - COST[sym]
            S[name] = pnl.groupby(df.date).sum().reindex(idx, fill_value=0)
    return pd.DataFrame(S).fillna(0)


def stats(x):
    eq = x.cumsum(); m = x.resample("ME").sum(); act = x[x != 0]
    return dict(per_day=x.mean(), green_days=100 * (act > 0).mean(), worst_day=x.min(), max_dd=(eq.cummax() - eq).max(),
                green_months=100 * (m > 0).mean(), worst_month=m.min(), last6m_per_day=x[x.index >= "2026-04-01"].mean())


def lucid_funded(pnl, start):
    """FUNDED LucidDaily: $50k, $2k trailing (EOD approx) locks at $50,100, withdraw down to $52,100 whenever >= $52,600 (90%)."""
    bal = peak = 50000.; floor = 48000.; paid = 0.; d = 0
    for i in range(start, len(pnl)):
        bal += pnl[i]; d += 1
        if bal <= floor: return paid, d, True
        if bal > peak: peak = bal; floor = min(max(floor, peak - 2000), 50100)
        if bal >= 52600: paid += (bal - 52100) * 0.9; bal = 52100.
    return paid, d, False


def lucid_eval(pnl, start, max_days=40):
    bal = peak = 0.; best = 0.; n = 0
    for i in range(start, min(len(pnl), start + max_days)):
        p = max(pnl[i], -1200)
        if p == 0: continue
        n += 1; bal += p; best = max(best, p)
        if bal <= peak - 2000: return False, i - start + 1
        peak = max(peak, bal)
        if bal >= 3000 and best <= 0.5 * bal and n >= 2: return True, i - start + 1
    return False, max_days


if __name__ == "__main__":
    P = build(); P.to_parquet("portfolio_daily_1micro.parquet")
    pd.set_option("display.width", 220)
    print("EACH STRATEGY, 1 micro (MNQ $2/pt, MGC $10/pt), fees + slippage, Oct 2023 -> Oct 2026:")
    print(pd.DataFrame({k: stats(P[k]) for k in P}).T.round(1).to_string())
    tot = P.sum(axis=1)
    print("\nALL 7 TOGETHER, 1 micro each:"); print(pd.Series(stats(tot)).round(1).to_string())
    print("\nSCALED (same strategies, N micros each = N/10 minis):")
    for n in (2, 5, 8, 10, 15, 20):
        s = stats(tot * n); print(f"  {n:2d} micros each: ${s['per_day']:7.0f}/day avg (last 6 mo ${s['last6m_per_day']:6.0f}/day) | green days {s['green_days']:.0f}% | worst day ${s['worst_day']:,.0f} | max drawdown ${s['max_dd']:,.0f} | worst month ${s['worst_month']:,.0f}")
    print("\nLUCIDDAILY 50K: eval pass (start every day) and FUNDED payouts:")
    for n in (2, 3, 5, 8, 10):
        pnl = (tot * n).values
        ev = [lucid_eval(pnl, s) for s in range(20, len(pnl) - 45)]
        fu = [lucid_funded(pnl, s) for s in range(20, len(pnl) - 130, 5)]
        paid = np.array([f[0] for f in fu]); life = np.array([f[1] for f in fu]); blown = np.array([f[2] for f in fu])
        per_month = (paid / np.maximum(life, 1) * 21).mean()
        print(f"  {n:2d} micros each: eval pass {100*np.mean([e[0] for e in ev]):4.1f}% (median {np.median([e[1] for e in ev if e[0]]) if any(e[0] for e in ev) else 0:.0f} days) | funded: "
              f"blown {100*blown.mean():.0f}% (median life {np.median(life):.0f} days), avg paid ${paid.mean():,.0f} per account, ~${per_month:,.0f}/month while alive")
