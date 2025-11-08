import os, json, datetime, urllib.request, urllib.error

DATA_URL = os.getenv("DATA_URL", "").strip()
ZAPIER_HOOK_URL = os.getenv("ZAPIER_HOOK_URL", "").strip()

EMO = {
    "bullish": "✅ bullish",
    "bearish": "❗ bearish",
    "neutral": "⏸️ neutral",
}

def _fmt(val):
    try:
        f = float(val)
    except Exception:
        return "0.00"
    s = f"{f:.2f}"
    return s

def load_data():
    # انتظار: JSON با کلیدهای BTC/ETH/GOLD/OIL/SP500/USD و مقدار تغییر روزانه
    if not DATA_URL:
        return {}
    try:
        with urllib.request.urlopen(DATA_URL, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return {}

def classify(x):
    try:
        v = float(x)
    except Exception:
        v = 0.0
    if v > 0.05:   # آستانه‌های ساده
        return "bullish"
    if v < -0.05:
        return "bearish"
    return "neutral"

def line(label, change):
    arrow = "↗" if change>0 else ("↘" if change<0 else "→")
    return f"- {label}: {_fmt(change)} → {EMO[classify(change)]}"

def build_message(d):
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    parts = [f"📊 Daily Market Sentiment Snapshot ({today}):"]
    # ترتیب: BTC, ETH, GOLD, OIL, SP500, USD (اگر موجود بود)
    for k,label in [("BTC","BTC"),("ETH","ETH"),("GOLD","GOLD"),
                    ("OIL","OIL"),("SP500","SP500"),("USD","USD")]:
        if k in d:
            try:
                change = float(d[k])
            except Exception:
                change = 0.0
            parts.append(line(label, change))

    parts.append("")  # خط خالی
    parts.append("#Crypto #Gold #Oil #Forex #AI #Sentiment #Trading")
    parts.append("We are coming soon")
    return "\n".join(parts)

def post_to_zapier(text):
    if not ZAPIER_HOOK_URL:
        print("WARN: ZAPIER_HOOK_URL is empty; skipping webhook.")
        return 0, "skipped"
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        ZAPIER_HOOK_URL,
        data=payload,
        headers={"Content-Type":"application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8")
            return r.getcode(), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"POST to Zapier failed: {e} | {body}")
        return e.code, body
    except Exception as e:
        print(f"POST to Zapier failed: {e}")
        return -1, str(e)

if __name__ == "__main__":
    data = load_data()
    msg = build_message(data)
    print(msg)
    code, body = post_to_zapier(msg)
    print(f"Webhook status: {code}")
    print(f"Webhook response: {body}")
