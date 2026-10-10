# MGW PROP FARM (PAPER): free Yahoo data (NQ=F, ~10 min delayed) -> our 3 strategies -> paper Topstep 50K eval farm.
# Alerts: Telegram (chart + Take/Skip) and Discord (#paper, #daily-report). No broker, no real orders.
#   python propfarm.py            -> runs forever (start it Sunday before 6 PM ET; Startup .bat does this automatically)
#   python propfarm.py replay     -> dry run over the last few days, prints trades + accounts, sends nothing
#   python propfarm.py report     -> sends the daily report now
# Strategies (same rules as the backtests in lab.py / published.py):
#   ORB      5-min opening range breakout, stop 10% of 14-day RTH ATR, hold to close, 1/day
#   ASIA     15-min engulfing candle 7 PM-2 AM ET (go with it), stop 10% ATR, target 2R, flat 2:55 AM, max 2/night
#   VWAP     60-min close beyond VWAP +/-2 sigma -> FADE it, 9:30-3:30, stop 10% ATR, exit after 60 min, max 2/day
import os, sys, io, json, time, threading, datetime as dt
import numpy as np, pandas as pd, requests

HERE = os.path.dirname(os.path.abspath(__file__))
TZ = "America/New_York"
PV, TICK, FEE = 2.0, 0.25, 0.62                     # MNQ
STATE = os.path.join(HERE, "propfarm_state.json")
DECISIONS = os.path.join(HERE, "tg_decisions.csv")
EVAL_FEE = 85                                       # what Moses pays per Topstep 50K eval
RULES = dict(start=50000, target=3000, dd=2000, consist=0.50, min_days=2, lock=50000,
             pay_days=5, pay_min_day=150, pay_frac=0.50, pay_cap=5000, split=0.90)
TIERS = {"A": 200, "B": 400}                        # $ risk per trade for each farm lane

TG_TOKEN = open(os.path.join(HERE, "telegram_token.txt")).read().strip()
TG_CHAT = open(os.path.join(HERE, "telegram_chat_id.txt")).read().strip()
TG = f"https://api.telegram.org/bot{TG_TOKEN}"
DC_TOKEN = open(os.path.join(HERE, "discord_token.txt")).read().strip()
DC_CH = json.load(open(os.path.join(HERE, "discord_channels.json")))
DC = "https://discord.com/api/v10"


# ---------------------------------------------------------------- data
def fetch():
    import yfinance as yf
    m1 = yf.download("NQ=F", period="7d", interval="1m", progress=False, auto_adjust=False)
    m5 = yf.download("NQ=F", period="60d", interval="5m", progress=False, auto_adjust=False)
    out = []
    for d in (m1, m5):
        d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
        d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
        d.index = d.index.tz_convert(TZ).as_unit("ns")
        out.append(d)
    m1, m5 = out
    m1 = m1.iloc[:-1]                                   # last minute may still be forming
    return m1, m5


