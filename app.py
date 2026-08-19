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

# --- STYLISH CUSTOM CSS (Revamped UI) ---
st.markdown("""
    <style>
    /* Main Background */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #1a1c23 0%, #0e1117 100%);
        color: #e0e0e0;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #15171e;
        border-right: 1px solid #2d3748;
    }
    
    /* Glassmorphism Cards for Metrics */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        margin-bottom: 15px;
    }
    
    /* Fix for Truncated Text (Alfaz Katna Khatam) */
    .css-17eq0t5 { /* Streamlit's default metric value class */
        white-space: normal !important; /* Allow text to wrap */
        font-size: 34px !important; /* Slightly smaller for wrapping */
        line-height: 1.2 !important;
    }
    
    .stMetricLabel {
        font-size: 16px !important;
        color: #a0a0a0 !important;
    }

    /* Analysis Item Styling */
    .analysis-item {
        padding: 10px;
        border-bottom: 1px solid #2d3748;
        font-size: 15px;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'SF Pro Display', sans-serif;
    }
    
    /* Buttons & Inputs */
    .stNumberInput, .stSlider {
        background-color: #1a1c23 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.title("🪙 XAU/USD Alpha Confluence | Risk Hub")
st.markdown("Automated Live Scanner & Dynamic Position Sizing System.")
st.markdown("---")

# --- SIDEBAR: USER INPUTS & RISK PARAMETERS ---
st.sidebar.header("Risk Settings ⚙️")
account_balance = st.sidebar.number_input("Account Balance ($)", min_value=100.0, max_value=1000000.0, value=10000.0, step=500.0, help="Your total trading capital.")
base_risk_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1, help="Percentage of capital to risk on this setup.")
stop_loss_pips = st.sidebar.number_input("Assumed Stop Loss (in USD/Points)", min_value=1.0, max_value=100.0, value=5.0, step=0.5, help="Distance from entry to stop loss in Gold points.")

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Yahoo Finance API (GC=F)")

# --- DATA FETCHER ---
@st.cache_data(ttl=180) # Cache for 3 mins
def load_gold_data():
    try:
        df = yf.download("GC=F", period="60d", interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return None

with st.spinner("Scanning the markets... Fetching Gold price action..."):
    df = load_gold_data()

if df is None or df.empty:
    st.error("Market data unavailable. Please check connection or try again later.")
else:
    # --- TECHNICAL CALCULATIONS (Pure Pandas) ---
    # RSI (14 periods)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Moving Averages (EMA 50 and EMA 200)
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # Support & Resistance (Rolling min/max)
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

    # 1. Trend Check (EMA)
    if current_price > ema_50 and ema_50 > ema_200:
        buy_score += 35
        reasons.append(("✅", "Bullish Trend (Price > EMA 50 > EMA 200)", "+35"))
    elif current_price < ema_50 and ema_50 < ema_200:
        sell_score += 35
        reasons.append(("🔻", "Bearish Trend (Price < EMA 50 < EMA 200)", "+35"))
    else:
        reasons.append(("⚠️", "Neutral/Choppy Trend (Mixed MAs)", "0"))

    # 2. Momentum (RSI)
    if current_rsi < 30:
        buy_score += 35
        reasons.append(("✅", f"RSI Oversold ({current_rsi:.1f}) - Buying Opportunity", "+35"))
    elif current_rsi > 70:
        sell_score += 35
        reasons.append(("🔻", f"RSI Overbought ({current_rsi:.1f}) - Selling Opportunity", "+35"))
    else:
        reasons.append(("ℹ️", f"RSI Neutral ({current_rsi:.1f}) - Safe Zone", "0"))

    # 3. S/R Proximity
    dist_to_support = abs(current_price - support_level)
    dist_to_resistance = abs(current_price - resistance_level)
    
    if dist_to_support < (current_price * 0.0025): # Within 0.25% of Support
        buy_score += 30
        reasons.append(("✅", f"Price at Support Zone (${support_level:.2f})", "+30"))
    elif dist_to_resistance < (current_price * 0.0025): # Within 0.25% of Resistance
        sell_score += 30
        reasons.append(("🔻", f"Price at Resistance Zone (${resistance_level:.2f})", "+30"))
    else:
        reasons.append(("ℹ️", "Price mid-range (Away from S/R)", "0"))

    # Final Decision
    total_score = max(buy_score, sell_score)
    if buy_score > sell_score:
        signal_signal = "BUY"
        signal_emoji = "🟢"
        final_score = buy_score
    elif sell_score > buy_score:
        signal_signal = "SELL"
        signal_emoji = "🔴"
        final_score = sell_score
    else:
        signal_signal = "NEUTRAL"
        signal_emoji = "⚪"
        final_score = 0
        
    # Cap score at 100
    if final_score > 100: final_score = 100

    # --- RISK MANAGEMENT CALCULATIONS ---
    risk_dollar_amount = account_balance * (base_risk_pct / 100.0)
    
    if final_score >= 75:
        risk_modifier = 1.0
        status_text = "🔥 Strong Setup (Full Risk Allowed)"
        status_color = "#2ecc71" # Green
    elif 40 <= final_score < 75:
        risk_modifier = 0.5
        status_text = "⚠️ Moderate Setup (Use Half Risk)"
        status_color = "#f1c40f" # Yellow
    else:
        risk_modifier = 0.1
        status_text = "❌ Risky/Choppy (Avoid or Micro-Lot)"
        status_color = "#e74c3c" # Red
        
    effective_risk = risk_dollar_amount * risk_modifier
    # Safe approximation: 1 Lot (100oz) = $100 per point move.
    # Lot Size = Effective Risk / (Stop Loss Points * 100)
    lot_size_recommended = round(effective_risk / (stop_loss_pips * 100.0), 2)
    if lot_size_recommended < 0.01: lot_size_recommended = 0.01

    # --- MAIN DASHBOARD DISPLAY (Stylish Cards) ---
    st.subheader("Live Market Metrics 📊")
    
    # Row 1: Metrics (Top Cards)
    m1_c1, m1_c2, m1_c3 = st.columns(3)
    
    with m1_c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="stMetricLabel">Current XAU/USD Price</div>
                <div class="css-17eq0t5">${current_price:.2f}</div>
            </div>
        """, unsafe_allow_html=True)

    with m1_c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="stMetricLabel">AI Alpha Signal</div>
                <div class="css-17eq0t5" style="color: {status_color};">{signal_emoji} {signal_signal}</div>
                <div style="font-size: 14px; color: #888; margin-top: 5px;">Confidence: {final_score}%</div>
            </div>
        """, unsafe_allow_html=True)

        # Using Streamlit's native metric for the 3rd one to keep it clean
    m1_c3.metric(label="Market Quality Status", value=status_text, delta=f"Risk Modifier: {int(risk_modifier*100)}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 2: Analysis & Risk
    an_col, ri_col = st.columns([1, 1])
    
    with an_col:
        st.markdown("### Confluence Analysis Breakdown 🔎")
        # Styled list for analysis points
        for icon, text, points in reasons:
            st.markdown(f"""
                <div class="analysis-item">
                    <span style="margin-right: 10px;">{icon}</span>
                    <span>{text}</span>
                    <span style="float: right; color: #aaa; font-size: 12px;">{points}</span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### Key Technical Levels")
        lvl_col1, lvl_col2 = st.columns(2)
        lvl_col1.metric("Estimated Support", f"${support_level:.2f}")
        lvl_col2.metric("Estimated Resistance", f"${resistance_level:.2f}")

    with ri_col:
        st.markdown(f"<h3 style='color: {status_color} !important;'>🛡️ Position Sizing & Risk Plan</h3>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown(f"<div style='background-color: rgba(46, 204, 113, 0.1); padding: 15px; border-radius: 10px; border: 1px solid #27ae60;'>", unsafe_allow_html=True)
            st.markdown(f"**Signal Quality:** <span style='color:{status_color}; font-weight:bold;'>{status_text}</span>", unsafe_allow_html=True)
            st.markdown(f"**Recommended Lot Size:** <span style='font-size: 24px; font-weight:bold; color:white;'> {lot_size_recommended} </span> Lots", unsafe_allow_html=True)
            st.caption(f"Calculated using {base_risk_pct}% base risk profile, applying {int(risk_modifier*100)}% multiplier based on {final_score}% confidence.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.write(f"**Max Capital at Risk:** ${effective_risk:.2f}")
            st.write(f"**SL used in calc:** {stop_loss_pips} Points")
            st.write(f"**Current RSI(14):** {current_rsi:.1f}")

    # --- CHART SECTION ---
    st.markdown("---")
    st.subheader("📉 XAU/USD Price Trend & Key MAs")
    chart_data = df[['Close', 'EMA_50', 'EMA_200']].tail(96) # Show last 4 days of hourly data
    st.line_chart(chart_data, height=350, use_container_width=True)
