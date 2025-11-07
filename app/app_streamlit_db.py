# app_streamlit_db.py
import os
import requests
import streamlit as st
from datetime import datetime

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL", "").strip()
SECRET_TOKEN    = os.environ.get("APPS_SECRET_TOKEN", "").strip()

st.set_page_config(page_title="AI Market Sentiment Pro", page_icon="📈", layout="wide")

def verify_license(email: str, license_key: str):
    try:
        payload = {
            "token": SECRET_TOKEN,
            "action": "verify",
            "email": email.strip(),
            "license_key": license_key.strip(),
        }
        r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
        if r.headers.get("content-type","").startswith("application/json"):
            return r.json()
        return {"ok": False, "error": "bad_content_type"}
    except Exception as e:
        return {"ok": False, "error": f"verify_failed: {e}"}

def login_box():
    st.markdown("### Sign in")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", value=st.session_state.get("email",""))
        license_key = st.text_input("License key", value=st.session_state.get("license_key",""))
        ok = st.form_submit_button("Continue")
    if ok:
        st.session_state.email = email.strip()
        st.session_state.license_key = license_key.strip()
        return True
    return False

# -----------------------------------------
# Auth gate
# -----------------------------------------
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

st.title("AI Market Sentiment Pro")

if not st.session_state.auth_ok:
    submitted = login_box()
    if submitted:
        email = st.session_state.get("email","").strip()
        lkey  = st.session_state.get("license_key","").strip()
        if not email or not lkey:
            st.error("Please enter your email and license key.")
            st.stop()
        res = verify_license(email, lkey)
        if res.get("ok"):
            st.session_state.auth_ok = True
            st.session_state.verified = res
        else:
            st.error("Your license is invalid or expired. Please renew to continue.")
            st.link_button("Renew License", "/buy")
            st.stop()

# اگر اینجاییم یعنی لاگین OK
ver = st.session_state.get("verified", {})
st.sidebar.markdown("### License")
if ver:
    st.sidebar.success(
        f"✅ Active • {ver.get('plan','-')}\n\n"
        f"Expires: {ver.get('expires_at','-')}\n"
        f"Days left: {ver.get('days_left','-')}"
    )
else:
    st.sidebar.info("Session verified.")

# ----------------------------
# TODO: محتوای اصلی داشبوردت
# ----------------------------
st.markdown("## Dashboard")
st.write("Welcome! Your license is active. Put your charts and analytics here…")
