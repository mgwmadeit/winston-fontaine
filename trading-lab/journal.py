# TRADE JOURNAL: every trade the farm (or later the live bot) takes is written down automatically.
#   trading\journal\trades.csv          one row per closed trade (all details, lane $ results, MFE/MAE, context, Moses's Take/Skip)
#   trading\journal\charts\<id>.png     the exit chart for that trade
#   trading\journal\YYYY-MM-DD.md       daily journal page (written at 5 PM ET by propfarm)
#   trading\journal\LESSONS.md          auto-updated lessons: what works, what loses, money left on the table, your picks vs the bot
#   python journal.py lessons           -> rebuild LESSONS.md now
import os, sys, csv, datetime as dt
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
JDIR = os.path.join(HERE, "..", "journal"); CHARTS = os.path.join(JDIR, "charts"); CSV = os.path.join(JDIR, "trades.csv")
FIELDS = ["id", "mode", "market", "strategy", "side", "entry_time", "exit_time", "minutes_held", "entry", "stop", "target", "exit", "result",
          "points", "R", "risk_pts", "mfe_R", "mae_R", "left_on_table_R", "session", "weekday", "hour_et", "atr", "day_range_so_far",
          "moses_decision", "lane_pnl", "chart", "logged_at"]


def _session(ts):
    m = ts.hour * 60 + ts.minute
    if 570 <= m < 960: return "NY"
    if 180 <= m < 570: return "London/pre-market"
    if 960 <= m < 1080: return "after hours"
    return "Asia"


def already_logged():
    if not os.path.exists(CSV): return set()
    try: return set(pd.read_csv(CSV, usecols=["id"]).id.astype(str))
    except Exception: return set()


