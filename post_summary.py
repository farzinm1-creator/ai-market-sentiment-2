import json
from datetime import date

# خواندن داده‌های احساسات ذخیره‌شده
with open("data/daily_sentiment.json", "r", encoding="utf-8") as f:
    data = json.load(f)

today = str(date.today())
rows = [row for row in data if row["day"] == today]

# اگر داده‌ای وجود نداشت
if not rows:
    print("Daily Sentiment Snapshot:\nNo data received.")
    exit()

# ساخت متن پست
lines = [f"📊 Daily Market Sentiment Snapshot ({today}):"]

for row in rows:
    sentiment = row["avg_sentiment"]

    # تعیین وضعیت بازار با ایموجی
    if sentiment > 0.15:
        emoji = "✅ bullish"
    elif sentiment < -0.15:
        emoji = "❗ bearish"
    else:
        emoji = "⏸️ neutral"

    lines.append(f"- {row['asset']}: {sentiment:.2f} → {emoji}")

# ✅ اضافه کردن لینک نسخه دمو و نسخه پرو
lines.append("\n🔗 نسخه دمو (فقط بیت‌کوین): https://sentiment-demo.onrender.com")
lines.append("🚀 نسخه حرفه‌ای (تمام دارایی‌ها + هشدار لحظه‌ای): https://sentiment-pro.onrender.com")

# ✅ هشتگ‌های حرفه‌ای لینکدین
lines.append("\n#Crypto #Forex #Gold #Oil #Trading #AI #SentimentAnalysis #MarketInsights")

# نهایی‌سازی و ارسال خروجی
text = "\n".join(lines)
print(text)