def daily_atr(m5):
    t = m5.index; tod = t.hour * 60 + t.minute
    r = m5[(tod >= 570) & (tod < 960)]
    D = r.groupby(r.index.date).agg(H=("High", "max"), L=("Low", "min"), C=("Close", "last"))
    D.index = pd.to_datetime(D.index)
    pc = D.C.shift()
    tr = pd.concat([D.H - D.L, (D.H - pc).abs(), (D.L - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean().shift()                 # ATR known BEFORE that day's open


def atr_for(atr, day):
    day = pd.Timestamp(day).normalize()
    s = atr[atr.index <= day]
    return float(s.iloc[-1]) if len(s) and not np.isnan(s.iloc[-1]) else np.nan


def tday(ts): return (ts + pd.Timedelta(hours=6)).normalize().tz_localize(None)


# ---------------------------------------------------------------- strategies -> trade list
def bars(m1, minutes, offset="0min"):
    b = m1.resample(f"{minutes}min", offset=offset).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()
    last_end = m1.index[-1] + pd.Timedelta(minutes=1)
    return b[b.index + pd.Timedelta(minutes=minutes) <= last_end]          # complete bars only


def run_exit(m1, i, side, entry, stop, tgt, end_i):
    """walk 1-min bars from i to end_i; stop first if both in one bar. Returns (exit_price, exit_index, closed?)"""
    H, L = m1.High.values, m1.Low.values
    last = min(end_i, len(m1) - 1)
    for j in range(i, last + 1):
        if side > 0:
            if L[j] <= stop: return stop, j, True
            if tgt is not None and H[j] >= tgt: return tgt, j, True
        else:
            if H[j] >= stop: return stop, j, True
            if tgt is not None and L[j] <= tgt: return tgt, j, True
    if end_i <= len(m1) - 1: return float(m1.Close.values[end_i]), end_i, True
    return float(m1.Close.values[-1]), len(m1) - 1, False                     # still open


def strat_orb(m1, atr):
    out = []
    t = m1.index; tod = t.hour * 60 + t.minute
    r = m1[(tod >= 570) & (tod < 960)]
    for day, d1 in r.groupby(r.index.date):
        d = d1.resample("5min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
        a = atr_for(atr, day)
        if len(d) < 2 or np.isnan(a): continue
        f = d.iloc[0]
        side = 0
        for k in range(1, min(len(d), 72)):
            b = d.iloc[k]
            if b.High > f.High and b.Low < f.Low: break
            if b.High > f.High: side, entry, k0 = 1, max(f.High + TICK, b.Open), k; break
            if b.Low < f.Low: side, entry, k0 = -1, min(f.Low - TICK, b.Open), k; break
        if not side: continue
        stop = entry - side * 0.10 * a
        if (entry - stop) * side < 8 * TICK: continue
        bar_start = d.index[k0]
        mins = d1[(d1.index >= bar_start) & (d1.index < bar_start + pd.Timedelta(minutes=5))]
        hit = mins[(mins.High > f.High)] if side > 0 else mins[(mins.Low < f.Low)]
        ets = hit.index[0] if len(hit) else bar_start
        # exit on 5-min bars like the backtest: entry bar counts only a CLOSE beyond the stop, then hold to close
        ex, xts, closed = None, None, False
        for j in range(k0, len(d)):
            b = d.iloc[j]
            if j > k0 and ((b.Low <= stop) if side > 0 else (b.High >= stop)): ex, xts = stop, d.index[j]; break
            if j == k0 and ((b.Close <= stop) if side > 0 else (b.Close >= stop)): ex, xts = stop, d.index[j] + pd.Timedelta(minutes=4); break
        if ex is None:
            if d.index[-1].hour * 60 + d.index[-1].minute >= 955:
                ex, xts = float(d.iloc[-1].Close), d.index[-1] + pd.Timedelta(minutes=4)
            else:
                ex, xts = float(d.iloc[-1].Close), None
        closed = xts is not None
        out.append(dict(strat="ORB", entry_ts=ets, side=side, entry=float(entry), stop=float(stop), target=None,
                        exit=float(ex), exit_ts=xts, closed=closed, rule="hold to 4 PM"))
    return out


def strat_asia(m1, atr):
    out = []
    b = bars(m1, 15)
    C, O = b.Close, b.Open
    longc = (C > O) & (C.shift() < O.shift()) & (C > O.shift()) & (O < C.shift())
    shortc = (C < O) & (C.shift() > O.shift()) & (C < O.shift()) & (O > C.shift())
    idx_ns = m1.index.asi8
    last_exit, cur_day, cnt = -1, None, 0
    for ts in b.index[(longc | shortc).values]:
        ct = ts + pd.Timedelta(minutes=15); todc = (ct.hour * 60 + ct.minute) % 1440
        if not (todc >= 1140 or todc <= 120): continue
        i = int(np.searchsorted(idx_ns, ct.value))
        if i >= len(m1) or (m1.index[i] - ct) > pd.Timedelta(minutes=5): continue
        side = 1 if longc[ts] else -1
        td = tday(ts)
        if i <= last_exit or (td == cur_day and cnt >= 2): continue
        a = atr_for(atr, td)
        if np.isnan(a): continue
        e = float(m1.Open.values[i]); sd = 0.10 * a
        flat = (ct.normalize() + pd.Timedelta(days=1 if todc >= 1140 else 0, minutes=175))
        end_i = int(np.searchsorted(idx_ns, flat.value, side="right")) - 1
        if flat > m1.index[-1]: end_i = 10 ** 9
        ex, xi, closed = run_exit(m1, i, side, e, e - side * sd, e + side * 2 * sd, end_i)
        out.append(dict(strat="ASIA", entry_ts=m1.index[i], side=side, entry=e, stop=e - side * sd, target=e + side * 2 * sd,
                        exit=ex, exit_ts=m1.index[xi] if closed else None, closed=closed, rule="2R target, flat 2:55 AM"))
        last_exit = xi if closed else 10 ** 9
        if td != cur_day: cur_day, cnt = td, 0
        cnt += 1
    return out


def strat_vwap(m1, atr):
    out = []
    b = bars(m1, 60, offset="30min")
    b["td"] = [tday(x) for x in b.index]
    tp = (b.High + b.Low + b.Close) / 3
    g = b.assign(pv=tp * b.Volume, pv2=tp * tp * b.Volume).groupby("td")
    cv = g.Volume.cumsum(); vw = g.pv.cumsum() / cv; sd_ = np.sqrt((g.pv2.cumsum() / cv - vw ** 2).clip(lower=0))
    C = b.Close
    up = (C > vw + 2 * sd_) & (C.shift() <= (vw + 2 * sd_).shift())
    dn = ((vw - 2 * sd_) > C) & ((vw - 2 * sd_).shift() <= C.shift())
    idx_ns = m1.index.asi8
    last_exit, cur_day, cnt = -1, None, 0
    for ts in b.index[(up | dn).values]:
        ct = ts + pd.Timedelta(minutes=60); todc = ct.hour * 60 + ct.minute
        if not (570 <= todc <= 930): continue
        i = int(np.searchsorted(idx_ns, ct.value))
        if i >= len(m1) or (m1.index[i] - ct) > pd.Timedelta(minutes=5): continue
        side = -1 if up[ts] else 1                                     # FADE
        td = b.td[ts]
        if i <= last_exit or (td == cur_day and cnt >= 2): continue
        a = atr_for(atr, td)
        if np.isnan(a): continue
        e = float(m1.Open.values[i]); sdist = 0.10 * a
        flat = ct.normalize() + pd.Timedelta(minutes=955)
        end_flat = int(np.searchsorted(idx_ns, flat.value, side="right")) - 1
        end_i = min(end_flat if flat <= m1.index[-1] else 10 ** 9, i + 59)
        ex, xi, closed = run_exit(m1, i, side, e, e - side * sdist, None, end_i)
        out.append(dict(strat="VWAP", entry_ts=m1.index[i], side=side, entry=e, stop=e - side * sdist, target=None,
                        exit=ex, exit_ts=m1.index[xi] if closed else None, closed=closed, rule="exit after 60 min"))
        last_exit = xi if closed else 10 ** 9
        if td != cur_day: cur_day, cnt = td, 0
        cnt += 1
    return out


def all_trades(m1, m5):
    atr = daily_atr(m5)
    tr = strat_orb(m1, atr) + strat_asia(m1, atr) + strat_vwap(m1, atr)
    for t in tr:
        t["id"] = f"{t['strat']}|{t['entry_ts']:%m%d%H%M}"
        t["risk_pts"] = abs(t["entry"] - t["stop"])
        t["pts"] = (t["exit"] - t["entry"]) * t["side"]
    return sorted(tr, key=lambda x: x["entry_ts"])


def pnl(t, risk_usd):
    q = int(risk_usd // (t["risk_pts"] * PV))
    return 0.0 if q < 1 else (t["pts"] * PV - 2 * TICK * PV - 2 * FEE) * q, q


# ---------------------------------------------------------------- paper accounts (stateless replay from the farm start)
def farm(trades, start_ts, only_ids=None):
    """Replays closed trades through Topstep 50K rules. Each lane: eval -> pass -> funded (and a NEW eval starts) / blow -> rebuy."""
    closed = [t for t in trades if t["closed"] and t["entry_ts"] >= start_ts and (only_ids is None or t["id"] in only_ids)]
    closed.sort(key=lambda t: t["exit_ts"])
    accts, ledger = [], {"fees": 0.0, "payouts": 0.0, "evals": 0, "passed": 0, "blown": 0}
    def new_eval(lane):
        ledger["fees"] += EVAL_FEE; ledger["evals"] += 1
        a = dict(name=f"{lane}-EVAL-{ledger['evals']}", lane=lane, risk=TIERS[lane], stage="eval", bal=RULES["start"], peak=RULES["start"],
                 floor=RULES["start"] - RULES["dd"], days={}, good=0, paid=0.0, status="active")
        accts.append(a); return a
    for lane in TIERS: new_eval(lane)
    for t in closed:
        d = tday(t["exit_ts"])
        for a in [x for x in accts if x["status"] == "active"]:
            p, q = pnl(t, a["risk"])
            if q < 1: continue
            if a["stage"] == "funded" and q > 1: p = p / q * max(1, q // 2)          # funded = half size
            a["bal"] += p; a["days"][d] = a["days"].get(d, 0) + p
            if a["bal"] <= a["floor"]:
                a["status"] = "blown"; ledger["blown"] += 1
                if a["stage"] == "eval": new_eval(a["lane"])
                continue
            prof = a["bal"] - RULES["start"]
            if a["stage"] == "eval":
                best = max(a["days"].values())
                if prof >= RULES["target"] and best <= RULES["consist"] * prof and len(a["days"]) >= RULES["min_days"]:
                    a.update(stage="funded", name=a["name"].replace("EVAL", "FUNDED"), bal=RULES["start"], peak=RULES["start"],
                             floor=RULES["start"] - RULES["dd"], days={}, good=0)
                    ledger["passed"] += 1; new_eval(a["lane"])
        # end-of-day trailing (EOD drawdown) and payout days, applied once per trading day boundary
        for a in [x for x in accts if x["status"] == "active"]:
            if a["bal"] > a["peak"]:
                a["peak"] = a["bal"]; a["floor"] = min(max(a["floor"], a["peak"] - RULES["dd"]), RULES["lock"] if a["stage"] == "funded" else 10 ** 9)
            if a["stage"] == "funded":
                a["good"] = sum(1 for v in a["days"].values() if v >= RULES["pay_min_day"])
                if a["good"] >= RULES["pay_days"] and a["bal"] > RULES["start"]:
                    amt = min((a["bal"] - RULES["start"]) * RULES["pay_frac"], RULES["pay_cap"])
                    a["bal"] -= amt; a["paid"] += amt * RULES["split"]; ledger["payouts"] += amt * RULES["split"]; a["days"] = {}
    return accts, ledger


# ---------------------------------------------------------------- messaging
def tg(method, **kw):
    try: return requests.post(f"{TG}/{method}", timeout=30, **kw).json()
    except Exception as e: print("tg error", e); return {}


def dc_post(ch, content=None, embed=None, png=None):
    h = {"Authorization": f"Bot {DC_TOKEN}"}
    payload = {"content": content or ""}
    if embed: payload["embeds"] = [embed]
    try:
        if png:
            if embed: embed["image"] = {"url": "attachment://chart.png"}
            return requests.post(f"{DC}/channels/{DC_CH[ch]}/messages", headers=h, timeout=30,
                                 data={"payload_json": json.dumps(payload)}, files={"files[0]": ("chart.png", png, "image/png")}).status_code
        return requests.post(f"{DC}/channels/{DC_CH[ch]}/messages", headers=h, json=payload, timeout=30).status_code
    except Exception as e: print("discord error", e)


def chart(m1, t, exit_mark=False):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    end = t["exit_ts"] if (exit_mark and t["exit_ts"] is not None) else t["entry_ts"]
    w = m1[(m1.index > end - pd.Timedelta(hours=3)) & (m1.index <= end + pd.Timedelta(minutes=5))]
    w = w.resample("5min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=110); fig.patch.set_facecolor("#111"); ax.set_facecolor("#111")
    for k, (ts, r) in enumerate(w.iterrows()):
        c = "#26a69a" if r.Close >= r.Open else "#ef5350"
        ax.vlines(k, r.Low, r.High, color=c, lw=1); ax.add_patch(plt.Rectangle((k - 0.3, min(r.Open, r.Close)), 0.6, max(abs(r.Close - r.Open), 0.25), color=c))
    ax.axhline(t["entry"], color="#4fc3f7", lw=1.2, label=f"entry {t['entry']:.2f}")
    ax.axhline(t["stop"], color="#ef5350", lw=1.2, ls="--", label=f"stop {t['stop']:.2f}")
    if t["target"]: ax.axhline(t["target"], color="#66bb6a", lw=1.2, ls="--", label=f"target {t['target']:.2f}")
    if exit_mark: ax.axhline(t["exit"], color="#ffd54f", lw=1.2, label=f"exit {t['exit']:.2f}")
    step = max(1, len(w) // 6)
    ax.set_xticks(range(0, len(w), step)); ax.set_xticklabels([w.index[i].strftime("%H:%M") for i in range(0, len(w), step)], color="#bbb", fontsize=8)
    ax.tick_params(colors="#bbb", labelsize=8); ax.legend(loc="upper left", fontsize=8, facecolor="#222", labelcolor="#ddd")
    ax.set_title(f"MNQ 5m  |  {t['strat']}  {'LONG' if t['side']>0 else 'SHORT'}  |  PAPER", color="#eee", fontsize=10)
    for s in ax.spines.values(): s.set_color("#333")
    buf = io.BytesIO(); fig.tight_layout(); fig.savefig(buf, format="png", facecolor=fig.get_facecolor()); plt.close(fig)
    return buf.getvalue()


NAMES = {"ORB": "ORB 5-min breakout", "ASIA": "Asia 15-min engulfing", "VWAP": "60-min VWAP 2σ fade"}

def entry_text(t):
    s = "🟢 LONG" if t["side"] > 0 else "🔴 SHORT"
    tg_ = f" | Target {t['target']:.2f}" if t["target"] else ""
    pa, qa = pnl(dict(t, pts=0), TIERS["A"]); pb, qb = pnl(dict(t, pts=0), TIERS["B"])
    return (f"🌾 PAPER ALERT: {NAMES[t['strat']]}\n{s} MNQ @ {t['entry']:.2f}  ({t['entry_ts']:%a %I:%M %p} ET)\n"
            f"Stop {t['stop']:.2f} ({t['risk_pts']:.1f} pts){tg_}\nExit rule: {t['rule']}\n"
            f"Size: lane A ${TIERS['A']} risk = {qa} MNQ | lane B ${TIERS['B']} = {qb} MNQ\n(data ~10 min delayed • paper only)")


def exit_text(t):
    pa, _ = pnl(t, TIERS["A"]); pb, _ = pnl(t, TIERS["B"])
    icon = "✅" if t["pts"] > 0 else "❌"
    return (f"{icon} CLOSED: {NAMES[t['strat']]} {'LONG' if t['side']>0 else 'SHORT'}\n"
            f"{t['entry']:.2f} → {t['exit']:.2f} ({t['pts']:+.1f} pts) at {t['exit_ts']:%I:%M %p} ET\n"
            f"Lane A: ${pa:+,.0f} | Lane B: ${pb:+,.0f}")


def decisions():
    if not os.path.exists(DECISIONS): return {}
    d = pd.read_csv(DECISIONS, encoding="utf-8")
    return dict(zip(d.trade_id.astype(str), d.decision))


def report_text(trades, state):
    start = pd.Timestamp(state["start"])
    accts, led = farm(trades, start)
    dec = decisions()
    taken = {k for k, v in dec.items() if v == "take"}
    maccts, mled = farm(trades, start, only_ids=taken)
    today = tday(pd.Timestamp.now(tz=TZ))
    tt = [t for t in trades if t["closed"] and tday(t["exit_ts"]) == today and t["entry_ts"] >= start]
    lines = [f"🌾 THE FARM AT THE CLOSE: {pd.Timestamp.now(tz=TZ):%a %b %d}", f"Trades closed today: {len(tt)}"]
    for t in tt:
        pa, _ = pnl(t, TIERS["A"]); lines.append(f"  • {t['strat']} {'L' if t['side']>0 else 'S'} {t['pts']:+.1f} pts (lane A ${pa:+,.0f})")
    lines.append("\nACCOUNTS (paper Topstep 50K):")
    for a in accts:
        icon = {"blown": "💀", "active": "🌱" if a["stage"] == "eval" else "🌽"}[a["status"]]
        prog = (f"{a['bal']-RULES['start']:+,.0f} / +{RULES['target']:,}" if a["stage"] == "eval" else f"bal {a['bal']:,.0f}, paid ${a['paid']:,.0f}")
        lines.append(f"  {icon} {a['name']} (${a['risk']} risk): {a['status']}, {prog}")
    net = led["payouts"] - led["fees"]
    lines.append(f"\nHARVEST: {led['evals']} evals bought (${led['fees']:,.0f} paper fees), {led['passed']} passed, {led['blown']} blown, "
                 f"${led['payouts']:,.0f} paid out → net ${net:+,.0f}")
    lines.append(f"YOUR PICKS (Take only): {len(taken)} taken → paid ${mled['payouts']:,.0f}, net ${mled['payouts']-mled['fees']:+,.0f}")
    return "\n".join(lines)


# ---------------------------------------------------------------- telegram listener (Take / Skip / commands)
def tg_listener(get_state):
    import csv
    offset = None
    while True:
        try:
            r = requests.get(f"{TG}/getUpdates", params={"timeout": 50, "offset": offset}, timeout=60).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                if "callback_query" in u:
                    cb = u["callback_query"]; action, _, tid = cb["data"].partition("|")
                    label = "✅ TAKEN (paper)" if action == "take" else "❌ SKIPPED"
                    tg("answerCallbackQuery", json={"callback_query_id": cb["id"], "text": label})
                    m = cb["message"]; cap = m.get("caption") or m.get("text") or ""
                    key = "caption" if "caption" in m else "text"
                    tg("editMessageCaption" if key == "caption" else "editMessageText",
                       json={"chat_id": m["chat"]["id"], "message_id": m["message_id"], key: f"{cap}\n\n{label} at {dt.datetime.now():%H:%M}"})
                    new = not os.path.exists(DECISIONS)
                    with open(DECISIONS, "a", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        if new: w.writerow(["time", "decision", "trade_id", "alert_text"])
                        w.writerow([dt.datetime.now().isoformat(timespec="seconds"), action, tid, cap.replace("\n", " | ")])
                elif "message" in u and str(u["message"]["chat"]["id"]) == TG_CHAT:
                    txt = (u["message"].get("text") or "").strip().lower()
                    st = get_state()
                    if txt in ("/status", "status", "/farm", "farm", "/report", "report") and st.get("trades") is not None:
                        tg("sendMessage", json={"chat_id": TG_CHAT, "text": report_text(st["trades"], st["state"])})
                    elif txt in ("/start", "/help", "help"):
                        tg("sendMessage", json={"chat_id": TG_CHAT, "text": "🌾 MGW Prop Farm (PAPER). Commands: status • help\nAlerts arrive here with Take/Skip. The farm trades every signal; your taps are tracked separately."})
        except Exception as e:
            print("listener error", e); time.sleep(5)


# ---------------------------------------------------------------- HUNTER SYSTEM dashboard (Solo Leveling style) -> dashboard\data.json
DASH = os.path.join(HERE, "dashboard")
RANKS = [("E", 0), ("D", 1000), ("C", 3000), ("B", 7500), ("A", 15000), ("S", 25000)]
DAILY_LOSS_LIMIT = 500


def dashboard_data(trades, start, mode):
    accts, led = farm(trades, start)
    mine = [t for t in trades if t["entry_ts"] >= start]
    closed = [t for t in mine if t["closed"]]
    dec = decisions()
    # XP: +10 per closed trade, +40 per green day, +500 per gate cleared, +1 per $10 paid
    days = {}
    for t in closed:
        d = tday(t["exit_ts"]); days[d] = days.get(d, 0) + pnl(t, TIERS["A"])[0]
    xp = 10 * len(closed) + 40 * sum(1 for v in days.values() if v > 0) + 500 * led["passed"] + int(led["payouts"] / 10)
    level = int((xp / 50) ** 0.5) + 1
    lo, hi = (level - 1) ** 2 * 50, level ** 2 * 50
    rank = [r for r, v in RANKS if led["payouts"] >= v][-1]
    nxt = next(((r, v) for r, v in RANKS if v > led["payouts"]), None)
    today = tday(pd.Timestamp.now(tz=TZ))
    tt = [t for t in closed if tday(t["exit_ts"]) == today]
    today_pnl = sum(pnl(t, TIERS["A"])[0] for t in tt)
    open_now = [t for t in mine if not t["closed"]]
    shadows = []
    for s in ("ORB", "ASIA", "VWAP"):
        st = [t for t in closed if t["strat"] == s]
        w = sum(1 for t in st if t["pts"] > 0); p = sum(pnl(t, TIERS["A"])[0] for t in st)
        shadows.append(dict(key=s, name={"ORB": "KNIGHT", "ASIA": "PHANTOM", "VWAP": "GOLEM"}[s], cls=NAMES[s], trades=len(st), wins=w,
                            losses=len(st) - w, pnl=round(p), level=1 + len(st) // 5 + max(0, int(p // 1000))))
    gates = []
    for a in accts:
        prof = a["bal"] - RULES["start"]
        if a["stage"] == "eval":
            pct = max(0, min(100, prof / RULES["target"] * 100)); goal = f"{prof:+,.0f} / +{RULES['target']:,}"
        else:
            pct = min(100, a["good"] / RULES["pay_days"] * 100); goal = f"{a['good']}/{RULES['pay_days']} payout days • paid ${a['paid']:,.0f}"
        room = a["bal"] - a["floor"]
        gates.append(dict(name=a["name"], lane=a["lane"], risk=a["risk"], stage=a["stage"], status=a["status"], pct=round(pct, 1),
                          goal=goal, room=round(room), danger=round(max(0, min(100, 100 - room / RULES["dd"] * 100)), 1)))
    log = []
    for t in sorted(mine, key=lambda x: x["exit_ts"] or x["entry_ts"], reverse=True)[:14]:
        p = pnl(t, TIERS["A"])[0]
        log.append(dict(time=f"{(t['exit_ts'] or t['entry_ts']):%a %I:%M %p}", strat=t["strat"], side="LONG" if t["side"] > 0 else "SHORT",
                        text=(f"{t['entry']:.2f} → {t['exit']:.2f} ({t['pts']:+.1f} pts)" if t["closed"] else f"OPEN @ {t['entry']:.2f}, stop {t['stop']:.2f}"),
                        pnl=round(p) if t["closed"] else None, you=dec.get(t["id"], "")))
    return dict(mode=mode, updated=f"{pd.Timestamp.now(tz=TZ):%a %b %d %I:%M %p} ET",
                hunter=dict(name="MOSESGOTWATER", rank=rank, level=level, xp=xp, xp_lo=lo, xp_hi=hi,
                            next_rank=nxt[0] if nxt else None, next_need=round(nxt[1] - led["payouts"]) if nxt else 0),
                quest=dict(pnl=round(today_pnl), limit=DAILY_LOSS_LIMIT, trades=len(tt), open=len(open_now),
                           held=today_pnl > -DAILY_LOSS_LIMIT),
                loot=dict(payouts=round(led["payouts"]), fees=round(led["fees"]), net=round(led["payouts"] - led["fees"]),
                          evals=led["evals"], passed=led["passed"], blown=led["blown"]),
                shadows=shadows, gates=gates, log=log)


def write_dashboard(trades, state):
    os.makedirs(DASH, exist_ok=True)
    start = pd.Timestamp(state["start"])
    live = [t for t in trades if t["entry_ts"] >= start]
    if live: d = dashboard_data(trades, start, "LIVE PAPER")
    else: d = dashboard_data(trades, trades[0]["entry_ts"] if trades else start, "DEMO: last week replay (paper starts Sun 6 PM ET)")
    tmp = os.path.join(DASH, "data.tmp"); json.dump(d, open(tmp, "w", encoding="utf-8")); os.replace(tmp, os.path.join(DASH, "data.json"))


def serve_dashboard(port=8787):
    import http.server, functools
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k): pass                     # pythonw has no console to log to
    h = functools.partial(Quiet, directory=DASH)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), h).serve_forever()


# ---------------------------------------------------------------- main loop
def load_state():
    if os.path.exists(STATE): return json.load(open(STATE))
    s = {"start": pd.Timestamp.now(tz=TZ).isoformat(), "sent_entry": [], "sent_exit": [], "last_report": ""}
    json.dump(s, open(STATE, "w")); return s


def market_closed(now):
    wd, hm = now.weekday(), now.hour * 60 + now.minute
    return (wd == 4 and hm >= 17 * 60 + 15) or wd == 5 or (wd == 6 and hm < 17 * 60 + 50)


def loop():
    state = load_state(); shared = {"trades": None, "state": state}
    threading.Thread(target=tg_listener, args=(lambda: shared,), daemon=True).start()
    os.makedirs(DASH, exist_ok=True)
    threading.Thread(target=serve_dashboard, daemon=True).start()
    print(f"Prop farm running. Paper start {state['start']}", flush=True)
    while True:
        now = pd.Timestamp.now(tz=TZ)
        try:
            if not market_closed(now) or shared["trades"] is None:
                m1, m5 = fetch()
                trades = all_trades(m1, m5); shared["trades"] = trades
                start = pd.Timestamp(state["start"])
                for t in trades:
                    if t["entry_ts"] < start: continue
                    if t["id"] not in state["sent_entry"]:
                        png = chart(m1, t)
                        btn = {"inline_keyboard": [[{"text": "✅ Take", "callback_data": f"take|{t['id']}"}, {"text": "❌ Skip", "callback_data": f"skip|{t['id']}"}]]}
                        tg("sendPhoto", data={"chat_id": TG_CHAT, "caption": entry_text(t), "reply_markup": json.dumps(btn)}, files={"photo": ("c.png", png)})
                        dc_post("paper", embed={"title": f"PAPER ENTRY: {NAMES[t['strat']]}", "description": entry_text(t), "color": 0x4fc3f7}, png=png)
                        state["sent_entry"].append(t["id"])
                    if t["closed"] and t["id"] not in state["sent_exit"]:
                        png = chart(m1, t, exit_mark=True)
                        tg("sendPhoto", data={"chat_id": TG_CHAT, "caption": exit_text(t)}, files={"photo": ("c.png", png)})
                        dc_post("paper", embed={"title": "PAPER EXIT", "description": exit_text(t), "color": 0x66bb6a if t["pts"] > 0 else 0xef5350}, png=png)
                        state["sent_exit"].append(t["id"])
                # 5 PM ET daily report (Mon-Fri)
                if now.weekday() < 5 and now.hour == 17 and now.minute >= 5 and state["last_report"] != str(now.date()):
                    txt = report_text(trades, state)
                    tg("sendMessage", json={"chat_id": TG_CHAT, "text": txt})
                    dc_post("daily-report", embed={"title": "🌾 The farm at the close", "description": txt[:4000], "color": 0xf1c40f})
                    state["last_report"] = str(now.date())
                json.dump(state, open(STATE, "w"))
            if shared["trades"] is not None: write_dashboard(shared["trades"], state)
        except Exception as e:
            print(f"{now:%H:%M} error: {e}", flush=True)
        time.sleep(60 if not market_closed(now) else 300)


if __name__ == "__main__":
    if sys.argv[1:] == ["replay"]:
        m1, m5 = fetch(); trades = all_trades(m1, m5)
        for t in trades:
            pa, q = pnl(t, 200)
            print(f"{t['entry_ts']:%a %m-%d %H:%M} {t['strat']:4s} {'L' if t['side']>0 else 'S'} {t['entry']:.2f} stop {t['stop']:.2f} -> "
                  f"{t['exit']:.2f} {'' if t['closed'] else '(OPEN)'} {t['pts']:+.1f}pts  $200 lane: {q} MNQ ${pa:+,.0f}")
        st = {"start": str(trades[0]["entry_ts"]) if trades else pd.Timestamp.now(tz=TZ).isoformat()}
        print("\n" + report_text(trades, st))
    elif sys.argv[1:] == ["dash"]:
        m1, m5 = fetch(); write_dashboard(all_trades(m1, m5), load_state()); print(open(os.path.join(DASH, "data.json"), encoding="utf-8").read()[:1500])
    elif sys.argv[1:] == ["report"]:
        m1, m5 = fetch(); trades = all_trades(m1, m5); txt = report_text(trades, load_state())
        tg("sendMessage", json={"chat_id": TG_CHAT, "text": txt}); dc_post("daily-report", embed={"title": "🌾 The farm at the close", "description": txt[:4000], "color": 0xf1c40f})
    else:
        loop()
