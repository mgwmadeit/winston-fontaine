# #1 THE ALL-ROBUST PORTFOLIO (NQ + gold + ES), picked HONESTLY:
#   selection uses the TRAIN period only (Oct 2023-Sep 2025): a (family, timeframe, session) group qualifies if >= MIN_POS of its 16 settings
#   were profitable in TRAIN and its best TRAIN setting has PF >= 1.15 and >= 100 trades. We keep that best-TRAIN setting.
#   Then the whole portfolio is judged on data it never saw: TEST (Oct 2025-Mar 2026) + RECENT (Apr-Oct 2026).
#   RANDOM control strategies go through the same selection to show what luck alone looks like.
#   python portfolio_all.py
import os, numpy as np, pandas as pd
import firms_compare as fc

HERE = os.path.dirname(os.path.abspath(__file__))
TR, TE = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-04-01")
MARKETS = {"NQ": "", "GC": "_GC", "ES": "_ES"}
MIN_POS = 10


def pick(sym, sfx, random_only=False):
    r = pd.read_csv(os.path.join(HERE, f"lab_results{sfx}.csv"))
    r = r[r.random] if random_only else r[~r.random]
    chosen = []
    for key, g in r.groupby(["family", "tf", "session"]):
        if (g.train_totR > 0).sum() < (MIN_POS if not random_only else 1): continue
        b = g.sort_values("train_totR", ascending=False).iloc[0]
        if b.train_n < 100 or not b.train_pf >= 1.15: continue
        chosen.append(b)
    return pd.DataFrame(chosen)


def daily(sym, sfx, ids, idx):
    tr = pd.read_parquet(os.path.join(HERE, f"lab_trades{sfx}.parquet"), columns=["id", "ts", "R"])
    tr = tr[tr.id.isin(ids)]
    tr["d"] = (tr.ts.dt.tz_convert("America/New_York") + pd.Timedelta(hours=6)).dt.normalize().dt.tz_localize(None)
    return {i: g.groupby("d").R.sum().reindex(idx, fill_value=0) for i, g in tr.groupby("id")}


def stats(x, label):
    out = [f"{label:44s}"]
    for p, sel in (("TRAIN (picked here)", x.index < TR), ("TEST unseen", (x.index >= TR) & (x.index < TE)), ("RECENT unseen", x.index >= TE)):
        y = x[sel]; eq = y.cumsum(); dd = (eq.cummax() - eq).max()
        out.append(f"{p}: {y.sum():+7.1f}R ({y.mean():+.2f}R/day, green days {100*(y[y!=0]>0).mean():.0f}%, DD {dd:.0f}R)")
    return " | ".join(out)


if __name__ == "__main__":
    idx = pd.Index(sorted(set((pd.read_parquet(os.path.join(HERE, "data", "NQ_1m.parquet")).index.tz_convert("America/New_York") + pd.Timedelta(hours=6)).normalize().tz_localize(None))))
    port, rnd, members = {}, {}, []
    for sym, sfx in MARKETS.items():
        if not os.path.exists(os.path.join(HERE, f"lab_results{sfx}.csv")): continue
        P = pick(sym, sfx); Rn = pick(sym, sfx, random_only=True)
        print(f"{sym}: {len(P)} strategy groups qualify on TRAIN only  (random controls passing the same bar: {len(Rn)})")
        for _, b in P.iterrows(): members.append(dict(market=sym, family=b.family, tf=b.tf, session=b.session, stop=b.stop, exit=b.exit, train_R=round(b.train_totR, 1), test_R=round(b.test_totR, 1), recent_R=round(b.recent_totR, 1)))
        for i, s in daily(sym, sfx, set(P.id), idx).items(): port[f"{sym}:{i}"] = s
        for i, s in daily(sym, sfx, set(Rn.id), idx).items(): rnd[f"{sym}:{i}"] = s
    M = pd.DataFrame(members); M.to_csv(os.path.join(HERE, "portfolio_all_members.csv"), index=False)
    pd.set_option("display.width", 220)
    print(f"\nPORTFOLIO = {len(port)} strategies (each risking 1 unit = $200 per trade)")
    print(M.sort_values(["market", "train_R"], ascending=[True, False]).to_string(index=False))
    P = pd.DataFrame(port).fillna(0); tot = P.sum(axis=1)
    print("\n" + stats(tot, f"ALL {len(port)} TOGETHER"))
    for sym in MARKETS:
        cols = [c for c in P if c.startswith(sym + ":")]
        if cols: print(stats(P[cols].sum(axis=1), f"  {sym} part ({len(cols)} strategies)"))
    if rnd:
        Rd = pd.DataFrame(rnd).fillna(0).sum(axis=1); print(stats(Rd, f"RANDOM controls picked the same way ({len(rnd)})"))
    unseen = tot[tot.index >= TR]
    print(f"\nOn UNSEEN data ({len(unseen)} days): avg {unseen.mean():+.2f}R/day. At $200 risk/strategy = ${unseen.mean()*200:+,.0f}/day; at $50 = ${unseen.mean()*50:+,.0f}/day.")
    # prop firm value with the portfolio, scaled so a strategy risks $X
    full = tot.values
    for per_risk in (25, 50, 75):
        pnl = full * per_risk
        for name in ("FundedNext Rapid 50K", "Topstep 50K", "LucidDaily 50K"):
            F = dict(fc.FIRMS[name]); a = fc.firm_ev(pnl, F)
            print(f"  {name:22s} ${per_risk}/strategy/trade: pass {a[0]:4.1f}%  avg funded payout ${a[1]:7,.0f}  NET/eval ${a[2]:+6,.0f}")
