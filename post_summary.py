# post_summary.py
import os, json, urllib.request, datetime
import ssl
from urllib.error import URLError, HTTPError

# ---------- تنظیمات ----------
ASSET_ORDER = ["BTC", "ETH", "GOLD", "OIL", "SP500", "USD"]
NEUTRAL_THRESH = 0.05  # آستانه‌ی خنثی

DATA_URL = os.environ.get("DATA_URL", "").strip()
ZAPIER_HOOK_URL = os.environ.get("ZAPIER_HOOK_URL", "").strip()

def fetch_json(url: str):
    if not url:
        raise ValueError("DATA_URL is empty")
    # برای برخی هاست‌ها که TLS هشدار می‌دهند
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=20) as resp:
            raw = resp.read().decode("utf-8", "ignore")
            print(f"DEBUG: downloaded bytes = {len(raw)}")
            return json.loads(raw)
    except (HTTPError, URLError) as e:
        raise RuntimeError(f"Failed to fetch DATA_URL: {e}")

def normalize_payload(payload):
    """
    خروجی را به شکل { 'BTC': value, ... }, و همچنین تاریخ روز برمی‌گرداند.
    payload می‌تواند dict یا list باشد.
    """
    # حالت آرایه‌ای (مثل داده‌ای که فرستادی)
    if isinstance(payload, list):
        # آخرین روز
        all_days = [row.get("day") for row in payload if isinstance(row, dict) and row.get("day")]
        if not all_days:
            raise ValueError("No 'day' found in array payload")
        latest_day = max(all_days)  # فرمت YYYY-MM-DD
        today_rows = [r for r in payload if r.get("day") == latest_day]
        out = {}
        for r in today_rows:
            a = str(r.get("asset", "")).upper()
            val = r.get("avg_sentiment")
            # فقط اگر مقدار عددی داریم
            try:
                if a and val is not None:
                    out[a] = float(val)
            except Exception:
                pass
        return latest_day, out

    # حالت دیکشنریِ ساده: { "BTC": 0.12, ... }
    if isinstance(payload, dict):
        # اگر کلید day نبود، تاریخ امروز UTC را می‌زنیم
        latest_day = payload.get("day")
        if not latest_day:
            latest_day = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        # اگر زیرکلید data وجود داشت
        if "data" in payload and isinstance(payload["data"], dict):
            return latest_day, {k.upper(): float(v) for k, v in payload["data"].items()}
        # در غیر این صورت فرض می‌کنیم خود دیکشنریِ بالا به پایین است
        core = {k.upper(): v for k, v in payload.items() if k.upper() in ASSET_ORDER or k.upper()=="DAY"}
        # day را برداشته و بقیه را نگه می‌داریم
        core.pop("DAY", None)
        core = {k: float(v) for k, v in core.items()}
        return latest_day, core

    raise ValueError("Unsupported payload type")

def sentiment_flag(x: float):
    if x >= NEUTRAL_THRESH:
        return "✅ bullish"
    if x <= -NEUTRAL_THRESH:
        return "❗ bearish"
    return "⏸️ neutral"

def build_message(day_str: str, values: dict):
    lines = []
    lines.append(f"📊 Daily Market Sentiment Snapshot ({day_str}):")
    for a in ASSET_ORDER:
        if a in values:
            flag = sentiment_flag(values[a])
            # مقدار به صورت اعشاری کوتاه نمایش داده می‌شود
            val = f"{values[a]:.2f}"
            lines.append(f"- {a}: {val} → {flag}")
    lines.append("")
    lines.append("#Crypto #Gold #Oil #Forex #AI #Sentiment #Trading")
    lines.append("")
    lines.append("We are coming soon")
    return "\n".join(lines)

def post_to_zapier(text: str):
    if not ZAPIER_HOOK_URL:
        print("INFO: ZAPIER_HOOK_URL is empty; printing message only.")
        print(text)
        return
    try:
        req = urllib.request.Request(
            ZAPIER_HOOK_URL,
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "ignore")
            print("Webhook status:", resp.status)
            print("Webhook response:", body)
    except Exception as e:
        print("POST to Zapier failed:", e)

def main():
    try:
        payload = fetch_json(DATA_URL)
        day_str, values = normalize_payload(payload)
        msg = build_message(day_str, values)
        print("\n===== POST TEXT =====\n" + msg + "\n=====================\n")
        post_to_zapier(msg)
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    main()
