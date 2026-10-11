# EBOOK BUILDER: turns the strategy rules + backtests + the automatic trade journal into an ebook draft.
#   trading\ebook\MGW-Prop-Farm-Playbook.md  (+ charts copied next to it)   ->  python ebook.py
# Each strategy chapter: the idea, the exact step-by-step entry checklist, backtest numbers, live/paper journal stats,
# and real example trades (best + worst) with the bot's reasoning and the chart. Honest results only (paper vs live labeled).
import os, shutil, datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
JDIR = os.path.join(HERE, "..", "journal"); OUT = os.path.join(HERE, "..", "ebook")

CHAPTERS = {
    "ORB": dict(title="The 9:30 Opening Range Breakout (Nasdaq)", market="NQ / MNQ",
        idea="The first 5 minutes of the New York open set the day's battle lines. When price breaks out of that range, trend days run for hours. "
             "Most breakouts fail, but the few big trend days pay for everything, so you never cap the winner.",
        rules=["Mark the high and low of the 9:30-9:35 ET opening range.", "Wait for the FIRST 1-minute break above the high (long) or below the low (short). One trade per day.",
               "Enter at the range high + 1 tick (long) / low - 1 tick (short).", "Stop = 15% of the 14-day average daily range from the entry.",
               "No target. Hold to 4:00 PM unless stopped.", "Risk a fixed dollar amount per trade; contracts = risk / (stop points x $ per point)."],
        backtest="3 years of 1-minute NQ data (stops checked minute by minute): positive in all 3 test periods (+42R / +5.5R / +12R), profit factor ~1.1. "
                 "Win rate ~25%: expect long losing streaks; the edge comes from a handful of trend days."),
    "ASIA": dict(title="The Asia Session Engulfing Candle (Nasdaq)", market="NQ / MNQ",
        idea="Overnight, Nasdaq drifts quietly. A 15-minute candle that completely engulfs the previous one shows a real shift in control, and price tends to follow it.",
        rules=["Trade only 7 PM-2 AM ET.", "On the 15-minute chart, wait for a candle whose body engulfs the previous candle's body in the opposite color.",
               "Enter with it at the next minute's open.", "Stop = 10% of the 14-day average daily range.", "Target = 2R. If neither hits, close at 2:55 AM. Max 2 trades a night."],
        backtest="The most robust setup in a 15,000-strategy test: 12 of 16 setting combinations were profitable in every test period."),
    "VWAP": dict(title="The VWAP 2-Sigma Snap-Back (Nasdaq)", market="NQ / MNQ",
        idea="VWAP is the market's fair price for the day. When an hourly candle closes more than 2 standard deviations away, it's overstretched, and it tends to snap back.",
        rules=["New York session only (9:30-3:30 ET), 60-minute candles.", "Compute session VWAP and its standard deviation bands.",
               "When an hourly candle CLOSES beyond the 2-sigma band, fade it at the next minute's open.", "Stop = 10% of the 14-day average daily range.",
               "Exit after 60 minutes (or the stop)."],
        backtest="Positive in all 3 test periods; also one of the few setups that works AFTER 10 AM (11 of 16 settings profitable)."),
    "G_ASIA": dict(title="The Gold Asia Breakout", market="Gold (GC / MGC)",
        idea="Gold makes its real moves out of the Asia session. When an hourly candle closes beyond the last 55 hours' range, go WITH the breakout. Fading it loses.",
        rules=["Gold, 7 PM-2 AM ET, 60-minute candles.", "Mark the highest high and lowest low of the previous 55 hourly candles.",
               "When an hourly candle CLOSES beyond that range, enter in the breakout direction at the next minute's open.",
               "Stop = 10% of the 14-day average daily range.", "No target. Hold until 2:55 AM."],
        backtest="9 of 16 setting combinations profitable in every period on 3 years of gold futures (most profit came in 2026's gold rally)."),
    "G_SPIKE": dict(title="The Gold Volume-Spike Fade", market="Gold (GC / MGC)",
        idea="When a 5-minute gold candle prints 3x normal volume and a huge range late in the morning, the move is usually exhausted. Fade it.",
        rules=["Gold, 10:00 AM-12:00 PM ET, 5-minute candles.", "Volume at least 3x the 20-candle average AND range at least 1.5x the average range.",
               "Fade the candle's direction at the next minute's open.", "Fixed $8 stop.", "Hold to 3:55 PM unless stopped."],
        backtest="7 of 16 setting combinations profitable in every period on 3 years of gold futures."),
}


