# MGW Prop Farm Telegram bot: listens for Take / Skip taps on alerts.
# PAPER MODE: a tap only marks the alert and logs it to tg_decisions.csv (no broker connected yet).
#   python telegram_bot.py            -> runs forever (long polling)
#   from telegram_bot import send_alert; send_alert("text", trade_id)   -> sends an alert with buttons
import os, csv, time, datetime as dt, requests

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = open(os.path.join(HERE, "telegram_token.txt")).read().strip()
CHAT = open(os.path.join(HERE, "telegram_chat_id.txt")).read().strip()
API = f"https://api.telegram.org/bot{TOKEN}"
LOG = os.path.join(HERE, "tg_decisions.csv")


def send(text, buttons=None):
    body = {"chat_id": CHAT, "text": text}
    if buttons: body["reply_markup"] = {"inline_keyboard": buttons}
    return requests.post(f"{API}/sendMessage", json=body, timeout=20).json()


def send_alert(text, trade_id="test"):
    return send(text, [[{"text": "✅ Take", "callback_data": f"take|{trade_id}"},
                        {"text": "❌ Skip", "callback_data": f"skip|{trade_id}"}]])


def log(row):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["time", "decision", "trade_id", "alert_text"])
        w.writerow(row)


def handle_tap(cb):
    action, _, trade_id = cb["data"].partition("|")
    msg = cb["message"]; now = dt.datetime.now().strftime("%H:%M:%S")
    label = "✅ TAKEN (paper, no real order yet)" if action == "take" else "❌ SKIPPED"
    requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": label}, timeout=20)
    requests.post(f"{API}/editMessageText", json={"chat_id": msg["chat"]["id"], "message_id": msg["message_id"],
                                                  "text": f"{msg.get('text','')}\n\n{label} at {now}"}, timeout=20)
    log([dt.datetime.now().isoformat(timespec="seconds"), action, trade_id or "test", msg.get("text", "").replace("\n", " | ")])


def handle_text(m):
    t = (m.get("text") or "").strip().lower()
    if t in ("/start", "/status", "status"):
        send("🌾 MGW Prop Farm bot is running (PAPER mode). Alerts come here; tap Take or Skip.")
    elif t in ("/test", "test"):
        send_alert("TEST ALERT (not a real trade)\nMNQ • ORB 5-min • LONG\nEntry 25,512.25 | Stop 25,472.25 | Hold to close\nRisk: $200 (1R)")


def run():
    offset = None
    print("Telegram bot listening...", flush=True)
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", params={"timeout": 50, "offset": offset}, timeout=60).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                if "callback_query" in u: handle_tap(u["callback_query"])
                elif "message" in u and str(u["message"]["chat"]["id"]) == CHAT: handle_text(u["message"])
        except Exception as e:
            print("error:", e, flush=True); time.sleep(5)


if __name__ == "__main__":
    run()
