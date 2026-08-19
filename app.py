import streamlit as st
import pandas as pd
import yfinance as yf

# --- PAGE CONFIGURATION & COMPACT SPACING ---
st.set_page_config(
    page_title="XAU/USD Alpha Confluence",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
st.markdown("## 🪙 XAU/USD Alpha Confluence & Risk Hub")
st.markdown("---")

# --- SIDEBAR: RISK SETTINGS ---
st.sidebar.header("Risk Settings ⚙️")
account_balance = st.sidebar.number_input("Account Balance ($)", min_value=10.0, max_value=1000000.0, value=1000.0, step=100.0)
base_risk_pct = st.sidebar.slider("Base Risk Per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
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
    # --- CALCULATIONS ---
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

    # --- SIGNAL & AUTO RISK LOGIC ---
    buy_score = 0
    sell_score = 0
    reasons = []

    if current_price > ema_50 and ema_50 > ema_200:
        buy_score += 1
        reasons.append(("✅", "Bullish Trend (Above MAs)"))
    elif current_price < ema_50 and ema_50 < ema_200:
        sell_score += 1
        reasons.append(("🔻", "Bearish Trend (Below MAs)"))
    else:
        reasons.append(("⚠️", "Choppy Trend (Neutral MAs)"))

    if current_rsi < 35:
        buy_score += 1
        reasons.append(("✅", f"RSI Oversold ({current_rsi:.1f})"))
    elif current_rsi > 65:
        sell_score += 1
        reasons.append(("🔻", f"RSI Overbought ({current_rsi:.1f})"))
    else:
        reasons.append(("ℹ️", f"RSI Neutral ({current_rsi:.1f})"))

    dist_to_support = abs(current_price - support_level)
    dist_to_resistance = abs(current_price - resistance_level)
    
    if dist_to_support < (current_price * 0.003):
        buy_score += 1
        reasons.append(("✅", f"At Support Zone (${support_level:.2f})"))
    elif dist_to_resistance < (current_price * 0.003):
        sell_score += 1
        reasons.append(("🔻", f"At Resistance Zone (${resistance_level:.2f})"))
    else:
        reasons.append(("ℹ️", "Price Mid-Range"))

    # Auto Risk Adjustment based on setup strength
    if buy_score >= 2:
        signal_text = "BUY"
        signal_color = "#16a34a"
        risk_modifier = 1.5  # Safe & Strong setup -> Increases lot size automatically
        safe_tp = current_price + (stop_loss_pips * 1.5)
        risky_tp = current_price + (stop_loss_pips * 3.0)
    elif sell_score >= 2:
        signal_text = "SELL"
        signal_color = "#dc2626"
        risk_modifier = 1.5  # Safe & Strong setup -> Increases lot size automatically
        safe_tp = current_price - (stop_loss_pips * 1.5)
        risky_tp = current_price - (stop_loss_pips * 3.0)
    else:
        signal_text = "NO BUY / NO SELL"
        signal_color = "#ca8a04"
        risk_modifier = 0.2  # Risky/Choppy -> Automatically reduces risk/lot size
        safe_tp = 0.0
        risky_tp = 0.0

    # --- DYNAMIC POSITION SIZING ---
    risk_dollar_amount = account_balance * (base_risk_pct / 100.0)
    effective_risk = risk_dollar_amount * risk_modifier
    lot_size_recommended = round(effective_risk / (stop_loss_pips * 100.0), 2)
    if lot_size_recommended < 0.01: lot_size_recommended = 0.01

    # --- COMPACT UI DISPLAY ---
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
                <div class="metric-label">Action Signal</div>
                <div class="metric-value" style="color: {signal_color};">{signal_text}</div>
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

    # --- DETAILS SECTION ---
    col_left, col_right = st.columns([1.1, 0.9])
    
    with col_left:
        st.markdown("### Technical Breakdown")
        for icon, text in reasons:
            st.markdown(f"""
                <div class="analysis-item">
                    <span>{icon} <strong>{text}</strong></span>
                </div>
            """, unsafe_allow_html=True)
        
        l_col1, l_col2 = st.columns(2)
        l_col1.caption(f"**Support:** ${support_level:.2f}")
        l_col2.caption(f"**Resistance:** ${resistance_level:.2f}")

    with col_right:
        st.markdown("### Auto Risk & TP Overview")
        st.markdown(f"""
            <div style="background-color: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 13px;">
                <p style="margin: 3px 0;"><strong>Balance:</strong> ${account_balance:.2f}</p>
                <p style="margin: 3px 0;"><strong>Effective Risk Amount:</strong> ${effective_risk:.2f}</p>
                <p style="margin: 3px 0;"><strong>Safe TP (1.5R):</strong> ${safe_tp:.2f}</p>
                <p style="margin: 3px 0;"><strong>Risky TP (3R):</strong> ${risky_tp:.2f}</p>
            </div>
        """, unsafe_allow_html=True)

    # --- COMPACT CHART ---
    st.markdown("---")
    chart_df = df[['Close', 'EMA_50', 'EMA_200']].tail(72)
    st.line_chart(chart_df, height=250, use_container_width=True)
