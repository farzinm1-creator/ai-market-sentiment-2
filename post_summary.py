import json
from datetime import datetime

# 1) خواندن فایل JSON از ریپو
with open("data/daily_sentiment.json", "r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    print("Daily Sentiment Snapshot:\nNo data received.")
    raise SystemExit(0)

# 2) تعیین آخرین تاریخ موجود در فایل (به‌جای اصرار روی امروز)
for r in data:
    r["day_dt"] = datetime.fromisoformat(r["day"])

latest_day = max(r["day_dt"] for r in data)
rows = [r for r in data if r["day_dt"].date() == latest_day.date()]

# 3) ساخت متن پست
lines = [f"📊 Daily Market Sentiment Snapshot ({latest_day.date()}):"]
for r in sorted(rows, key=lambda x: x["asset"]):
    s = float(r["avg_sentiment"])
    if s > 0.15:
        emo = "✅ bullish"
    elif s < -0.15:
        emo = "❗ bearish"
    else:
        emo = "⏸️ neutral"
    lines.append(f"- {r['asset']}: {s:.2f} → {emo}")

# 4) لینک‌ها و هشتگ‌ها
lines.append("\n🔗 Demo (BTC only): https://sentiment-demo.onrender.com")
lines.append("🚀 Pro (all assets + alerts): https://sentiment-pro.onrender.com")
lines.append("\n#Crypto #Gold #Oil #Forex #AI #Sentiment #Trading")

# 5) تایم‌استمپ برای جلوگیری از خطای Duplicate
stamp = "⏱ " + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
lines.append("\n" + stamp)

print("\n".join(lines))
