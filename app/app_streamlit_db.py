import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os, json, requests
from pathlib import Path

st.set_page_config(page_title="AI Market Sentiment (Demo/Pro)", page_icon="📊", layout="wide")
st.title("📊 AI Market Sentiment — Demo / Pro")

APP_MODE = os.getenv("APP_MODE", "demo").lower()
DEMO_ASSETS = {"BTC"}
DEMO_DAYS = 3
HIDE_ALERTS_IN_DEMO = True

PRO_KEY = os.getenv("PRO_KEY", "").strip()
if APP_MODE == "pro":
    st.info("Pro Mode: لطفاً کلید دسترسی را وارد کنید.")
    if "authed" not in st.session_state:
        st.session_state.authed = False
    with st.form("pro_login", clear_on_submit=False):
        user_key = st.text_input("Access key", type="password")
        submitted = st.form_submit_button("Unlock")
    if not PRO_KEY:
        st.error("کلید Pro روی سیستم ست نشده است (PRO_KEY).")
        st.stop()
    if submitted:
        if user_key.strip() == PRO_KEY:
            st.session_state.authed = True
            st.success("Unlocked ✅")
        else:
            st.session_state.authed = False
            st.error("کلید اشتباه است.")
    if not st.session_state.authed:
        st.stop()

BASE = Path(__file__).resolve().parent.parent

@st.cache_data(ttl=300)
def load_daily_df():
    data_url = os.getenv("DATA_URL", "").strip()
    if data_url:
        r = requests.get(data_url, timeout=20)
        r.raise_for_status()
        j = r.json()
    else:
        local_json = BASE / "data" / "daily_sentiment.json"
        if not local_json.exists():
            return pd.DataFrame(columns=["day","asset","avg_sentiment","count_used"])
        j = json.loads(local_json.read_text(encoding="utf-8"))
    df = pd.DataFrame(j)
    if df.empty:
        return df
    df["day"] = pd.to_datetime(df["day"])
    return df

st.caption(f"Mode: {APP_MODE.upper()}  |  Data Source: {'DATA_URL' if os.getenv('DATA_URL') else 'local JSON'}")

try:
    df = load_daily_df()

    if APP_MODE == "demo" and not df.empty:
        df = df[df["asset"].isin(list(DEMO_ASSETS))].copy()
        last_day = df["day"].max()
        if pd.notnull(last_day):
            df = df[df["day"] >= (last_day - pd.Timedelta(days=DEMO_DAYS-1))]

    with st.sidebar:
        st.header("Filters")
        all_assets = sorted(df["asset"].unique().tolist()) if not df.empty else []
        selected_assets = st.multiselect("Assets", all_assets, default=all_assets)
        if not df.empty:
            min_day = df["day"].min().date()
            max_day = df["day"].max().date()
            dr = st.date_input("Date range", value=(min_day, max_day), min_value=min_day, max_value=max_day)
        else:
            dr = None

    if dr and isinstance(dr, tuple) and len(dr) == 2 and not df.empty:
        start, end = pd.to_datetime(dr[0]), pd.to_datetime(dr[1])
        f = (df["day"] >= start) & (df["day"] <= end)
        if selected_assets:
            f &= df["asset"].isin(selected_assets)
        dff = df.loc[f].copy()
    else:
        dff = df.copy()

    st.subheader("📈 Daily Sentiment by Asset")
    if dff.empty:
        st.warning("No data to display yet. Wait for hourly update or run ETL locally once to seed data.")
    else:
        fig = plt.figure(figsize=(9, 3.2))
        for a in (selected_assets or []):
            sub = dff[dff["asset"] == a]
            if not sub.empty:
                plt.plot(sub["day"], sub["avg_sentiment"], marker="o", label=f"{a} (n≈{int(sub['count_used'].sum())})")
        plt.axhline(0, linestyle="--", linewidth=1, alpha=0.5)
        plt.xlabel("Date")
        plt.ylabel("Avg Sentiment (-1..1)")
        plt.title("Daily Market Sentiment")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)

    st.subheader("🔔 Notes")
    if APP_MODE == "demo":
        st.caption("Demo Mode: Alerts hidden & only BTC for last 3 days. Upgrade to Pro for full assets/history.")

except Exception as e:
    st.error(f"Error: {e}")
