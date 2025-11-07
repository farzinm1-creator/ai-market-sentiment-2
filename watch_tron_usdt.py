# watch_tron_usdt.py
import os, json, requests, uuid
from datetime import datetime, timedelta
from pathlib import Path

APPS_SCRIPT_URL   = os.environ.get("APPS_SCRIPT_URL","").strip()
APPS_SCRIPT_TOKEN = os.environ.get("APPS_SCRIPT_TOKEN","").strip()
WALLET_ADDRESS    = os.environ.get("WALLET_ADDRESS","").strip()

# اگر قرارداد دقیق USDT را می‌دانی بگذار؛ وگرنه با نماد USDT فیلتر می‌کنیم
USDT_CONTRACT     = os.environ.get("USDT_CONTRACT","Tether_USDT_TRON").strip()

MONTHLY_AMOUNT   = float(os.environ.get("MONTHLY_AMOUNT","15.0"))
QUARTERLY_AMOUNT = float(os.environ.get("QUARTERLY_AMOUNT","40.0"))
AMOUNT_EPS       = float(os.environ.get("AMOUNT_EPS","0.05"))

STATE_PATH = Path(".state/processed_txids.json")
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_state():
    if STATE_PATH.exists():
        try:
            return set(json.loads(STATE_PATH.read_text()))
        except:
            return set()
    return set()

def save_state(s):
    STATE_PATH.write_text(json.dumps(sorted(list(s))))

def plan_from_amount(amount):
    if abs(amount - MONTHLY_AMOUNT) <= AMOUNT_EPS:
        return ("Monthly", 30)
    if abs(amount - QUARTERLY_AMOUNT) <= AMOUNT_EPS:
        return ("Quarterly", 90)
    return (None, 0)

def post_issue_license(email, license_key, plan, expires_at, txid, amount):
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

def apps_get_pending():
    url = f"{APPS_SCRIPT_URL}?pending=1&secret={APPS_SCRIPT_TOKEN}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    j = r.json()
    if not j.get("ok"):
        return {}
    pend = {}
    for row in j.get("rows", []):
        tax = str(row.get("tax_id","")).strip()
        if not tax:
            continue
        pend[tax.upper()] = {
            "email": str(row.get("email","")).strip(),
            "plan":  str(row.get("plan","")).strip(),
            "amount": float(row.get("amount") or 0.0),
        }
    return pend

def apps_complete_pending(tax_id, txid):
    payload = { "token": APPS_SCRIPT_TOKEN, "action": "complete", "tax_id": tax_id, "txid": txid }
    r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def gen_license():
    stamp = datetime.utcnow().strftime("%Y%m%d")
    return f"PRO-{stamp}-{uuid.uuid4().hex[:6].upper()}"

def fetch_trc20_transfers_to_me():
    out = []
    # منبع 1
    try:
        url1 = f"https://apilist.tronscan.org/api/token_trc20/transfers?limit=50&toAddress={WALLET_ADDRESS}"
        j = requests.get(url1, timeout=20).json()
        for it in j.get("token_transfers", []):
            out.append({
                "txid": it.get("transaction_id") or it.get("hash"),
                "to": it.get("to_address"),
                "from": it.get("from_address"),
                "contract": it.get("contract_address"),
                "token_symbol": (it.get("token_info", {}) or {}).get("symbol") or it.get("symbol"),
                "decimals": int((it.get("token_info", {}) or {}).get("decimals", 6) or 6),
                "quant": it.get("quant", 0),
                "ts": int(it.get("block_ts") or 0) // 1000,
                "data": it.get("data") or it.get("memo") or ""
            })
    except Exception as e:
        print("tronscan.org fetch error:", e)

    # منبع 2 (پشتیبان)
    if not out:
        try:
            url2 = f"https://apilist.tronscanapi.com/api/token_trc20/transfers?limit=50&toAddress={WALLET_ADDRESS}"
            j = requests.get(url2, timeout=20).json()
            for it in j.get("token_transfers", []):
                out.append({
                    "txid": it.get("transaction_id") or it.get("hash"),
                    "to": it.get("to_address"),
                    "from": it.get("from_address"),
                    "contract": it.get("contract_address"),
                    "token_symbol": (it.get("token_info", {}) or {}).get("symbol") or it.get("symbol"),
                    "decimals": int((it.get("token_info", {}) or {}).get("decimals", 6) or 6),
                    "quant": it.get("quant", 0),
                    "ts": int(it.get("block_ts") or 0) // 1000,
                    "data": it.get("data") or it.get("memo") or ""
                })
        except Exception as e:
            print("tronscanapi.com fetch error:", e)

    # نرمال‌سازی amount
    norm = []
    for t in out:
        if not t["txid"] or not t["to"]:
            continue
        dec = int(t.get("decimals", 6) or 6)
        q = float(t.get("quant", 0) or 0)
        amt = q / (10 ** dec) if dec >= 0 else q
        norm.append({
            "txid": t["txid"],
            "to": t["to"],
            "from": t["from"],
            "contract": t["contract"] or "",
            "token_symbol": (t["token_symbol"] or "").upper(),
            "amount": amt,
            "ts": t["ts"],
            "data": (t.get("data") or "").strip()
        })
    return norm

