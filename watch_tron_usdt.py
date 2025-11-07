# watch_tron_usdt.py
import os, json, time, requests, uuid
from datetime import datetime, timedelta
from pathlib import Path

# ---------- تنظیمات از طریق متغیر محیطی ----------
APPS_SCRIPT_URL   = os.environ.get("APPS_SCRIPT_URL", "").strip()
APPS_SCRIPT_TOKEN = os.environ.get("APPS_SCRIPT_TOKEN", "").strip()
WALLET_ADDRESS    = os.environ.get("WALLET_ADDRESS", "").strip()

# آدرس قرارداد USDT روی TRON (TRC20). اگر مطمئن نیستی، همین را بگذار.
# در صورت نیاز بعداً عوضش می‌کنیم.
USDT_CONTRACT     = os.environ.get("USDT_CONTRACT", "Tether_USDT_TRON").strip()

# حداقل مبالغ و پلن‌ها
MONTHLY_AMOUNT   = float(os.environ.get("MONTHLY_AMOUNT", "15.0"))
QUARTERLY_AMOUNT = float(os.environ.get("QUARTERLY_AMOUNT", "40.0"))

# آستانه‌ی تلورانس برای تشخیص دقیق مبلغ (رُند شدن‌ها)
AMOUNT_EPS = float(os.environ.get("AMOUNT_EPS", "0.05"))

STATE_PATH = Path(".state/processed_txids.json")
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_state():
    if STATE_PATH.exists():
        try:
            return set(json.loads(STATE_PATH.read_text()))
        except:
            return set()
    return set()

def save_state(txids):
    STATE_PATH.write_text(json.dumps(sorted(list(txids))))

def plan_from_amount(amount):
    if abs(amount - MONTHLY_AMOUNT) <= AMOUNT_EPS:
        return ("Monthly", 30)
    if abs(amount - QUARTERLY_AMOUNT) <= AMOUNT_EPS:
        return ("Quarterly", 90)
    return (None, 0)

def post_to_apps_script(email, license_key, plan, expires_at, txid, amount):
    payload = {
        "token": APPS_SCRIPT_TOKEN,
        "email": email,
        "license_key": license_key,
        "plan": plan,
        "expires_at": expires_at,
        "txid": txid,
        "amount": str(amount),
        "asset": "USDT",
        "network": "TRON",
        "status": "active",
        "note": "autodetected_tx"
    }
    r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def gen_license():
    stamp = datetime.utcnow().strftime("%Y%m%d")
    return f"PRO-{stamp}-{uuid.uuid4().hex[:6].upper()}"

def fetch_trc20_transfers_to_me():
    """
    سعی می‌کنیم از دو اندپوینت عمومی استفاده کنیم (هرکدام در دسترس بود).
    خروجی یک لیست از {txid, from, to, contract, amount, tokenSymbol, timestamp}
    """
    candidates = []
    # قالب 1: api.tronscan.org
    try:
        url1 = f"https://apilist.tronscan.org/api/token_trc20/transfers?limit=50&toAddress={WALLET_ADDRESS}"
        j = requests.get(url1, timeout=20).json()
        for it in j.get("token_transfers", []):
            candidates.append({
                "txid": it.get("transaction_id") or it.get("hash"),
                "to": it.get("to_address"),
                "from": it.get("from_address"),
                "contract": it.get("contract_address"),
                "token_symbol": it.get("token_info", {}).get("symbol") or it.get("symbol"),
                "amount": float(it.get("quant", 0)) / (10 ** int(it.get("token_info", {}).get("decimals", 6) or 6)),
                "ts": int(it.get("block_ts") or 0) // 1000
            })
    except Exception as e:
        print("tronscan.org fetch error:", e)

    # قالب 2: tronscanapi.com
    if not candidates:
        try:
            url2 = f"https://apilist.tronscanapi.com/api/token_trc20/transfers?limit=50&toAddress={WALLET_ADDRESS}"
            j = requests.get(url2, timeout=20).json()
            for it in j.get("token_transfers", []):
                candidates.append({
                    "txid": it.get("transaction_id") or it.get("hash"),
                    "to": it.get("to_address"),
                    "from": it.get("from_address"),
                    "contract": it.get("contract_address"),
                    "token_symbol": it.get("token_info", {}).get("symbol") or it.get("symbol"),
                    "amount": float(it.get("quant", 0)) / (10 ** int(it.get("token_info", {}).get("decimals", 6) or 6)),
                    "ts": int(it.get("block_ts") or 0) // 1000
                })
        except Exception as e:
            print("tronscanapi.com fetch error:", e)

    # فقط ورودی‌های معنادار
    out = []
    for c in candidates:
        if not c["txid"] or not c["to"]:
            continue
        out.append(c)
    return out

def main():
    if not (APPS_SCRIPT_URL and APPS_SCRIPT_TOKEN and WALLET_ADDRESS):
        raise SystemExit("Missing APPS_SCRIPT_URL / APPS_SCRIPT_TOKEN / WALLET_ADDRESS env vars.")

    seen = load_state()
    txs = fetch_trc20_transfers_to_me()
    if not txs:
        print("No transfers found (or API offline).")
        return

    # جدیدترین‌ها جلو
    txs.sort(key=lambda x: x["ts"], reverse=True)

    processed_now = 0

    for tx in txs:
        txid = tx["txid"]
        if txid in seen:
            continue
        # فقط USDT را بگیر (سمبل یا کانترکت)
        sym = (tx.get("token_symbol") or "").upper()
        contract = (tx.get("contract") or "").strip()

        # اگر کاربر قرارداد دقیق USDT را بده، بر آن تطبیق بده؛
        # وگرنه بر اساس نماد USDT جلو می‌رویم.
        if USDT_CONTRACT != "Tether_USDT_TRON":
            if contract.lower() != USDT_CONTRACT.lower():
                continue
        else:
            if sym != "USDT":
                continue

        amount = float(tx["amount"])
        plan, days = plan_from_amount(amount)
        if not plan:
            continue

        # تعیین ایمیل مشتری: در نسخه واقعی باید از فرم کاربر بیاد؛
        # برای MVP، می‌تونیم از txid ایمیل ساختگی بسازیم یا بعداً وصلش کنیم.
        # اینجا ایمیل-placeholder می‌گذاریم تا Sheet/Email کامل شود:
        customer_email = f"client+{txid[:8]}@example.com"
        license_key = gen_license()
        expires_at = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")

        print(f"Posting TX {txid} amount={amount} plan={plan} → Apps Script …")
        try:
            resp = post_to_apps_script(
                email=customer_email,
                license_key=license_key,
                plan=plan,
                expires_at=expires_at,
                txid=txid,
                amount=amount
            )
            print("AppsScript response:", resp)
            seen.add(txid)
            processed_now += 1
        except Exception as e:
            print("POST error:", e)

    if processed_now:
        save_state(seen)
        print(f"Processed {processed_now} tx(s).")
    else:
        print("No new payable txs.")

if __name__ == "__main__":
    main()
