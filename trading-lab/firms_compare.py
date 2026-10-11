# Compare prop firms with OUR 6 strategies (and a zero-edge coin flip): net $ per eval bought = P(pass) x avg funded payouts - fee.
# Rules from public 2026 sources (simplified; confirm on firm sites). End-of-day drawdown approximations.
#   python firms_compare.py
import numpy as np, pandas as pd

FIRMS = {
    # name: fee, eval(target, dd, consistency or 0, min_days, dll or 0), funded(dd, lock_above_start, payout model)
    "Topstep 50K":          dict(fee=85,  size=3, ev=(3000, 2000, .50, 2, 0),    fu=dict(dd=2000, lock=0,   mode="cycle", days=5, min_day=150, frac=.5, cap=5000, minpay=125, split=.9, cons=0)),
    "LucidDaily 50K":       dict(fee=150, size=3, ev=(3000, 2000, .50, 2, 1200), fu=dict(dd=2000, lock=100, mode="keep", keep=2100, minpay=500, split=.9)),
    "FundedNext Rapid 50K": dict(fee=150, size=3, ev=(3000, 2000, 0, 1, 0),      fu=dict(dd=2000, lock=100, mode="cycle", days=5, min_day=0, frac=1., cap=1500, minpay=250, split=.8, cons=.4)),
    "FundedNext Rapid 25K": dict(fee=80,  size=2, ev=(1500, 1000, 0, 1, 0),      fu=dict(dd=1000, lock=100, mode="cycle", days=5, min_day=0, frac=1., cap=800, minpay=250, split=.8, cons=.4)),
    "FundedNext Legacy 50K":dict(fee=165, size=3, ev=(3000, 2000, .40, 2, 0),    fu=dict(dd=2000, lock=100, mode="cycle", days=5, min_day=150, frac=.5, cap=6000, minpay=250, split=.8, cons=0)),
}


def eval_pass(pnl, s, target, dd, cons, min_days, dll, max_days=60):
    bal = peak = best = 0.; n = 0
    for i in range(s, min(len(pnl), s + max_days)):
        p = max(pnl[i], -dll) if dll else pnl[i]
        if p == 0: continue
        n += 1; bal += p; best = max(best, p)
        if bal <= peak - dd: return False
        peak = max(peak, bal)
        if bal >= target and n >= min_days and (not cons or best <= cons * bal): return True
    return False


def funded(pnl, s, f, horizon=250):
    bal = peak = 0.; floor = -f["dd"]; paid = 0.; days = 0; cyc = []
    for i in range(s, min(len(pnl), s + horizon)):
        p = pnl[i]
        if p == 0: continue
        bal += p; days += 1; cyc.append(p)
        if bal <= floor: break
        if bal > peak: peak = bal; floor = min(max(floor, peak - f["dd"]), f["lock"])
        if f["mode"] == "keep":
            if bal >= f["keep"] + f["minpay"]: paid += (bal - f["keep"]) * f["split"]; bal = f["keep"]
        else:
            good = sum(1 for x in cyc if x >= max(f["min_day"], 1))
            prof = bal
            if len(cyc) >= f["days"] and good >= (f["days"] if f["min_day"] else 1) and prof >= f["minpay"]:
                pos = [x for x in cyc if x > 0]
                if not f["cons"] or (pos and max(pos) <= f["cons"] * sum(pos)):
                    amt = min(prof * f["frac"], f["cap"]); paid += amt * f["split"]; bal -= amt; cyc = []
    return paid


def firm_ev(pnl, F):
    st = range(20, len(pnl) - 130, 2)
    ps = np.mean([eval_pass(pnl, s, *F["ev"]) for s in st])
    pay = np.mean([funded(pnl, s, F["fu"]) for s in st])
    return ps * 100, pay, ps * pay - F["fee"] * (1 + 0.3)          # ~30% extra for resets / extra months


if __name__ == "__main__":
    P = pd.read_parquet("portfolio_daily_1micro.parquet"); good = P.drop(columns=["NQ Asia supertrend"]).sum(axis=1)
    rng = np.random.default_rng(11); coin = good.abs() * np.where(rng.random(len(good)) < .5, 1, -1)
    print(f"{'firm':24s} {'fee':>5s} size | OUR STRATEGIES: pass%  avg funded payout  NET/eval | COIN FLIP: pass%  NET/eval")
    for name, F in FIRMS.items():
        for size in sorted({F['size'] - 1, F['size'], F['size'] + 2} - {0}):
            a = firm_ev((good * size).values, F); b = firm_ev((coin * size).values, F)
            print(f"{name:24s} ${F['fee']:4d}  x{size}  |      {a[0]:5.1f}%      ${a[1]:7,.0f}     ${a[2]:+6,.0f}  |      {b[0]:5.1f}%   ${b[2]:+6,.0f}")
