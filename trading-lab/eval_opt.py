# EVAL PASS-RATE OPTIMIZER (Topstep 50K: +$3,000 target, $2,000 EOD trailing, 50% consistency, $85/month)
# Replays our real daily results (NQ combo, + gold lane) starting an eval on every trading day, with different SIZING RULES.
#   python eval_opt.py
import numpy as np, pandas as pd
import evalfarm as ef

TARGET, DD, CONS, FEE = 3000, 2000, 0.50, 85
F = ef.FIRMS["Topstep 50K"]


def eval_run(R, start, rule, max_days=250):
    """R = daily result in R (1R = $1 risk). rule(state)->$ risk for today. Returns (passed, trading_days, fees)."""
    bal = peak = 0.0; best = 0.0; n = 0; days = 0; fees = FEE; i = start
    while i < len(R) and days < max_days:
        r = R[i]; i += 1; days += 1
        if days % 21 == 0: fees += FEE
        if r == 0: continue
        risk = rule(bal, peak, n, best)
        if risk <= 0: continue
        p = r * risk; n += 1
        bal += p; best = max(best, p)
        if bal <= peak - DD: return False, days, fees
        peak = max(peak, bal)
        if bal >= TARGET and best <= CONS * bal and n >= 2: return True, days, fees
    return False, days, fees


def fixed(x): return lambda bal, peak, n, best: x
def room_pct(f, cap=600, floor_min=50):                     # risk a % of the room left above the trailing floor
    return lambda bal, peak, n, best: max(floor_min, min(cap, f * (bal - (peak - DD))))
def room_target(f, g, cap=600):                             # % of room, but never more than g x what's left to the target
    return lambda bal, peak, n, best: max(50, min(cap, f * (bal - (peak - DD)), g * max(TARGET - bal, 150)))
def consistency_safe(f, cap=600):                           # also keep any single day under ~45% of the target -> no consistency stall
    return lambda bal, peak, n, best: max(50, min(cap, f * (bal - (peak - DD)), 0.45 * TARGET / 3.0))


def score(R, rule, horizon):
    res = [eval_run(R, s, rule, horizon) for s in range(20, len(R) - 40)]
    ps = np.array([r[0] for r in res]); d = np.array([r[1] for r in res]); fees = np.array([r[2] for r in res])
    return ps.mean() * 100, np.median(d[ps]) if ps.any() else np.nan, fees.mean()


if __name__ == "__main__":
    sets = ef.daily_R()
    base = sets["ORB + Asia engulf + VWAP fade"]
    combos = {"NQ combo": base.values}
    try:
        import pandas as pd
        meta = pd.read_csv("lab_meta_GC.csv"); tr = pd.read_parquet("lab_trades_GC.parquet")
        def g(fam, tf, ses, stop, ex):
            sid = meta[(meta.family == fam) & (meta.tf == tf) & (meta.session == ses) & (meta.stop == stop) & (meta.exit == ex)].id.iloc[0]
            t = tr[tr.id == sid].copy(); t["d"] = (t.ts.dt.tz_convert("America/New_York") + pd.Timedelta(hours=6)).dt.normalize().dt.tz_localize(None)
            return t.groupby("d").R.sum().reindex(base.index, fill_value=0)
        gold = g("donchian55_break", 60, "ASIA", "atr10", "hold") + g("volume_spike3x_FADE", 5, "AFTER10_AM", "fix8", "hold")
        combos["NQ combo + gold (half)"] = (base + 0.5 * gold).values
    except Exception as e:
        print("gold skipped:", e)
    rules = {"fixed $200": fixed(200), "fixed $300": fixed(300), "fixed $400": fixed(400), "fixed $150": fixed(150), "fixed $100": fixed(100),
             "room 10%": room_pct(.10), "room 15%": room_pct(.15), "room 20%": room_pct(.20), "room 25%": room_pct(.25),
             "room 15% + target cap 0.5": room_target(.15, .5), "room 20% + target cap 0.5": room_target(.20, .5),
             "room 20% + target cap 0.33": room_target(.20, .33), "room 25% + target cap 0.4": room_target(.25, .4),
             "room 20% + consistency-safe": consistency_safe(.20)}
    rows = []
    for cname, R in combos.items():
        for rname, rule in rules.items():
            for hz in (42, 84, 250):                         # ~2 months, ~4 months, no limit (1 yr)
                p, d, fee = score(R, rule, hz)
                rows.append(dict(strategy=cname, rule=rname, horizon=f"{hz}d", pass_pct=round(p, 1), median_days=d, avg_fees=round(fee)))
    df = pd.DataFrame(rows)
    df.to_csv("eval_opt_results.csv", index=False)
    pv = df.pivot_table(index=["strategy", "rule"], columns="horizon", values=["pass_pct", "median_days", "avg_fees"])
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print(pv[[("pass_pct", "42d"), ("pass_pct", "84d"), ("pass_pct", "250d"), ("median_days", "250d"), ("avg_fees", "250d")]].round(1).to_string())
