# app/app_pending.py
import os, requests, streamlit as st

APPS_SCRIPT_URL   = os.environ.get("APPS_SCRIPT_URL", "")
APPS_SCRIPT_TOKEN = os.environ.get("APPS_SCRIPT_TOKEN", "")

st.set_page_config(page_title="Buy PRO • Market Sentiment", layout="centered")
st.title("Market Sentiment PRO — Buy / Pending Order")

st.info("ایمیل، پلن و Tax ID (کدی که درگاه پرداخت تولید می‌کند) را وارد کنید. \
پس از ساخت سفارش معلق، درگاه را پرداخت کنید و **همان Tax ID** را در MEMO تراکنش بنویسید.")

email = st.text_input("Email", placeholder="client@example.com")
plan = st.selectbox("Plan", ["Monthly", "Quarterly"])
amount = 15.0 if plan == "Monthly" else 40.0
tax_id = st.text_input("Tax ID (از درگاه)", placeholder="کدی که درگاه تولید می‌کند")
note = st.text_input("Note (اختیاری)", value="linkedin-campaign-1")

col1, col2 = st.columns(2)
with col1:
    st.metric("Amount (USDT-TRC20)", f"{amount:.2f}")
with col2:
    st.caption("کیف پول مقصد: آدرس TRON شما (USDT-TRC20)")

st.divider()

if st.button("Create Pending Order"):
    if not (APPS_SCRIPT_URL and APPS_SCRIPT_TOKEN):
        st.error("APPS_SCRIPT_URL / APPS_SCRIPT_TOKEN در سرور تنظیم نشده.")
    elif not (email and tax_id):
        st.error("ایمیل و Tax ID لازم است.")
    else:
        payload = {
            "token": APPS_SCRIPT_TOKEN,
            "action": "add_pending",
            "tax_id": tax_id,
            "email": email,
            "plan": plan,
            "amount": str(amount),
            "note": note
        }
        try:
            r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=20)
            r.raise_for_status()
            j = r.json()
            if j.get("ok"):
                st.success("✅ سفارش معلق ثبت شد. \
اکنون مبلغ را به آدرس TRON تعیین‌شده واریز کنید و **همان Tax ID** را در MEMO بنویسید. \
پس از تأیید شبکه، لایسنس خودکار صادر می‌شود و ایمیل می‌آید.")
            else:
                st.error(f"Apps Script error: {j}")
        except Exception as e:
            st.error(f"POST error: {e}")

st.caption("نیاز به راهنمایی بیشتر داشتید، به ما پیام بدهید.")
