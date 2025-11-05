import os
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ---------- تنظیمات صفحه ----------
st.set_page_config(
    page_title="AI Market Sentiment",
    page_icon="📊",
    layout="wide"
)

APP_MODE = os.getenv("APP_MODE", "demo").lower()  # demo | pro
DATA_URL = os.getenv("DATA_URL", "").strip()
PRO_KEY_ENV = os.getenv("PRO_KEY", "").strip()

# ---------- هِدِر ----------
left, mid, right = st.columns([1.5, 1, 1.2])
with left:
    st.markdown("### 📊 AI Market Sentiment Dashboard")
with right:
    st.markdown(
        "#### "
        + ("**Mode: DEMO**" if APP_MODE == "demo" else "**Mode: PRO**")
        + f"  \n`Data Source: DATA_URL`"
    )

st.markdown("---")

# ---------- یوتیلیتی: خواندن JSON از GitHub Raw ----------
@st.cache_data(ttl=300)
def fetch_data(url: str):
    if not url:
        return pd.DataFrame()
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()  # list of {day, asset, avg_sentiment, count_used}
    df = pd.DataFrame(data)
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"])
        df = df.sort_values(["asset", "day"])
    return df

# ---------- لود دیتا ----------
try:
    df = fetch_data(DATA_URL)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

if df.empty:
    st.warning("No data to display yet.")
    st.stop()

# ---------- کنترل دسترسی PRO ----------
if APP_MODE == "pro":
    if "auth_ok" not to in st.session_state:
        st.session_state["auth_ok"] = False

    if not st.session_state["auth_ok"]:
        st.info("🔐 برای مشاهدهٔ همهٔ دارایی‌ها، کلید دسترسی (Pro Key) را وارد کنید.")
        k = st.text_input("Pro Key", type="password")
        go = st.button("ورود به نسخه Pro")
        if go:
            if PRO_KEY_ENV and k.strip() == PRO_KEY_ENV:
                st.session_state["auth_ok"] = True
                st.success("دسترسی تأیید شد ✅")
                st.rerun()
            else:
                st.error("کلید صحیح نیست.")
        st.stop()

# ---------- سایدبار ----------
with st.sidebar:
    st.markdown("### 🎛️ تنظیمات")
    all_assets = sorted(df["asset"].unique().tolist())

    if APP_MODE == "demo":
        st.caption("نسخه دمو فقط BTC را نشان می‌دهد.")
        default_assets = ["BTC"] if "BTC" in all_assets else [all_assets[0]]
        assets = st.multiselect("دارایی‌ها", all_assets, default_assets, disabled=True)
        st.link_button("🔐 ارتقا به Pro", "https://sentiment-pro.onrender.com")
    else:
        # نسخه پرو: کاربر آزاد است
        default_assets = ["BTC", "GOLD"] if "GOLD" in all_assets else [all_assets[0]]
        assets = st.multiselect("دارایی‌ها", all_assets, default_assets)

    st.markdown("---")
    st.caption("⚠️ Educational only — not financial advice.")

# فیلتر دارایی‌ها
if APP_MODE == "demo":
    # پین روی BTC
    work = df[df["asset"] == "BTC"].copy()
else:
    pick = assets or all_assets
    work = df[df["asset"].isin(pick)].copy()

if work.empty:
    st.warning("داده‌ای برای فیلتر انتخابی وجود ندارد.")
    st.stop()

# ---------- ویجت تاریخ ----------
min_day, max_day = work["day"].min(), work["day"].max()
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### بازهٔ زمانی")
with c2:
    st.caption(f"{min_day.date()} → {max_day.date()}")

# ---------- نمودار ----------
st.markdown("### روند احساسات")
fig, ax = plt.subplots(figsize=(12, 5), dpi=120)

for a in sorted(work["asset"].unique()):
    sub = work[work["asset"] == a]
    ax.plot(sub["day"], sub["avg_sentiment"], label=a, linewidth=2)

ax.axhline(0, linewidth=1, linestyle="--")
ax.set_ylabel("Avg Sentiment")
ax.set_xlabel("Date")
ax.legend(loc="best")
st.pyplot(fig, use_container_width=True)

# ---------- جدول خلاصه روز آخر ----------
last_day = work["day"].max()
today_rows = work[work["day"] == last_day].copy().sort_values("asset")
today_rows["signal"] = today_rows["avg_sentiment"].apply(
    lambda x: "✅ bullish" if x > 0.15 else ("❗ bearish" if x < -0.15 else "⏸️ neutral")
)

st.markdown("### اسنپ‌شات آخرین روز")
st.dataframe(
    today_rows[["asset", "avg_sentiment", "count_used", "signal"]]
    .rename(columns={"asset": "Asset", "avg_sentiment": "AvgSent", "count_used": "N"})
    .reset_index(drop=True),
    use_container_width=True
)
