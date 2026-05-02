import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta
import concurrent.futures

@st.cache_data(ttl=14400, show_spinner=False)
def fetch_stock_data(symbol):
    """
    Fetches 1 year of daily data for a given symbol using yfinance.
    Cached for 4 hours to prevent repeated downloads.
    """
    try:
        # Download 1 year of daily data
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if df.empty or len(df) < 50:
            return None, symbol
        
        # Flatten MultiIndex columns if yfinance returns them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df, symbol
    except Exception as e:
        return None, symbol

def analyze_stock(df, symbol):
    """
    Analyzes the stock data based on the defined criteria and returns a dictionary 
    with the calculated indicators and scores.
    """
    try:
        # Calculate Technical Indicators using pandas-ta
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['RSI_14'] = ta.rsi(df['Close'], length=14)
        
        # MACD
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            df = pd.concat([df, macd], axis=1)
            macd_line_col = [c for c in macd.columns if c.startswith('MACD_')][0]
            signal_line_col = [c for c in macd.columns if c.startswith('MACDs_')][0]
        else:
            return None # Skip if MACD can't be calculated

        # ADX
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        if adx is not None and not adx.empty:
            df = pd.concat([df, adx], axis=1)
            adx_col = [c for c in adx.columns if c.startswith('ADX_')][0]
        else:
            return None

        # Volume
        df['Vol_Avg_20'] = ta.sma(df['Volume'], length=20)
        
        # 52-Week High
        df['High_52W'] = df['High'].rolling(window=252, min_periods=50).max()

        # Get latest data point
        latest = df.iloc[-1]
        
        # Score calculation
        score = 0
        reasons = []

        # Criteria 1 - Trend Filter (Max +4)
        if pd.notna(latest['EMA_200']) and latest['Close'] > latest['EMA_200']:
            score += 2
            reasons.append("Price is above 200 EMA")
            
        if pd.notna(latest['EMA_50']) and latest['Close'] > latest['EMA_50']:
            score += 2
            reasons.append("Price is above 50 EMA")

        # Criteria 2 - Momentum Filter (Max +4)
        rsi_val = latest['RSI_14']
        if pd.notna(rsi_val) and 50 <= rsi_val <= 70:
            score += 2
            reasons.append(f"RSI is {rsi_val:.2f} (Between 50 and 70)")
            
        # MACD crossover in last 3 candles
        crossover = False
        if pd.notna(latest[macd_line_col]) and pd.notna(latest[signal_line_col]):
            # Check last 3 rows (including latest)
            for i in range(-3, 0):
                if df.iloc[i-1][macd_line_col] <= df.iloc[i-1][signal_line_col] and \
                   df.iloc[i][macd_line_col] > df.iloc[i][signal_line_col]:
                    crossover = True
                    break
        if crossover:
            score += 2
            reasons.append("Fresh MACD bullish crossover in last 3 days")

        # Criteria 3 - Volume Confirmation (Max +3)
        vol_ratio = latest['Volume'] / latest['Vol_Avg_20'] if pd.notna(latest['Vol_Avg_20']) and latest['Vol_Avg_20'] > 0 else 0
        if pd.notna(vol_ratio) and vol_ratio >= 1.5:
            score += 3
            reasons.append(f"Volume surge: {vol_ratio:.2f}x of 20-day average")

        # Criteria 4 - Price Structure (Max +3)
        if pd.notna(latest['High_52W']):
            distance_to_high = (latest['High_52W'] - latest['Close']) / latest['High_52W']
            if distance_to_high <= 0.15:
                score += 1
                reasons.append("Price is within 15% of 52-week high")

        # Higher High and Higher Low compared to 10 days ago
        if len(df) > 10:
            past_candle = df.iloc[-11]
            if latest['High'] > past_candle['High'] and latest['Low'] > past_candle['Low']:
                score += 2
                reasons.append("Structure intact: Higher High & Higher Low vs 10 days ago")

        # Criteria 5 - ADX Trend Strength (Max +2)
        adx_val = latest[adx_col] if adx_col in latest else 0
        if pd.notna(adx_val) and adx_val > 20:
            score += 2
            reasons.append(f"ADX is {adx_val:.2f} (Strong trend > 20)")

        # Risk-Reward Calculator
        entry_price = latest['Close']
        stop_loss = df['Low'].iloc[-5:].min() # Lowest low of last 5 candles
        risk_amount = entry_price - stop_loss
        
        if risk_amount <= 0:
            return None
            
        target_price = entry_price + (2.5 * risk_amount)
        risk_percent = (risk_amount / entry_price) * 100
        reward_percent = ((target_price - entry_price) / entry_price) * 100

        return {
            'Symbol': symbol.replace('.NS', ''),
            'Current Price': round(entry_price, 2),
            'Score': score,
            'RSI': round(rsi_val, 2) if pd.notna(rsi_val) else 0,
            'Vol Ratio': round(vol_ratio, 2) if pd.notna(vol_ratio) else 0,
            'ADX': round(adx_val, 2) if pd.notna(adx_val) else 0,
            'Entry Price': round(entry_price, 2),
            'Stop Loss': round(stop_loss, 2),
            'Target Price': round(target_price, 2),
            'Risk %': round(risk_percent, 2),
            'Reward %': round(reward_percent, 2),
            'RR Ratio': '1:2.5',
            'Reasons': reasons
        }
    except Exception as e:
        return None
