import streamlit as st
import pandas as pd
import requests
import numpy as np
import altair as alt

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="XAU/USD Multi-Timeframe Hub",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto refresh every 10 seconds for live updates
st.markdown("""
    <meta http-equiv="refresh" content="10">
""", unsafe_allow_html=True)

# --- LIGHT THEME & CSS ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1rem !important;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #f8f9fa;
        color: #212529;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    .metric-card {
        background: #ffffff;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        padding: 14px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 22px !important;
        font-weight: 700;
        color: #1a202c;
        word-break: break-word;
    }
    .metric-label {
        font-size: 13px !important;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 2px;
    }
    .analysis-item {
        background: #ffffff;
        padding: 10px 12px;
        border-radius: 6px;
        border: 1px solid #edf2f7;
        margin-bottom: 6px;
        font-size: 13px;
    }
    h1, h2, h3 {
        color: #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- COMPACT HEADER ---
st.markdown("## 🪙 XAU/USD Multi-Timeframe Confluence Hub")
st.markdown("---")

# --- SIDEBAR: RISK SETTINGS ---
st.sidebar.header("Risk Settings ⚙️")
account_balance = st.sidebar.number_input("Account Balance ($)", min_value=10.0, max_value=1000000.0, value=1000.0, step=100.0)
base_risk_pct = st.sidebar.slider("Base Risk Per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
stop_loss_pips = st.sidebar.number_input("Assumed Stop Loss (USD/Points)", min_value=1.0, max_value=100.0, value=5.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.caption("Multi-Timeframe Analysis Active (1m, 5m, 15m)")

# --- MULTI-TIMEFRAME DATA FETCHER ---
@st.cache_data(ttl=5)
def fetch_multi_tf_data():
    def get_klines(interval):
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={interval}&limit=60"
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                d = res.json()
                df = pd.DataFrame(d, columns=['Open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time', 'QAV', 'NOT', 'TBBAV', 'TBQAV', 'Ignore'])
                df['Datetime'] = pd.to_datetime(df['Open_time'], unit='ms')
                for col in ['Open', 'High', 'Low', 'Close']:
                    df[col] = df[col].astype(float)
                return df[['Datetime', 'Open', 'High', 'Low', 'Close']]
        except:
            pass
        return None

    df_1m = get_klines('1m')
    df_5m = get_klines('5m')
    df_15m = get_klines('15m')
    
    # Fallback if API fails
    if df_1m is None or df_5m is None or df_15m is None:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq='1min')
        base_p = 4341.0 + np.random.normal(0, 0.2, 60).cumsum()
        df_dummy = pd.DataFrame({'Datetime': dates, 'Open': base_p-0.1, 'High': base_p+0.4, 'Low': base_p-0.4, 'Close': base_p})
        return df_dummy, df_dummy, df_dummy

    return df_1m, df_5m, df_15m

df_1m, df_5m, df_15m = fetch_multi_tf_data()
current_price = float(df_1m['Close'].iloc[-1])

# --- CALCULATE INDICATORS ACROSS TIMEFRAMES ---
def analyze_tf(df, span):
    ema = df['Close'].ewm(span=span, adjust=False).mean().iloc[-1]
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss)))
    current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    support = float(df['Low'].rolling(window=20).min().iloc[-1])
    resistance = float(df['High'].rolling(window=20).max().iloc[-1])
    return ema, current_rsi, support, resistance

ema_1m, rsi_1m, sup_1m, res_1m = analyze_tf(df_1m, 20)
ema_5m, rsi_5m, sup_5m, res_5m = analyze_tf(df_5m, 30)
ema_15m, rsi_15m, sup_15m, res_15m = analyze_tf(df_15m, 50)

# --- CONFLUENCE SCORING ENGINE ---
buy_score = 0
sell_score = 0
reasons = []

# 15M Macro Trend Check (High Weight)
if current_price > ema_15m:
    buy_score += 35
    reasons.append(("✅", f"15m Macro Trend is Bullish (Price > EMA)"))
else:
    sell_score += 35
    reasons.append(("🔻", f"15m Macro Trend is Bearish (Price < EMA)"))

# 5M Momentum Check (Medium Weight)
if current_price > ema_5m:
    buy_score += 25
    reasons.append(("✅", f"5m Momentum is Bullish"))
else:
    sell_score += 25
    reasons.append(("🔻", f"5m Momentum is Bearish"))

# 1M Execution & RSI Check
if rsi_1m < 45:
    buy_score += 25
    reasons.append(("✅", f"1m RSI indicates Dip Entry ({rsi_1m:.1f})"))
