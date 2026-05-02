import streamlit as st
import pandas as pd
from datetime import datetime
import concurrent.futures

# Import our custom modules
from stocks_list import NIFTY_STOCKS
from screener import fetch_stock_data, analyze_stock, analyze_long_term_stock

# Set page configuration for wide layout
st.set_page_config(page_title="Swing & Long Term Screener", layout="wide")

# --- PREMIUM UI CSS INJECTION ---
st.markdown("""
<style>
    /* Global Font and Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Gradient Title */
    h1 {
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        padding-bottom: 10px;
    }

    /* Glassmorphism Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #4ECDC4 !important;
        font-weight: 800;
    }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
    }

    /* Buttons Styling */
    div.stButton > button {
        background: linear-gradient(90deg, #4ECDC4, #556270);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #556270, #4ECDC4);
        box-shadow: 0 5px 15px rgba(78, 205, 196, 0.4);
        border-color: transparent;
        color: white;
    }

    /* Expander Styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
    }
    
    /* Tabs Styling */
    [data-baseweb="tab"] {
        font-weight: 600;
    }
    [data-baseweb="tab-list"] {
        gap: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- APP HEADER ---
st.title("📈 Pro Screener: Nifty 500")
st.markdown("""
<div style="font-size:1.1rem; color:#A0AEC0; margin-bottom: 20px;">
An advanced technical screener to identify high-probability Swing Trading setups and solid Long-Term Investment opportunities.
</div>
""", unsafe_allow_html=True)

# --- MAIN TABS ---
tab1, tab2 = st.tabs(["⚡ Swing Trading", "🏦 Long Term Investing"])

# ==========================================
# TAB 1: SWING TRADING
# ==========================================
with tab1:
    st.subheader("Swing Trading Filters")
    # Filters in columns for a dashboard feel
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        min_score = st.slider("Min Score (Max 16)", 10, 16, 12, 1, key='swing_score')
    with col_s2:
        rsi_range = st.slider("RSI Range", 40, 80, (50, 70), key='swing_rsi')
    with col_s3:
        min_vol_mult = st.slider("Min Volume Mult.", 1.0, 3.0, 1.5, 0.1, key='swing_vol')
    with col_s4:
        max_risk_pct = st.slider("Max Risk %", 1, 8, 5, 1, key='swing_risk')

    run_swing = st.button("🚀 Run Swing Screener", use_container_width=True)

    if run_swing:
        progress_bar = st.progress(0, text="Starting Swing Scan...")
        passed_stocks = []
        total_symbols = len(NIFTY_STOCKS)
        completed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(fetch_stock_data, sym): sym for sym in NIFTY_STOCKS}
            for future in concurrent.futures.as_completed(future_to_symbol):
                df, sym = future.result()
                completed_count += 1
                progress_bar.progress(completed_count / total_symbols, text=f"Scanning {sym} ({completed_count}/{total_symbols})...")
                
                if df is not None:
                    analysis = analyze_stock(df, sym)
                    if analysis is not None:
                        if (analysis['Score'] >= min_score and 
                            analysis['Risk %'] <= max_risk_pct and 
                            analysis['Vol Ratio'] >= min_vol_mult and
                            rsi_range[0] <= analysis['RSI'] <= rsi_range[1]):
                            passed_stocks.append(analysis)

        progress_bar.empty()
        passed_stocks.sort(key=lambda x: x['Score'], reverse=True)
        
        st.markdown("### 📊 Scan Results")
        m1, m2, m3 = st.columns(3)
        m1.metric("Stocks Scanned", total_symbols)
        m2.metric("Stocks Passed", len(passed_stocks))
        m3.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))
        
        if len(passed_stocks) > 0:
            df_results = pd.DataFrame(passed_stocks)
            display_cols = ['Symbol', 'Current Price', 'Score', 'RSI', 'Vol Ratio', 'ADX', 
                            'Entry Price', 'Stop Loss', 'Target Price', 'Risk %', 'Reward %', 'RR Ratio']
            df_display = df_results[display_cols]
            
            def highlight_score(val):
                if isinstance(val, int):
                    if val >= 14: return 'background-color: rgba(78, 205, 196, 0.2)'
                    elif val >= 12: return 'background-color: rgba(255, 206, 86, 0.2)'
                return ''
                
            styled_df = df_display.style.map(highlight_score, subset=['Score'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            st.markdown("### 💡 Why This Stock?")
            for stock in passed_stocks:
                with st.expander(f"**{stock['Symbol']}** — Score: {stock['Score']}/16"):
                    for reason in stock['Reasons']:
                        st.markdown(f"- ✅ {reason}")
        else:
            st.warning("No stocks passed the criteria. Try relaxing the filters.")


# ==========================================
# TAB 2: LONG TERM INVESTING
# ==========================================
with tab2:
    st.subheader("Long Term Investing Filters")
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l1:
        min_lt_score = st.slider("Min LT Score (Max 10)", 5, 10, 7, 1, key='lt_score')
    with col_l2:
        max_dist_high = st.slider("Max Distance from 52W High %", 5, 30, 20, 1, key='lt_dist')
    with col_l3:
        lt_rsi_range = st.slider("RSI Range", 30, 80, (45, 65), key='lt_rsi')

    run_longterm = st.button("🏦 Run Long Term Screener", use_container_width=True)

    if run_longterm:
        progress_bar_lt = st.progress(0, text="Starting Long Term Scan...")
        passed_lt_stocks = []
        total_symbols = len(NIFTY_STOCKS)
        completed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(fetch_stock_data, sym): sym for sym in NIFTY_STOCKS}
            for future in concurrent.futures.as_completed(future_to_symbol):
                df, sym = future.result()
                completed_count += 1
                progress_bar_lt.progress(completed_count / total_symbols, text=f"Scanning {sym} ({completed_count}/{total_symbols})...")
                
                if df is not None:
                    analysis = analyze_long_term_stock(df, sym)
                    if analysis is not None:
                        if (analysis['Score'] >= min_lt_score and 
                            analysis['Dist from High %'] <= max_dist_high and 
                            lt_rsi_range[0] <= analysis['RSI'] <= lt_rsi_range[1]):
                            passed_lt_stocks.append(analysis)

        progress_bar_lt.empty()
        passed_lt_stocks.sort(key=lambda x: x['Score'], reverse=True)
        
        st.markdown("### 📊 Scan Results")
        m1, m2, m3 = st.columns(3)
        m1.metric("Stocks Scanned", total_symbols)
        m2.metric("Stocks Passed", len(passed_lt_stocks))
        m3.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))
        
        if len(passed_lt_stocks) > 0:
            df_results_lt = pd.DataFrame(passed_lt_stocks)
            display_cols_lt = ['Symbol', 'Current Price', 'Score', 'RSI', 'Dist from High %', 
                            'Entry Price', 'Stop Loss', 'Target Price', 'Risk %', 'Reward %', 'RR Ratio']
            df_display_lt = df_results_lt[display_cols_lt]
            
            def highlight_score_lt(val):
                if isinstance(val, int):
                    if val >= 8: return 'background-color: rgba(78, 205, 196, 0.2)'
                    elif val >= 6: return 'background-color: rgba(255, 206, 86, 0.2)'
                return ''
                
            styled_df_lt = df_display_lt.style.map(highlight_score_lt, subset=['Score'])
            st.dataframe(styled_df_lt, use_container_width=True, hide_index=True)
            
            st.markdown("### 💡 Why This Stock?")
            for stock in passed_lt_stocks:
                with st.expander(f"**{stock['Symbol']}** — Score: {stock['Score']}/10"):
                    for reason in stock['Reasons']:
                        st.markdown(f"- ✅ {reason}")
        else:
            st.warning("No stocks passed the criteria. Try relaxing the filters.")


# --- FOOTER DISCLAIMER ---
st.markdown("---")
st.caption("⚠️ **Disclaimer**: This app is for educational purposes only. It does not constitute financial advice. Not SEBI registered investment advice.")
