# app_streamlit_pro.py
# Minimal, production-safe Streamlit login using Google Apps Script licensing

import os
import json
import requests
from datetime import datetime, timezone
import streamlit as st

# --- Config via environment (Render -> Environment) ---
GAS_URL   = os.environ.get("GOOGLE_SCRIPT_URL", "").strip()   # Your GAS Web App 'exec' URL
GAS_TOKEN = os.environ.get("LICENSE_TOKEN", "").strip()       # Must match Code.gs token

APP_NAME  = "AI Market Sentiment Pro"

# ---------- Utilities ----------
def call_gas(action: str, extra: dict) -> dict:
    """POST JSON to Google Apps Script with safe defaults (redirects, timeout, JSON handling)."""
    if not GAS_URL or not GAS_TOKEN:
        return {"ok": False, "error": "server_misconfigured"}

    body = {"token": GAS_TOKEN, "action": action}
    if extra:
        body.update(extra)

    try:
        r = requests.post(
            GAS_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            allow_redirects=True,
            timeout=20,
        )
    except Exception as e:
        return {"ok": False, "error": f"request_failed: {e}"}

    # Try to parse JSON; GAS may return HTML on errors
    try:
        data = r.json()
    except Exception:
        snippet = (r.text or "")[:500]
        return {"ok": False, "error": f"bad_json status={r.status_code}", "text": snippet}

    if r.status_code != 200 and "error" not in data:
        data["error"] = f"http_{r.status_code}"
        data["status"] = r.status_code
    return data


def verify_license(email: str, license_key: str) -> dict:
    """Calls GAS verify action -> expects {ok, plan, expires_at, days_left}."""
    email = (email or "").strip().lower()
    license_key = (license_key or "").strip()

    if not email or not license_key:
        return {"ok": False, "error": "missing_credentials"}

    resp = call_gas("verify", {"email": email, "license_key": license_key})

    if not resp.get("ok"):
        err = (resp.get("error") or "").lower()
        if "not_found" in err:
            return {"ok": False, "error": "not_found"}
        if "expired" in err:
            return {"ok": False, "error": "expired"}
        if "server_misconfigured" in err:
            return {"ok": False, "error": "server_misconfigured"}
        return {"ok": False, "error": err or "unknown_error"}

    # Normalize days_left to int
    try:
        resp["days_left"] = int(resp.get("days_left", 0))
    except Exception:
        resp["days_left"] = 0
    return resp


def sign_out():
    for k in ("auth_ok", "user_email", "plan", "expires_at", "days_left"):
        if k in st.session_state:
            del st.session_state[k]
    st.experimental_rerun()


# ---------- UI ----------
st.set_page_config(page_title=APP_NAME, page_icon="📈", layout="centered")
st.title(APP_NAME)

# Create session flags if missing
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

if st.session_state.auth_ok:
    # ---- Logged-in view (placeholder dashboard) ----
    st.success(
        f"Welcome, **{st.session_state.user_email}** — Plan: **{st.session_state.plan}**, "
        f"Days left: **{st.session_state.days_left}** (expires at {st.session_state.expires_at})."
    )
    st.divider()
    st.subheader("Dashboard")
    st.write("✅ Your license is valid. Load your charts, data, and features here.")

    st.button("Sign out", on_click=sign_out)
else:
    # ---- Login form ----
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com")
        license_key = st.text_input("License key", placeholder="PRO-YYYYMMDD-XXXXXX")
        submitted = st.form_submit_button("Continue")

    if submitted:
        resp = verify_license(email, license_key)
        if resp.get("ok"):
            st.session_state.auth_ok    = True
            st.session_state.user_email = email.strip().lower()
            st.session_state.plan       = resp.get("plan", "")
            st.session_state.expires_at = resp.get("expires_at", "")
            st.session_state.days_left  = resp.get("days_left", 0)
            st.success("License verified. Redirecting…")
            st.experimental_rerun()
        else:
            err = resp.get("error", "unknown_error")
            # Human-friendly messages
            messages = {
                "missing_credentials": "Please enter both email and license key.",
                "not_found": "License not found for this email. Please check and try again.",
                "expired": "Your license is expired. Please renew to continue.",
                "server_misconfigured": "Server is not configured (missing GOOGLE_SCRIPT_URL or LICENSE_TOKEN).",
            }
            st.error(messages.get(err, f"Login failed: {err}"))

    # Renew helper button (optional, you can wire this to your purchase page)
    st.button("Renew License", help="Go to purchase/renewal page")