def main():
    if not (APPS_SCRIPT_URL and APPS_SCRIPT_TOKEN and WALLET_ADDRESS):
        raise SystemExit("Missing APPS_SCRIPT_URL / APPS_SCRIPT_TOKEN / WALLET_ADDRESS env vars.")

    pending = apps_get_pending()  # { TAXID_UPPER: {email, plan, amount}, ... }
    seen = load_state()
    txs = fetch_trc20_transfers_to_me()
    if not txs:
        print("No transfers found (or API offline).")
        return

    txs.sort(key=lambda x: x["ts"], reverse=True)
    processed = 0

    for tx in txs:
        txid = tx["txid"]
        if txid in seen:
            continue

        sym = (tx["token_symbol"] or "").upper()
        contract = (tx.get("contract") or "").strip()

        # فیلتر USDT
        if USDT_CONTRACT != "Tether_USDT_TRON":
            if contract.lower() != USDT_CONTRACT.lower():
                continue
        else:
            if sym != "USDT":
                continue

        amount = float(tx["amount"])
        memo = (tx.get("data") or "").strip()
        if not memo:
            continue  # بدون memo نمی‌توان tax_id را پیدا کرد

        tax_id = memo  # هر فرمتی که درگاه می‌سازد، همان را می‌پذیریم
        key = tax_id.upper()
        if key not in pending:
            # سفارشی با این tax_id ثبت نشده
            continue

        order = pending[key]  # email, plan, amount(اختیاری)
        exp_amount = float(order.get("amount") or 0.0)

        # پلن و روزها
        plan, days = plan_from_amount(amount)

        if exp_amount > 0.0:
            # اگر مبلغ در pending مشخص شده، باید دقیقاً به آن بخورد
            if abs(amount - exp_amount) > AMOUNT_EPS:
                print(f"⚠️ TX {txid}: amount={amount} != expected={exp_amount} for tax_id={tax_id}")
                continue
            # پلن از مقدار pending
            if abs(exp_amount - MONTHLY_AMOUNT) <= AMOUNT_EPS:
                plan, days = "Monthly", 30
            elif abs(exp_amount - QUARTERLY_AMOUNT) <= AMOUNT_EPS:
                plan, days = "Quarterly", 90
            else:
                print(f"⚠️ TX {txid}: unknown expected amount {exp_amount}")
                continue
        else:
            # اگر pending مقدار ندارد، از مبلغ واقعی استنباط کن
            if not plan:
                continue

        email = order.get("email") or f"user+{tax_id.lower()}@example.com"
        license_key = gen_license()
        expires_at = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")

        print(f"✅ Match tax_id={tax_id} plan={plan} amount={amount} → issuing license")
        try:
            jr = post_issue_license(
                email=email,
                license_key=license_key,
                plan=plan,
                expires_at=expires_at,
                txid=txid,
                amount=amount
            )
            print("AppsScript response:", jr)
            # complete pending
            try:
                done = apps_complete_pending(tax_id, txid)
                print("Completed pending:", done)
            except Exception as e:
                print("completePending error:", e)
            seen.add(txid)
            processed += 1
        except Exception as e:
            print("POST error:", e)

    if processed:
        save_state(seen)
        print(f"Processed {processed} tx(s).")
    else:
        print("No new payable txs.")

if __name__ == "__main__":
    main()
