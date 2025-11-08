import os, json, datetime, urllib.request, urllib.error

DATA_URL = os.getenv("DATA_URL", "").strip()
ZAPIER_HOOK_URL = os.getenv("ZAPIER_HOOK_URL", "").strip()

EMO = {"bullish": "✅ bullish", "bearish": "❗ bearish", "neutral": "⏸️ neutral"}
ASSETS_ORDER = ["BTC", "ETH", "GOLD", "OIL", "SP500", "USD"]  # ترتیب نمایش

def _fmt(val):
    try:
        f = float(val)
    except Exception:
        f = 0.0
    return f"{f:.2f}"

def classify(x):
    try:
        v = float(x)
    except Exception:
        v = 0.0
    if v > 0.05: return "bullish"
    if v < -0.05: return "bearish"
    return "neutral"

def line(label, change):
    arrow = "↗" if change>0 else ("↘" if change<0 else "→")
    return f"- {label}: {_fmt(change)} → {EMO[classify(change)]}"

def fetch_json(url):
    if not url:
        print("ERROR: DATA_URL is empty.")
        return None
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = r.read().decode("utf-8")
            print("DEBUG: downloaded bytes =", len(raw))
            return json.loads(raw)
    except Exception as e:
        print("ERROR: fetch_json failed:", e)
        return None

def extract_changes(data):
    """
    خروجی: dict مثل {"BTC": -0.12, "ETH": 0.34, ...}
    پشتیبانی از چند اسکیمای متداول:
      A) {"BTC": -0.1, "ETH": 0.2, ...}
      B) {"BTC":{"change":-0.1}, "ETH":{"24h":0.2}, ...}
      C) [{"symbol":"BTC","change":-0.1}, {"symbol":"ETH","pct":0.2}, ...]
    کلیدهای محتمل تغییر: change, delta, pct, d1, _24h, 24h, change_24h
    """
    if data is None:
        return {}

    # حالت A: دیکشنری فلت (مقادیر عددی)
    if isinstance(data, dict):
        # اگر مستقیم عددی بود
        flat_numeric = {k: v for k, v in data.items() if isinstance(v, (int, float, str))}
        # اگر داخل آبجکت‌ها بود
        nested = {}
        for k, v in data.items():
            if isinstance(v, dict):
                for key in ("change","delta","pct","d1","_24h","24h","change_24h"):
                    if key in v:
                        nested[k] = v[key]
                        break
        # ادغام، nested اولویت دارد
        merged = {**flat_numeric, **nested}
        # فقط نمادهایی که در لیست ما هست یا شبیهش هستند
        cleaned = {}
        for sym in ASSETS_ORDER:
            if sym in merged:
                cleaned[sym] = merged[sym]
        # اگر اسامی متفاوت هستند (مثلاً XAU=GOLD، WTI=OIL، SPX=SP500، DXY=USD)
        alias = {"XAU":"GOLD","WTI":"OIL","SPX":"SP500","DXY":"USD"}
        for a, std in alias.items():
            if std not in cleaned and a in merged:
                cleaned[std] = merged[a]
        print("DEBUG: extracted (dict) =", cleaned)
        return cleaned

    # حالت C: لیست آبجکت‌ها
    if isinstance(data, list):
        tmp = {}
        for row in data:
            if not isinstance(row, dict): 
                continue
            sym = row.get("symbol") or row.get("asset") or row.get("ticker") or row.get("name")
            if not sym: 
                continue
            val = None
            for key in ("change","delta","pct","d1","_24h","24h","change_24h","value"):
                if key in row:
                    val = row[key]
                    break
            if val is None:
                continue
            sym = sym.upper()
            tmp[sym] = val
        cleaned = {}
        for sym in ASSETS_ORDER:
            if sym in tmp:
                cleaned[sym] = tmp[sym]
        alias = {"XAU":"GOLD","WTI":"OIL","SPX":"SP500","DXY":"USD"}
        for a, std in alias.items():
            if std not in cleaned and a in tmp:
                cleaned[std] = tmp[a]
        print("DEBUG: extracted (list) =", cleaned)
        return cleaned

    print("WARN: unsupported JSON root type:", type(data).__name__)
    return {}

def build_message(changes):
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    parts = [f"📊 Daily Market Sentiment Snapshot ({today}):"]

    any_line = False
    for sym in ASSETS_ORDER:
        if sym in changes:
            try:
                v = float(changes[sym])
            except Exception:
                v = 0.0
            parts.append(line(sym, v))
            any_line = True

    if not any_line:
        parts.append("- No assets found in data source.")

    parts.append("")
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
        with urllib.request.urlopen(req, timeout=20) as r:
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
    data = fetch_json(DATA_URL)
    print("DEBUG: top-level type:", type(data).__name__ if data is not None else "None")
    changes = extract_changes(data)
    msg = build_message(changes)
    print("----- MESSAGE PREVIEW -----\n" + msg + "\n---------------------------")
    code, body = post_to_zapier(msg)
    print(f"Webhook status: {code}")
    print(f"Webhook response: {body}")
