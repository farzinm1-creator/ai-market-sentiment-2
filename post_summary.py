# post_summary.py
# Builds a daily LinkedIn post from a JSON dataset and sends it to Zapier.
# - DATA_URL: raw JSON URL (or any HTTP URL returning JSON array of rows: {day, asset, avg_sentiment,...})
# - ZAPIER_HOOK_URL: Zapier Catch Hook URL
#
# Output format has no product links; includes hashtags and "We are coming soon".

import os
import json
import ssl
import datetime
import urllib.request
from urllib.error import URLError, HTTPError

# -------- Config --------
ASSET_ORDER = ["BTC", "ETH", "GOLD", "OIL", "SP500", "USD"]  # add "EURUSD" if you want
NEUTRAL_THRESH = 0.05

DATA_URL = os.environ.get("DATA_URL", "").strip()
ZAPIER_HOOK_URL = os.environ.get("ZAPIER_HOOK_URL", "").strip()

# -------- Helpers --------
def fetch_json(url: str):
    if not url:
        raise ValueError("DATA_URL is empty")
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, context=ctx, timeout=20) as resp:
        raw = resp.read().decode("utf-8", "ignore")
        print(f"DEBUG: downloaded bytes = {len(raw)}")
        return json.loads(raw)

def pick_latest_day(rows):
    """rows: list of dicts having 'day' key -> returns latest day string (YYYY-MM-DD)"""
    days = [r.get("day") for r in rows if isinstance(r, dict) and r.get("day")]
    if not days:
        raise ValueError("No 'day' found in payload")
    return max(days)  # assumes ISO date strings

def values_for_day(rows, day_str):
    """
    From all rows of the latest day, build dict {ASSET: value}.
    Uses 'avg_sentiment' as the numeric value.
    """
    out = {}
    for r in rows:
        if r.get("day") != day_str:
            continue
        a = str(r.get("asset", "")).upper()
        if not a:
            continue
        try:
            val = float(r.get("avg_sentiment"))
        except Exception:
            continue
        out[a] = val
    return out

def classify(v: float) -> str:
    if v >= NEUTRAL_THRESH:
        return "✅ bullish"
    if v <= -NEUTRAL_THRESH:
        return "❗ bearish"
    return "⏸️ neutral"

def build_message(day_str: str, vals: dict) -> str:
    lines = [f"📊 Daily Market Sentiment Snapshot ({day_str}):"]
    any_line = False
    for a in ASSET_ORDER:
        if a in vals:
            v = float(vals[a])
            lines.append(f"- {a}: {v:.2f} → {classify(v)}")
            any_line = True
    if not any_line:
        lines.append("- No assets found in data source.")
    lines.append("")
    lines.append("#Crypto #Gold #Oil #Forex #AI #Sentiment #Trading")
    lines.append("We are coming soon")
    return "\n".join(lines)

def post_to_zapier(text: str):
    if not ZAPIER_HOOK_URL:
        print("WARN: ZAPIER_HOOK_URL is empty; skipping webhook.")
        return 0, "skipped"
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        ZAPIER_HOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", "ignore")
            print("Webhook status:", r.status)
            print("Webhook response:", body)
            return r.status, body
    except HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        print(f"POST to Zapier failed: {e} | {body}")
        return e.code, body
    except URLError as e:
        print(f"POST to Zapier failed: {e}")
        return -1, str(e)

# -------- Main --------
if __name__ == "__main__":
    try:
        payload = fetch_json(DATA_URL)
        if isinstance(payload, list):
            latest = pick_latest_day(payload)
            vals = values_for_day(payload, latest)
            msg = build_message(latest, vals)
        elif isinstance(payload, dict):
            # fallback: if dict form is ever used {BTC:0.1, ...}
            day_str = payload.get("day") or datetime.datetime.utcnow().strftime("%Y-%m-%d")
            vals = {k.upper(): float(v) for k, v in payload.items() if k.upper() in ASSET_ORDER}
            msg = build_message(day_str, vals)
        else:
            raise ValueError(f"Unsupported payload type: {type(payload).__name__}")

        print("\n===== MESSAGE PREVIEW =====\n" + msg + "\n===========================\n")
        post_to_zapier(msg)

    except Exception as e:
        print("ERROR:", e)
        # Let the job continue (so the workflow doesn't fail the entire pipeline)
        # Remove the '|| true' in workflow if you prefer failures to be visible.
