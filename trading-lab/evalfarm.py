# EVAL FARM CALCULATOR: does buying evals pay at Moses's firms, with our strategies, at each risk size?
# Replays real daily P&L (NQ, Oct 2023 -> today) starting an eval on EVERY trading day; eval -> funded -> payouts.
# Rules are approximate public numbers (Oct 2026) and must be checked on each firm's site. PRICES ARE EDITABLE BELOW.
#   python evalfarm.py
import os, numpy as np, pandas as pd
from kron import MNQ
from published import orb2, rth
from run_published import load
HERE = os.path.dirname(os.path.abspath(__file__))

FIRMS = {  # price = what one eval attempt costs (1 month sub or reset), activation = fee when funded
    "Topstep 50K":     dict(price=85,  activation=0,   target=3000, dd=2000, consist=0.50, min_days=2, lock=50000,
                            pay_days=5, pay_min_day=150, pay_frac=0.50, pay_cap=5000, split=0.90, bot=True),
    "Lucid Flex 25K":  dict(price=100, activation=0,   target=1250, dd=1000, consist=0.50, min_days=2, lock=25100,
                            pay_days=5, pay_min_day=100, pay_frac=0.50, pay_cap=1000, split=0.90, bot=True, pay_min=500),
    "Lucid Flex 50K":  dict(price=136, activation=0,   target=3000, dd=2000, consist=0.50, min_days=2, lock=50100,
                            pay_days=5, pay_min_day=150, pay_frac=0.50, pay_cap=2000, split=0.90, bot=True, pay_min=500),
    "TPT 25K (manual)": dict(price=150, activation=130, target=1500, dd=1500, consist=0.50, min_days=5, lock=25000,
                            pay_days=5, pay_min_day=0, pay_frac=0.50, pay_cap=1500, split=0.80, bot=False),
    "TPT 50K (manual)": dict(price=170, activation=130, target=3000, dd=2000, consist=0.50, min_days=5, lock=50000,
                            pay_days=5, pay_min_day=0, pay_frac=0.50, pay_cap=3000, split=0.80, bot=False),
}
RISKS = [200, 300, 400, 600, 800, 1000]          # $ risked per trade (1R)
MAX_EVAL_DAYS, MAX_FUNDED_DAYS, MAX_PAYOUTS = 60, 120, 3


def daily_R():
    """Daily R (at 1R per trade) for each strategy set."""
    nq = load("NQ")
    days = pd.Index(sorted(set(pd.to_datetime(rth(nq).index.date))))
    orb = orb2(nq, MNQ, mode="breakout", atr_stop=0.10); orb["date"] = pd.to_datetime(orb["date"])
    r = rth(nq); f5 = r[(r.index.hour == 9) & (r.index.minute < 35)]
    v5 = f5.groupby(f5.index.date).Volume.sum(); v5.index = pd.to_datetime(v5.index)
    orb["rvol"] = orb.date.map(v5 / v5.rolling(14).mean().shift())
    meta = pd.read_csv(os.path.join(HERE, "lab_meta.csv")); tr = pd.read_parquet(os.path.join(HERE, "lab_trades.parquet"))
    tr["date"] = pd.to_datetime(tr["date"])
    def lab(fam, tf, ses, stop, ex):
        sid = meta[(meta.family == fam) & (meta.tf == tf) & (meta.session == ses) & (meta.stop == stop) & (meta.exit == ex)].id.iloc[0]
        t = tr[tr.id == sid].copy()
        t["date"] = (t.ts.dt.tz_convert("America/New_York") + pd.Timedelta(hours=6)).dt.normalize().dt.tz_localize(None)  # night trades count for next session
        return t.groupby("date").R.sum().reindex(days, fill_value=0)
    D = pd.DataFrame(index=days)
    D["ORB"] = orb.groupby("date").R.sum().reindex(days, fill_value=0)
    D["ORB_busy"] = orb[orb.rvol >= 1].groupby("date").R.sum().reindex(days, fill_value=0)
    D["ASIA_engulf"] = lab("engulfing", 15, "ASIA", "atr10", "2R")
    D["VWAP_fade60"] = lab("vwap_2sigma_break_FADE", 60, "NY", "atr10", "60min")
    D["AFTER10_lateORB"] = lab("orb15_break", 5, "AFTER10_AM", "fix40", "2R")
    D["AFTER10_vwapfade"] = lab("vwap_2sigma_break_FADE", 60, "AFTER10_ALL", "atr10", "60min")
    sets = {"ORB only": D.ORB, "ORB busy opens": D.ORB_busy,
            "ORB + Asia engulf + VWAP fade": D.ORB + D.ASIA_engulf + D.VWAP_fade60,
            "After-10 only (late ORB + VWAP fade)": D.AFTER10_lateORB + D.AFTER10_vwapfade}
    return sets


