import pandas as pd
import ta
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta
import concurrent.futures

@st.cache_data(ttl=14400, show_spinner=False)
def fetch_stock_data(symbol):
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if df.empty or len(df) < 50:
            return None, symbol
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df, symbol
    except Exception as e:
        return None, symbol

def analyze_stock(df, symbol):
    try:
        df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
        df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
        df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
        
        macd_obj = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
        df['MACD_line'] = macd_obj.macd()
        df['MACD_signal'] = macd_obj.macd_signal()

        adx_obj = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
        df['ADX'] = adx_obj.adx()

        df['Vol_Avg_20'] = df['Volume'].rolling(window=20).mean()
        df['High_52W'] = df['High'].rolling(window=252, min_periods=50).max()

        latest = df.iloc[-1]
        score = 0
        reasons = []

        if pd.notna(latest['EMA_200']) and latest['Close'] > latest['EMA_200']:
            score += 2
            reasons.append("Price is above 200 EMA")
            
        if pd.notna(latest['EMA_50']) and latest['Close'] > latest['EMA_50']:
            score += 2
            reasons.append("Price is above 50 EMA")

        rsi_val = latest['RSI_14']
        if pd.notna(rsi_val) and 50 <= rsi_val <= 70:
            score += 2
            reasons.append(f"RSI is {rsi_val:.2f} (Between 50 and 70)")
            
        crossover = False
        if pd.notna(latest['MACD_line']) and pd.notna(latest['MACD_signal']):
            for i in range(-3, 0):
                if df.iloc[i-1]['MACD_line'] <= df.iloc[i-1]['MACD_signal'] and \
                   df.iloc[i]['MACD_line'] > df.iloc[i]['MACD_signal']:
                    crossover = True
                    break
        if crossover:
            score += 2
            reasons.append("Fresh MACD bullish crossover in last 3 days")

        vol_ratio = latest['Volume'] / latest['Vol_Avg_20'] if pd.notna(latest['Vol_Avg_20']) and latest['Vol_Avg_20'] > 0 else 0
        if pd.notna(vol_ratio) and vol_ratio >= 1.5:
            score += 3
            reasons.append(f"Volume surge: {vol_ratio:.2f}x of 20-day average")

        if pd.notna(latest['High_52W']):
            distance_to_high = (latest['High_52W'] - latest['Close']) / latest['High_52W']
            if distance_to_high <= 0.15:
                score += 1
                reasons.append("Price is within 15% of 52-week high")

        if len(df) > 10:
            past_candle = df.iloc[-11]
            if latest['High'] > past_candle['High'] and latest['Low'] > past_candle['Low']:
                score += 2
                reasons.append("Structure intact: Higher High & Higher Low vs 10 days ago")

        adx_val = latest['ADX']
        if pd.notna(adx_val) and adx_val > 20:
            score += 2
            reasons.append(f"ADX is {adx_val:.2f} (Strong trend > 20)")

        entry_price = latest['Close']
        stop_loss = df['Low'].iloc[-5:].min()
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