def build():
    os.makedirs(os.path.join(OUT, "charts"), exist_ok=True)
    j = pd.read_csv(os.path.join(JDIR, "trades.csv")) if os.path.exists(os.path.join(JDIR, "trades.csv")) else pd.DataFrame()
    md = [f"# The MGW Prop Farm Playbook", f"*Draft auto-built {dt.datetime.now():%B %d, %Y} from backtests and the bot's own trade journal.*", "",
          "## How to read this book",
          "Every strategy here was tested on years of real futures data with stops checked minute by minute, then traded by a bot that wrote down WHY it took every trade. "
          "Results are labeled honestly as BACKTEST, PAPER (simulated live), or LIVE. Trading futures is risky; past results don't guarantee future results.", "",
          "## The prop-firm engine",
          "Prop firm evaluations cost $80-150. You keep the profits from funded accounts, and the firm takes the drawdown losses. That lopsided structure is where the money "
          "is: the strategies below are the engine that drives it, sized to the firm's rules.", ""]
    for key, c in CHAPTERS.items():
        md += [f"# {c['title']}", f"**Market:** {c['market']}", "", "## The idea", c["idea"], "", "## The exact entry checklist"]
        md += [f"{i + 1}. {r}" for i, r in enumerate(c["rules"])] + ["", "## Backtest", c["backtest"], ""]
        t = j[j.strategy == key] if len(j) else pd.DataFrame()
        if len(t):
            md += ["## From the bot's journal", f"{len(t)} trades ({', '.join(sorted(t['mode'].unique()))}): win {100*(t.R>0).mean():.0f}%, total {t.R.sum():+.1f}R, "
                   f"average best open profit {t.mfe_R.mean():+.2f}R.", ""]
            for label, ex in (("Best examples", t[t.R > 0].nlargest(3, "R")), ("Losing examples (they happen)", t[t.R < 0].nsmallest(2, "R"))):
                if ex.empty: continue
                md += [f"### {label}"]
                for _, r in ex.iterrows():
                    md += [f"**{r.id}: {r.side}, {r.result} {r.R:+.2f}R** ({r.entry_time} -> {r.exit_time[11:]})"]
                    steps = r.why.split(" || ") if isinstance(r.why, str) and r.why else []
                    md += [f"{i + 1}. {x}" for i, x in enumerate(steps)]
                    if isinstance(r.chart, str) and r.chart and os.path.exists(os.path.join(JDIR, r.chart)):
                        dst = os.path.join("charts", os.path.basename(r.chart)); shutil.copy(os.path.join(JDIR, r.chart), os.path.join(OUT, dst))
                        md.append(f"![{r.id}]({dst.replace(chr(92), '/')})")
                    md.append("")
        else:
            md += ["## From the bot's journal", "*(examples get added automatically as the bot trades)*", ""]
    md += ["# Risk rules that keep you funded", "- Size every trade by dollar risk, never by feel.", "- Keep the size FLAT until funded; on a trailing drawdown a 'cushion' isn't real room.",
           "- One bad day can't end the account: daily loss stop.", "- Withdraw payouts the moment they're allowed.", ""]
    path = os.path.join(OUT, "MGW-Prop-Farm-Playbook.md"); open(path, "w", encoding="utf-8").write("\n".join(md))
    return path


if __name__ == "__main__":
    print("ebook draft ->", os.path.abspath(build()))
