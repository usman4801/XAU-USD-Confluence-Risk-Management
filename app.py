import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="XAU/USD AI Confluence & Risk Hub",
    page_icon="🪙",
    layout="wide"
)

# Custom Styling for Clean Dashboard
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .metric-card { background-color: #1a1c23; padding: 20px; border-radius: 10px; border: 1px solid #2d3748; }
    .stAlert { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.title("🪙 XAU/USD Advanced Confluence & Risk Dashboard")
st.markdown("Automated Technical Scanner, Multi-Indicator Confluence Scoring, and Dynamic Lot Sizing.")

# --- SIDEBAR: USER INPUTS & RISK PARAMETERS ---
st.sidebar.header("⚙️ Risk Management Settings")
account_balance = st.sidebar.number_input("Account Balance ($)", min_value=100.0, max_value=1000000.0, value=5000.0, step=100.0)
base_risk_pct = st.sidebar.slider("Max Risk Per Trade (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
stop_loss_pips = st.sidebar.number_input("Assumed Stop Loss (in USD/Points)", min_value=1.0, max_value=50.0, value=5.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.info("Data source: Yahoo Finance (GC=F / Gold Futures)")

# --- DATA FETCHER ---
@st.cache_data(ttl=300) # Cache data for 5 minutes
def load_gold_data():
    try:
        # Fetching Gold Futures data (GC=F acts as XAU/USD proxy)
        df = yf.download("GC=F", period="60d", interval="1h")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return None

with st.spinner("Fetching live XAU/USD market data and calculating technical indicators..."):
    df = load_gold_data()

if df is None or df.empty:
    st.error("Failed to load market data. Please check your internet connection or try refreshing.")
else:
    # --- TECHNICAL ANALYSIS CALCULATIONS ---
    # Indicators using pandas_ta
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['EMA_50'] = ta.ema(df['Close'], length=50)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    
    # Simple Support & Resistance based on rolling min/max
    df['Support'] = df['Low'].rolling(window=20).min()
    df['Resistance'] = df['High'].rolling(window=20).max()

    # Current Market Metrics
    current_price = float(df['Close'].iloc[-1])
    current_rsi = float(df['RSI'].iloc[-1])
    ema_50 = float(df['EMA_50'].iloc[-1])
    ema_200 = float(df['EMA_200'].iloc[-1])
    support_level = float(df['Support'].iloc[-1])
    resistance_level = float(df['Resistance'].iloc[-1])

    # --- CONFLUENCE SCORING ENGINE ---
    buy_score = 0
    sell_score = 0
    reasons = []

    # 1. Trend Analysis (EMA Check)
    if current_price > ema_50 and ema_50 > ema_200:
        buy_score += 30
        reasons.append("✅ **Strong Uptrend:** Price is above both EMA 50 & EMA 200 (+30%)")
    elif current_price < ema_50 and ema_50 < ema_200:
        sell_score += 30
        reasons.append("🔻 **Strong Downtrend:** Price is below both EMA 50 & EMA 200 (+30%)")
    else:
        reasons.append("⚠️ **Choppy Trend:** Moving averages are mixed (Neutral)")

    # 2. Momentum Analysis (RSI Check)
    if current_rsi < 35:
        buy_score += 30
        reasons.append(f"✅ **RSI Oversold ({current_rsi:.1f}):** Good bounce potential (+30%)")
    elif current_rsi > 65:
        sell_score += 30
        reasons.append(f"🔻 **RSI Overbought ({current_rsi:.1f}):** Potential pullback zone (+30%)")
    else:
        reasons.append(f"ℹ️ **RSI Neutral ({current_rsi:.1f}):** In safe middle zone (+0%)")

    # 3. Proximity to Support / Resistance
    dist_to_support = abs(current_price - support_level)
    dist_to_resistance = abs(current_price - resistance_level)

    if dist_to_support < (current_price * 0.003): # Within 0.3% of support
        buy_score += 40
        reasons.append(f"✅ **At Support Zone:** Price testing key support near ${support_level:.2f} (+40%)")
    elif dist_to_resistance < (current_price * 0.003): # Within 0.3% of resistance
        sell_score += 40
        reasons.append(f"🔻 **At Resistance Zone:** Price testing key resistance near ${resistance_level:.2f} (+40%)")
    else:
        reasons.append("ℹ️ **Mid-Range Price:** Away from immediate S/R zones (+0%)")

    # Final Decision Logic
    total_score = max(buy_score, sell_score)
    if total_score > 100: total_score = 100

    if buy_score > sell_score:
        signal_type = "🟢 BUY SETUP"
        confidence = buy_score
    elif sell_score > buy_score:
        signal_type = "🔴 SELL SETUP"
        confidence = sell_score
    else:
        signal_type = "⚪ NEUTRAL / NO TRADE"
        confidence = 0

    # --- RISK & LOT SIZE CALCULATION ---
    # Standard Gold Lot: 1 Lot = 100 oz. 1 Point move = $100 per lot.
    # Risk Amount ($) = Account Balance * (Risk % / 100)
    risk_dollar_amount = account_balance * (base_risk_pct / 100.0)
    
    # Adjust risk multiplier based on confidence score (Dynamic Lot Sizing)
    if confidence >= 70:
        risk_modifier = 1.0  # Full allowed risk (Strong setup)
        market_status = "🔥 Strong High-Probability Setup"
    elif 40 <= confidence < 70:
        risk_modifier = 0.5  # Half risk (Moderate setup / Slightly risky)
        market_status = "⚠️ Moderate Setup (Proceed with Caution)"
    else:
        risk_modifier = 0.1  # Minimal risk (Choppy / Low confidence)
        market_status = "❌ High Risk / Choppy Market (Avoid or Micro-lot)"

    effective_risk_dollar = risk_dollar_amount * risk_modifier
    # Lot Size Formula = Risk Amount / (Stop Loss Points * Contract Size ($10 per point for micro/mini, $100 for standard))
    # Using standard standard lot calculation where 1 pip/point = $10 per 0.1 lot or $100 per 1.0 lot.
    # Safe approximation: Lot Size = Effective Risk / (Stop Loss * 100)
    calculated_lot_size = round(effective_risk_dollar / (stop_loss_pips * 100.0), 2)
    if calculated_lot_size < 0.01:
        calculated_lot_size = 0.01

    # --- MAIN DASHBOARD DISPLAY ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Live Gold Price", f"${current_price:.2f}")
    col2.metric("AI Signal", signal_type)
    col3.metric("Confidence Score", f"{confidence}%")
    col4.metric("Market Quality", market_status)

    st.markdown("---")

    # Detailed Layout
    left_col, right_col = st.columns([1.2, 0.8])

    with left_col:
        st.subheader("📊 Confluence Breakdown & Analysis")
        for r in reasons:
            st.markdown(r)
        
        st.markdown("### 📈 Key Technical Levels")
        lvl_col1, lvl_col2 = st.columns(2)
        lvl_col1.info(f"**Estimated Support:** ${support_level:.2f}")
        lvl_col2.warning(f"**Estimated Resistance:** ${resistance_level:.2f}")

    with right_col:
        st.subheader("🛡️ Dynamic Risk & Position Sizing")
        st.markdown(f"**Signal Status:** {market_status}")
        st.markdown(f"**Recommended Lot Size:** ` {calculated_lot_size} Lots `")
        st.caption(f"Calculated using a {base_risk_pct}% base risk profile adjusted by confidence modifier ({int(risk_modifier*100)}%).")
        
        st.markdown("### 🧮 Trade Plan Summary")
        st.write(f"- **Max Capital at Risk:** ${effective_risk_dollar:.2f}")
        st.write(f"- **Assumed Stop Loss:** {stop_loss_pips} Points")
        st.write(f"- **RSI Value:** {current_rsi:.1f}")

    # --- PRICE CHART VISUALIZATION ---
    st.markdown("---")
    st.subheader("📉 XAU/USD 1-Hour Price Trend & Indicators")
    chart_data = df[['Close', 'EMA_50', 'EMA_200']].tail(100)
    st.line_chart(chart_data)
