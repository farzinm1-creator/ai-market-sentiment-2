import os, json, requests
from pathlib import Path
from datetime import datetime
import pandas as pd

DATA = Path("data/daily_sentiment.json")
HOOK = os.getenv("ZAPIER_HOOK_URL")

def today_summary():
    if not DATA.exists():
        return "Daily Sentiment Snapshot:\nNo data yet."
    df = pd.read_json(DATA)
    if df.empty:
        return "Daily Sentiment Snapshot:\nNo data yet."
    df["day"] = pd.to_datetime(df["day"])
    last_day = df["day"].max()
    d = df[df["day"] == last_day]
    lines = [f"Daily Sentiment Snapshot ({last_day.date()}):"]
    for _, r in d.iterrows():
        s = float(r["avg_sentiment"])
        label = "positive ✅" if s>0.1 else ("negative ❗" if s<-0.1 else "neutral ⏸️")
        lines.append(f"- {r['asset']}: {s:.2f} ({label})")
    lines.append("\nDemo: BTC only | Pro: full assets & alerts.")
    return "\n".join(lines)

def main():
    msg = today_summary()
    print(msg)
    if HOOK:
        try:
            requests.post(HOOK, json={"text": msg}, timeout=12)
            print("Posted to webhook.")
        except Exception as e:
            print("Webhook error:", e)

if __name__ == "__main__":
    main()
