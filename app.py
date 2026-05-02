import streamlit as st
import pandas as pd
from datetime import datetime
import concurrent.futures

# Import our custom modules
from stocks_list import NIFTY_STOCKS
from screener import fetch_stock_data, analyze_stock

# Set page configuration for wide layout (better for tables and mobile)
st.set_page_config(page_title="Swing Trading Screener", layout="wide")

# --- APP HEADER ---
st.title("📈 Swing Trading Screener — Nifty 500")
st.markdown("""
This app screens top Nifty stocks for swing trading opportunities based on Trend, Momentum, Volume, and Price Action.
""")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Screener Settings")

min_score = st.sidebar.slider("Minimum Score Filter (Max 16)", min_value=10, max_value=16, value=12, step=1)
rsi_range = st.sidebar.slider("RSI Range Filter", min_value=40, max_value=80, value=(50, 70))
min_vol_mult = st.sidebar.slider("Min Volume Multiplier", min_value=1.0, max_value=3.0, value=1.5, step=0.1)
max_risk_pct = st.sidebar.slider("Max Risk % Allowed", min_value=1, max_value=8, value=5, step=1)

run_button = st.sidebar.button("🚀 Run Screener", type="primary")

# --- MAIN LOGIC ---
if run_button:
    # 1. Initialize Progress Tracking
    progress_bar = st.progress(0, text="Starting stock scan...")
    
    passed_stocks = []
    total_symbols = len(NIFTY_STOCKS)
    
    # 2. Parallel Processing
    # We use ThreadPoolExecutor to fetch and process stocks in parallel for speed.
    completed_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all fetching tasks
        future_to_symbol = {executor.submit(fetch_stock_data, sym): sym for sym in NIFTY_STOCKS}
        
        for future in concurrent.futures.as_completed(future_to_symbol):
            df, sym = future.result()
            completed_count += 1
            
            # Update progress bar
            progress_bar.progress(completed_count / total_symbols, text=f"Scanning {sym} ({completed_count}/{total_symbols})...")
            
            if df is not None:
                # Analyze the stock
                analysis = analyze_stock(df, sym)
                
                # Apply user-selected filters
                if analysis is not None:
                    if (analysis['Score'] >= min_score and 
                        analysis['Risk %'] <= max_risk_pct and 
                        analysis['Vol Ratio'] >= min_vol_mult and
                        rsi_range[0] <= analysis['RSI'] <= rsi_range[1]):
                        
                        passed_stocks.append(analysis)

    progress_bar.empty() # Clear the progress bar when done
    
    # 3. Sort Results
    passed_stocks.sort(key=lambda x: x['Score'], reverse=True)
    
    # 4. Display Metrics
    st.subheader("📊 Scan Results")
    col1, col2, col3 = st.columns(3)
    col1.metric("Stocks Scanned", total_symbols)
    col2.metric("Stocks Passed", len(passed_stocks))
    col3.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    if len(passed_stocks) > 0:
        # 5. Display Table
        df_results = pd.DataFrame(passed_stocks)
        
        # We don't want to display the "Reasons" list directly in the table
        display_cols = ['Symbol', 'Current Price', 'Score', 'RSI', 'Vol Ratio', 'ADX', 
                        'Entry Price', 'Stop Loss', 'Target Price', 'Risk %', 'Reward %', 'RR Ratio']
        
        df_display = df_results[display_cols]
        
        # Function to color code scores
        def highlight_score(val):
            if isinstance(val, int):
                if val >= 14:
                    return 'background-color: rgba(0, 255, 0, 0.2)' # Green
                elif val >= 12:
                    return 'background-color: rgba(255, 255, 0, 0.2)' # Yellow
            return ''
            
        styled_df = df_display.style.map(highlight_score, subset=['Score'])
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # 6. CSV Download Button
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name=f"swing_screener_results_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
        
        # 7. "Why This Stock?" Expanders
        st.subheader("💡 Why This Stock?")
        for stock in passed_stocks:
            with st.expander(f"{stock['Symbol']} — Score: {stock['Score']}/16"):
                for reason in stock['Reasons']:
                    st.markdown(f"- ✅ {reason}")
                
    else:
        st.warning("No stocks passed the criteria. Try relaxing the filters in the sidebar.")
else:
    st.info("👈 Adjust your settings in the sidebar and click 'Run Screener' to start.")

# --- FOOTER DISCLAIMER ---
st.markdown("---")
st.caption("⚠️ **Disclaimer**: This app is for educational purposes only. It does not constitute financial advice. Not SEBI registered investment advice.")
