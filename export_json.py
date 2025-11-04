import sqlite3, json
from pathlib import Path
import pandas as pd

DB = Path("data/sentiment.db")
OUT = Path("data/daily_sentiment.json")

def main():
    if not DB.exists():
        OUT.write_text("[]", encoding="utf-8")
        print("No DB yet. Wrote empty JSON.")
        return
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT day, asset, avg_sentiment, count_used FROM sentiments_daily ORDER BY day, asset", conn)
    conn.close()
    if df.empty:
        OUT.write_text("[]", encoding="utf-8")
        print("No data in DB. Wrote empty JSON.")
        return
    df["day"] = pd.to_datetime(df["day"]).dt.strftime("%Y-%m-%d")
    OUT.write_text(df.to_json(orient="records", force_ascii=False), encoding="utf-8")
    print("Wrote:", OUT)

if __name__ == "__main__":
    main()