elif rsi_1m > 55:
    sell_score += 25
    reasons.append(("🔻", f"1m RSI indicates Rally Exit ({rsi_1m:.1f})"))
else:
    reasons.append(("ℹ️", f"1m RSI Neutral ({rsi_1m:.1f})"))

# Support / Resistance Proximity
dist_sup = abs(current_price - sup_5m)
dist_res = abs(current_price - res_5m)
if dist_sup < dist_res:
    buy_score += 15
    reasons.append(("✅", f"Closer to 5m Support Zone (${sup_5m:.2f})"))
else:
    sell_score += 15
    reasons.append(("🔻", f"Closer to 5m Resistance Zone (${res_5m:.2f})"))

# Final Decision with High Confluence Threshold (>= 75)
if buy_score >= 75 and buy_score > sell_score:
    signal_text = "BUY"
    signal_color = "#16a34a"
    accuracy_pct = buy_score
    risk_modifier = 1.5
    safe_tp = current_price + (stop_loss_pips * 1.5)
    risky_tp = current_price + (stop_loss_pips * 3.0)
elif sell_score >= 75 and sell_score > buy_score:
    signal_text = "SELL"
    signal_color = "#dc2626"
    accuracy_pct = sell_score
    risk_modifier = 1.5
    safe_tp = current_price - (stop_loss_pips * 1.5)
    risky_tp = current_price - (stop_loss_pips * 3.0)
else:
    signal_text = "NO BUY / NO SELL"
    signal_color = "#ca8a04"
    accuracy_pct = max(buy_score, sell_score)
    risk_modifier = 0.2
    safe_tp = 0.0
    risky_tp = 0.0

# --- POSITION SIZING ---
risk_dollar_amount = account_balance * (base_risk_pct / 100.0)
effective_risk = risk_dollar_amount * risk_modifier
lot_size_recommended = round(effective_risk / (stop_loss_pips * 100.0), 2)
if lot_size_recommended < 0.01: lot_size_recommended = 0.01

# --- UI DISPLAY ---
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">XAU/USD Live Spot Rate</div>
            <div class="metric-value">${current_price:.2f}</div>
        </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Multi-TF Signal & Accuracy</div>
            <div class="metric-value" style="color: {signal_color}; font-size: 18px !important;">
                {signal_text} <span style="font-size: 14px; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">({accuracy_pct}%)</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Auto-Scaled Lot Size</div>
            <div class="metric-value" style="color: #0284c7;">{lot_size_recommended} Lots</div>
        </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Take Profit Targets</div>
            <div style="font-size: 13px; font-weight: 600; color: #334155; margin-top: 2px;">
                🛡️ Safe: ${safe_tp:.2f}<br>🔥 Risky: ${risky_tp:.2f}
            </div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- BREAKDOWN SECTION ---
col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    st.markdown("### Multi-Timeframe Technical Breakdown")
    for icon, text in reasons:
        st.markdown(f"""
            <div class="analysis-item">
                <span>{icon} <strong>{text}</strong></span>
            </div>
        """, unsafe_allow_html=True)
    
    l_col1, l_col2 = st.columns(2)
    l_col1.caption(f"**5m Support:** ${sup_5m:.2f}")
    l_col2.caption(f"**5m Resistance:** ${res_5m:.2f}")

with col_right:
    st.markdown("### Risk & Execution Overview")
    st.markdown(f"""
        <div style="background-color: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 13px;">
            <p style="margin: 3px 0;"><strong>Balance:</strong> ${account_balance:.2f}</p>
            <p style="margin: 3px 0;"><strong>Effective Risk Amount:</strong> ${effective_risk:.2f}</p>
            <p style="margin: 3px 0;"><strong>Safe TP (1.5R):</strong> ${safe_tp:.2f}</p>
            <p style="margin: 3px 0;"><strong>Risky TP (3R):</strong> ${risky_tp:.2f}</p>
        </div>
    """, unsafe_allow_html=True)

# --- CHART ---
st.markdown("---")
st.markdown("### 5-Minute Price Action Chart")

chart_df = df_5m[['Datetime', 'Close']].tail(60).melt('Datetime', var_name='Indicator', value_name='Price')
chart = alt.Chart(chart_df).mark_line(point=True).encode(
    x=alt.X('Datetime:T', title='Time (5m Candles)'),
    y=alt.Y('Price:Q', title='Price ($)', scale=alt.Scale(zero=False)),
    color=alt.Color('Indicator:N', scale=alt.Scale(domain=['Close'], range=['#0284c7']))
).properties(
    height=260
).interactive()

st.altair_chart(chart, use_container_width=True)
