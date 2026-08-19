import streamlit as st
import pandas as pd
import yfinance as yf

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="XAU/USD Alpha Confluence",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LIGHT THEME & STYLISH CUSTOM CSS ---
st.markdown("""
    <style>
    /* Light Mode Background & Global Font Settings */
    [data-testid="stAppViewContainer"] {
        background-color: #f8f9fa;
        color: #212529;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Clean Modern Cards */
    .metric-card {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 18px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        margin-bottom: 12px;
    }
    
    /* Text Wrapping and Fix for Truncation */
    .metric-value {
        font-size: 28px !important;
        font-weight: 700;
        color: #1a202c;
        word-break: break-word;
    }
    
    .metric-label {
        font-size: 14px !important;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 4px;
    }

    /* Analysis Item Styling */
    .analysis-item {
        background: #ffffff;
        padding: 12px 15px;
        border-radius: 8px;
        border: 1px solid #edf2f7;
        margin-bottom: 8px;
        font-size: 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.title("🪙 XAU/USD Alpha Confluence & Risk Hub")
st.markdown("Automated Live Technical Scanner & Dynamic Position Sizing System.")
st.markdown("---")

# --- SIDEBAR: USER INPUTS & RISK PARAMETERS ---
st.sidebar.header("Risk Settings ⚙️")
account_balance = st.sidebar.number_input("Account Balance ($)", min_value=100.0, max_value=1000000.0, value=10000.0, step=500.0)
base_risk_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
stop_loss_pips = st.sidebar.number_input("Assumed Stop Loss (USD/Points)", min_value=1.0, max_value=100.0, value=5.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.caption("Data Source: Yahoo Finance (GC=F)")

# --- DATA FETCHER ---
@st.cache_data(ttl=180)
def load_gold_data():
    try:
        df = yf.download("GC=F", period="60d", interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return None

with st.spinner("Scanning market data..."):
    df = load_gold_data()

if df is None or df.empty:
    st.error("Market data unavailable. Please check connection or try again later.")
else:
    # --- TECHNICAL CALCULATIONS ---
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    df['Support'] = df['Low'].rolling(window=20).min()
    df['Resistance'] = df['High'].rolling(window=20).max()

    current_price = float(df['Close'].iloc[-1])
    current_rsi = float(df['RSI'].iloc[-1])
    ema_50 = float(df['EMA_50'].iloc[-1])
    ema_200 = float(df['EMA_200'].iloc[-1])
    support_level = float(df['Support'].iloc[-1])
    resistance_level = float(df['Resistance'].iloc[-1])

    # --- CONFLUENCE SCORING ---
    buy_score = 0
    sell_score = 0
    reasons = []

    if current_price > ema_50 and ema_50 > ema_200:
        buy_score += 35
        reasons.append(("✅", "Bullish Trend (Price > EMA 50 > EMA 200)", "+35"))
    elif current_price < ema_50 and ema_50 < ema_200:
        sell_score += 35
        reasons.append(("🔻", "Bearish Trend (Price < EMA 50 < EMA 200)", "+35"))
    else:
        reasons.append(("⚠️", "Neutral/Choppy Trend (Mixed MAs)", "0"))

    if current_rsi < 30:
        buy_score += 35
        reasons.append(("✅", f"RSI Oversold ({current_rsi:.1f}) - Buy Zone", "+35"))
    elif current_rsi > 70:
        sell_score += 35
        reasons.append(("🔻", f"RSI Overbought ({current_rsi:.1f}) - Sell Zone", "+35"))
    else:
        reasons.append(("ℹ️", f"RSI Neutral ({current_rsi:.1f}) - Safe", "0"))

    dist_to_support = abs(current_price - support_level)
    dist_to_resistance = abs(current_price - resistance_level)
    
    if dist_to_support < (current_price * 0.0025):
        buy_score += 30
        reasons.append(("✅", f"Testing Support Zone (${support_level:.2f})", "+30"))
    elif dist_to_resistance < (current_price * 0.0025):
        sell_score += 30
        reasons.append(("🔻", f"Testing Resistance Zone (${resistance_level:.2f})", "+30"))
    else:
        reasons.append(("ℹ️", "Price mid-range (Away from S/R)", "0"))

    total_score = max(buy_score, sell_score)
    if buy_score > sell_score:
        signal_signal = "BUY SETUP"
        signal_color = "#16a34a" # Green
        final_score = buy_score
    elif sell_score > buy_score:
        signal_signal = "SELL SETUP"
        signal_color = "#dc2626" # Red
        final_score = sell_score
    else:
        signal_signal = "NEUTRAL"
        signal_color = "#ca8a04" # Yellow/Orange
        final_score = 0
        
    if final_score > 100: final_score = 100

    # --- RISK MANAGEMENT ---
    risk_dollar_amount = account_balance * (base_risk_pct / 100.0)
    
    if final_score >= 75:
        risk_modifier = 1.0
        status_text = "Strong Setup (Full Risk)"
        status_badge_color = "#dcfce7"
        status_text_color = "#166534"
    elif 40 <= final_score < 75:
        risk_modifier = 0.5
        status_text = "Moderate (Half Risk)"
        status_badge_color = "#fef9c3"
        status_text_color = "#854d0e"
    else:
        risk_modifier = 0.1
        status_text = "Risky / Micro-Lot Only"
        status_badge_color = "#fee2e2"
        status_text_color = "#991b1b"
        
    effective_risk = risk_dollar_amount * risk_modifier
    lot_size_recommended = round(effective_risk / (stop_loss_pips * 100.0), 2)
    if lot_size_recommended < 0.01: lot_size_recommended = 0.01

    # --- UI DISPLAY ---
    st.subheader("Market Metrics Overview 📊")
    
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Live Gold Price</div>
                <div class="metric-value">${current_price:.2f}</div>
            </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Signal Status</div>
                <div class="metric-value" style="color: {signal_color}; font-size: 22px !important;">{signal_signal}</div>
            </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Confidence Score</div>
                <div class="metric-value">{final_score}%</div>
            </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Market Quality</div>
                <div style="background-color: {status_badge_color}; color: {status_text_color}; padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 13px; display: inline-block; margin-top: 6px;">
                    {status_text}
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- TWO COLUMN DETAILS ---
    col_left, col_right = st.columns([1.1, 0.9])
    
    with col_left:
        st.markdown("### Confluence Breakdown 🔎")
        for icon, text, pts in reasons:
            st.markdown(f"""
                <div class="analysis-item">
                    <span>{icon} <strong>{text}</strong></span>
                    <span style="float: right; color: #64748b; font-weight: 500;">{pts} pts</span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### Key Technical Levels")
        l_col1, l_col2 = st.columns(2)
        l_col1.metric("Support Zone", f"${support_level:.2f}")
        l_col2.metric("Resistance Zone", f"${resistance_level:.2f}")

    with col_right:
        st.markdown("### 🛡️ Dynamic Position Sizing")
        st.markdown(f"""
            <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                <p style="margin: 0; font-size: 14px; color: #64748b;">Recommended Lot Size</p>
                <p style="font-size: 32px; font-weight: 700; color: #0284c7; margin: 5px 0;">{lot_size_recommended} Lots</p>
                <hr style="border: none; border-top: 1px solid #edf2f7; margin: 12px 0;">
                <p style="margin: 4px 0; font-size: 14px;"><strong>Capital at Risk:</strong> ${effective_risk:.2f}</p>
                <p style="margin: 4px 0; font-size: 14px;"><strong>Stop Loss Distance:</strong> {stop_loss_pips} Points</p>
                <p style="margin: 4px 0; font-size: 14px;"><strong>RSI Value:</strong> {current_rsi:.1f}</p>
            </div>
        """, unsafe_allow_html=True)

    # --- CHART SECTION ---
    st.markdown("---")
    st.subheader("📉 Price Action & Trend Lines")
    chart_df = df[['Close', 'EMA_50', 'EMA_200']].tail(96)
    st.line_chart(chart_df, height=320, use_container_width=True)