def record(t, m1, lane_pnl, decision="", png=None, mode="PAPER", atr=None):
    """append one CLOSED trade. t = propfarm trade dict; m1 = 1-min bars of its market; lane_pnl = {lane: $}"""
    os.makedirs(CHARTS, exist_ok=True)
    side = t["side"]; risk = abs(t["entry"] - t["stop"]) or 1e-9
    w = m1[(m1.index >= t["entry_ts"]) & (m1.index <= t["exit_ts"])]
    if len(w):
        fav = (w.High.max() - t["entry"]) * side if side > 0 else (t["entry"] - w.Low.min())
        adv = (t["entry"] - w.Low.min()) if side > 0 else (w.High.max() - t["entry"])
    else: fav = adv = 0.0
    day = m1[(m1.index.date == t["entry_ts"].date()) & (m1.index <= t["entry_ts"])]
    R = (t["exit"] - t["entry"]) * side / risk
    chart = ""
    if png:
        chart = os.path.join("charts", f"{t['id'].replace('|', '_')}.png")
        with open(os.path.join(JDIR, chart), "wb") as f: f.write(png)
    row = dict(id=t["id"], mode=mode, market=t.get("sym", "NQ"), strategy=t["strat"], side="LONG" if side > 0 else "SHORT",
               entry_time=f"{t['entry_ts']:%Y-%m-%d %H:%M}", exit_time=f"{t['exit_ts']:%Y-%m-%d %H:%M}",
               minutes_held=int((t["exit_ts"] - t["entry_ts"]).total_seconds() // 60), entry=round(t["entry"], 2), stop=round(t["stop"], 2),
               target=round(t["target"], 2) if t.get("target") else "", exit=round(t["exit"], 2),
               result="WIN" if R > 0.05 else ("LOSS" if R < -0.05 else "SCRATCH"), points=round((t["exit"] - t["entry"]) * side, 2),
               R=round(R, 2), risk_pts=round(risk, 2), mfe_R=round(fav / risk, 2), mae_R=round(adv / risk, 2),
               left_on_table_R=round(fav / risk - R, 2), session=_session(t["entry_ts"]), weekday=f"{t['entry_ts']:%a}",
               hour_et=t["entry_ts"].hour, atr=round(atr, 2) if atr else "", day_range_so_far=round(day.High.max() - day.Low.min(), 2) if len(day) else "",
               moses_decision=decision, lane_pnl="; ".join(f"{k} ${v:+,.0f}" for k, v in lane_pnl.items()), chart=chart,
               logged_at=dt.datetime.now().isoformat(timespec="seconds"))
    new = not os.path.exists(CSV)
    with open(CSV, "a", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS)
        if new: wr.writeheader()
        wr.writerow(row)
    return row


def daily_page(date, report_text=""):
    os.makedirs(JDIR, exist_ok=True)
    if not os.path.exists(CSV): return
    j = pd.read_csv(CSV); j = j[j.exit_time.str.startswith(str(date))]
    lines = [f"# Trade journal {date}", "", report_text.replace("\n", "  \n") if report_text else "", "",
             "| time | market | strategy | side | entry -> exit | R | best it got (MFE) | worst (MAE) | you | lanes |", "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in j.iterrows():
        lines.append(f"| {r.entry_time[11:]}-{r.exit_time[11:]} | {r.market} | {r.strategy} | {r.side} | {r.entry} -> {r.exit} | {r.R:+.2f} | "
                     f"{r.mfe_R:+.2f}R | -{r.mae_R:.2f}R | {r.moses_decision if isinstance(r.moses_decision, str) else ''} | {r.lane_pnl} |")
    if j.empty: lines.append("| no closed trades today | | | | | | | | | |")
    open(os.path.join(JDIR, f"{date}.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def lessons():
    """auto-analysis of the whole journal -> LESSONS.md (what Claude reads first in future sessions)"""
    if not os.path.exists(CSV): return "no trades yet"
    j = pd.read_csv(CSV)
    if j.empty: return "no trades yet"
    def tab(g):
        a = j.groupby(g).agg(trades=("R", "size"), win_pct=("R", lambda x: round(100 * (x > 0).mean())), total_R=("R", "sum"), avg_R=("R", "mean"),
                             avg_left_R=("left_on_table_R", "mean")).round(2)
        return a.sort_values("total_R", ascending=False).to_markdown()
    out = [f"# LESSONS (auto-built from {len(j)} journaled trades, updated {dt.datetime.now():%Y-%m-%d %H:%M})", "",
           f"Overall: {len(j)} trades, win {100*(j.R>0).mean():.0f}%, total {j.R.sum():+.1f}R, avg {j.R.mean():+.2f}R. "
           f"Average best open profit (MFE) {j.mfe_R.mean():+.2f}R vs result {j.R.mean():+.2f}R -> {j.left_on_table_R.mean():.2f}R left on the table per trade.", "",
           "## By strategy", tab("strategy"), "", "## By market", tab("market"), "", "## By session", tab("session"), "",
           "## By weekday", tab("weekday"), "", "## By hour (ET)", tab("hour_et"), ""]
    gave_back = j[(j.mfe_R >= 1) & (j.R <= 0)]
    out += [f"## Round trips (was up 1R+ and finished flat or red): {len(gave_back)} of {len(j)} trades "
            f"({100*len(gave_back)/len(j):.0f}%). If high, add a profit lock (Moses's rule: don't let green trades go back to entry).", ""]
    if "moses_decision" in j and j.moses_decision.notna().any():
        d = j[j.moses_decision.isin(["take", "skip"])]
        if len(d):
            tk, sk = d[d.moses_decision == "take"], d[d.moses_decision == "skip"]
            out += ["## Moses's picks vs the bot",
                    f"Took {len(tk)}: {tk.R.sum():+.1f}R (win {100*(tk.R>0).mean() if len(tk) else 0:.0f}%). Skipped {len(sk)}: those would have made {sk.R.sum():+.1f}R. "
                    + ("-> His skips are SAVING money." if sk.R.sum() < 0 else "-> His skips are COSTING money (the bot should take them)."), ""]
    worst = j.nsmallest(5, "R")[["id", "strategy", "session", "R", "mae_R"]]; best = j.nlargest(5, "R")[["id", "strategy", "session", "R", "mfe_R"]]
    out += ["## 5 best trades", best.to_markdown(index=False), "", "## 5 worst trades", worst.to_markdown(index=False), ""]
    txt = "\n".join(out)
    open(os.path.join(JDIR, "LESSONS.md"), "w", encoding="utf-8").write(txt)
    return txt


if __name__ == "__main__":
    if sys.argv[1:] == ["lessons"]: print(lessons()[:3000])
