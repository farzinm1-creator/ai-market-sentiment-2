# post_summary.py
# - می‌خواند: data/daily_sentiment.json یا متغیر DATA_URL (اختیاری)
# - متن پست LinkedIn را می‌سازد
# - در summary.txt ذخیره می‌کند (برای لاگ)
# - در صورت وجود ZAPIER_HOOK_URL معتبر، با requests به Zapier POST می‌کند

import os
import sys
import json
from datetime import datetime


def load_data():
    """Load JSON either from DATA_URL (if set) or local file."""
    data_url = (os.getenv("DATA_URL") or "").strip().strip('"').strip("'")
    try:
        if data_url:
            import urllib.request
            with urllib.request.urlopen(data_url, timeout=20) as r:
                return json.load(r)
        # fallback: local file inside repo
        with open("data/daily_sentiment.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("ERROR loading data:", e, file=sys.stderr)
        return []


def build_text(data):
    """Build final post text using the latest available day in the dataset."""
    if not data:
        return "Daily Sentiment Snapshot:\nNo data received."

    # parse dates and find latest day
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
    """POST to Zapier webhook if ZAPIER_HOOK_URL is valid."""
    hook = (os.getenv("ZAPIER_HOOK_URL") or "").strip().strip('"').strip("'")
    if not hook or not hook.startswith("http"):
        print("ZAPIER_HOOK_URL invalid or missing → skipping POST to Zapier.")
        return

    try:
        import requests
    except Exception:
        # minimal fallback if requests not installed (should be installed by workflow)
        print("requests not found; installing…")
        os.system(f"{sys.executable} -m pip install --quiet requests")
        import requests

    try:
        resp = requests.post(hook, json={"text": text}, timeout=20)
        print("Webhook status:", resp.status_code)
        # avoid dumping huge body
        print("Webhook response:", (resp.text or "")[:300])
        resp.raise_for_status()
    except Exception as e:
        print("POST to Zapier failed:", e, file=sys.stderr)


def main():
    data = load_data()
    text = build_text(data)

    # print for GitHub logs and save to file
    print(text)
    try:
        with open("summary.txt", "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print("WARN: could not write summary.txt:", e, file=sys.stderr)

    # send to Zapier (if URL set)
    post_to_zapier(text)


if __name__ == "__main__":
    main()