def run_account(pnl, F, start):
    """pnl: daily $ array. Returns (cost, payouts_$, passed, days_to_pass)."""
    bal, peak, best, n = 0.0, 0.0, 0.0, 0
    cost = F["price"]; i = start; passed = False
    while i < len(pnl) and n < MAX_EVAL_DAYS:
        p = pnl[i]; i += 1
        if p != 0: n += 1
        bal += p; best = max(best, p)
        if bal <= peak - F["dd"]: return cost, 0.0, False, n
        peak = max(peak, bal)
        if n % 21 == 0 and n: cost += F["price"]                      # another monthly fee
        if bal >= F["target"] and best <= F["consist"] * bal and n >= F["min_days"]: passed = True; break
    if not passed: return cost, 0.0, False, n
    days_pass = n
    cost += F["activation"]
    start_bal = F["lock"] - (F["lock"] % 25000)                       # 25000/50000
    bal = start_bal; peak = bal; floor = bal - F["dd"]; paid = 0.0; npay = 0; good_days = 0; k = 0
    while i < len(pnl) and k < MAX_FUNDED_DAYS and npay < MAX_PAYOUTS:
        p = pnl[i]; i += 1; k += 1
        bal += p
        if bal <= floor: break
        if bal > peak: peak = bal; floor = min(max(floor, peak - F["dd"]), F["lock"])
        if p >= max(F["pay_min_day"], 1): good_days += 1
        if good_days >= F["pay_days"] and bal > start_bal:
            amt = min((bal - start_bal) * F["pay_frac"], F["pay_cap"])
            if amt >= F.get("pay_min", 125):
                paid += amt * F["split"]; bal -= amt; npay += 1; good_days = 0
                floor = min(floor, bal - 1) if bal - 1 < floor else floor
    return cost, paid, True, days_pass


def main():
    sets = daily_R()
    rows = []
    recent_cut = pd.Timestamp("2026-04-01")
    for sname, R in sets.items():
        idx = R.index
        for firm, F in FIRMS.items():
            for risk in RISKS:
                pnl = (R.values * risk).astype(float)
                for per, starts in (("3yrs", range(20, len(idx) - 40)), ("last6m", [j for j in range(len(idx) - 40) if idx[j] >= recent_cut - pd.Timedelta(days=45)])):
                    res = [run_account(pnl, F, s) for s in starts]
                    cost = np.array([x[0] for x in res]); paid = np.array([x[1] for x in res]); ps = np.array([x[2] for x in res])
                    dtp = np.array([x[3] for x in res if x[2]])
                    rows.append(dict(strategy=sname, firm=firm, risk=risk, period=per, evals=len(res), pass_pct=ps.mean() * 100,
                                     days_to_pass=np.median(dtp) if len(dtp) else np.nan, avg_cost=cost.mean(), avg_payouts=paid.mean(),
                                     net_per_eval=(paid - cost).mean(), paid_pct=(paid > 0).mean() * 100))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(HERE, "evalfarm_results.csv"), index=False)
    piv = out.pivot_table(index=["strategy", "firm", "risk"], columns="period", values=["pass_pct", "days_to_pass", "paid_pct", "net_per_eval"]).round(1)
    pd.set_option("display.width", 250)
    for s in sets:
        print(f"\n=== {s} ===")
        print(piv.loc[s].to_string())
    best = out[out.period == "3yrs"].sort_values("net_per_eval", ascending=False).head(15)
    print("\nBEST 15 COMBOS (3 yrs, net $ per eval bought):")
    print(best.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
