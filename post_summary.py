# post_summary.py
# - می‌خواند: data/daily_sentiment.json یا DATA_URL (اختیاری)
# - متن پست را می‌سازد
# - در summary.txt چاپ می‌کند (برای لاگ)
# - اگر ZAPIER_HOOK_URL ست باشد → مستقیم به Zapier POST می‌کند

import os, json, sys
from datetime import datetime

def load_data():
    data_url = os.getenv("DATA_URL", "").strip()
    if data_url:
        # خواندن مستقیم از GitHub Raw (یا هر URL JSON)
        import urllib.request
        with urllib.request.urlopen(data_url, timeout=20) as r:
            return json.load(r)
    # حالت فایل محلی
    with open("data/daily_sentiment.json", "r", encoding="utf-8") as f:
        return json.load(f)

def build_text(data):
    if not data:
        return "Daily Sentiment Snapshot:\nNo data received."
    for r in data:
        r["__dt"] = datetime.fromisoformat(r["day"])
    latest = max(r["__dt"] for r in data)
    rows = [r for r in data if r["__dt"].date() == latest.date()]

    lines = [f"📊 Daily Market Sentiment Snapshot ({latest.date()}):"]
    for r in sorted(rows, key=lambda x: x["asset"]):
        s = float(r["avg_sentiment"])
        emo = "✅ bullish" if s > 0.15 else ("❗ bearish" if s < -0.15 else "⏸️ neutral")
        lines.append(f"- {r['asset']}: {s:.2f} → {emo}")

    lines += [
        "",
        "🔗 Demo (BTC only): https://sentiment-demo.onrender.com",
        "🚀 Pro (all assets + alerts): https://sentiment-pro.onrender.com",
        "",
        "#Crypto #Gold #Oil #Forex #AI #Sentiment #Trading",
        "",
        "⏱ " + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    ]
    return "\n".join(lines)

def post_to_zapier(text):
    hook = os.getenv("ZAPIER_HOOK_URL", "").strip()
    if not hook:
        print("ZAPIER_HOOK_URL not set → skipping POST to Zapier.")
        return
    try:
        import requests
        resp = requests.post(hook, json={"text": text}, timeout=15)
        print("Webhook status:", resp.status_code)
        print("Webhook response:", resp.text[:500])
        resp.raise_for_status()
    except Exception as e:
        print("POST to Zapier failed:", e, file=sys.stderr)

def main():
    data = load_data()
    text = build_text(data)
    # برای لاگ گیت‌هاب:
    print(text)
    with open("summary.txt", "w", encoding="utf-8") as f:
        f.write(text)
    # ارسال به وبهوک
    post_to_zapier(text)

if __name__ == "__main__":
    main()
