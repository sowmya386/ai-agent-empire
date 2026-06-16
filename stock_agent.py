# stock_agent.py — pip install nsepython yfinance pandas-ta requests
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass
import yfinance as yf
import pandas_ta_classic as ta
import requests
import os
import schedule
import time

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # Free: @BotFather on Telegram
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

WATCHLIST = ['HDFCBANK.NS', 'RELIANCE.NS', 'INFY.NS', 'TCS.NS', 'ICICIBANK.NS']

def send_notification(title, msg, click_url=None):
    # Free push notification service — no sign-up or API keys required
    topic = os.environ.get('NTFY_TOPIC', 'sowmya_stock_alerts_2026')
    url = f"https://ntfy.sh/{topic}"
    try:
        import base64
        title_enc = "=?utf-8?B?" + base64.b64encode(title.encode('utf-8')).decode('utf-8') + "?="
        headers = {
            "Title": title_enc,
            "Priority": "high",
            "Tags": "chart_with_upwards_trend,moneybag"
        }
        if click_url:
            headers["Click"] = click_url
            
        # Strip simple HTML tags for ntfy app compatibility
        import re
        clean_text = re.sub(r'<[^>]+>', '', msg)
        
        requests.post(url, data=clean_text.encode('utf-8'), headers=headers)
        print(f"Push notification sent via ntfy.sh to channel: {topic}")
    except Exception as e:
        print(f"Failed to send push notification: {e}")

def analyse_stock(symbol):
    # Get free historical data
    df = yf.download(symbol, period='3mo', interval='1d', progress=False)
    if df.empty:
        print(f"No data retrieved for {symbol}")
        return
    if df.columns.nlevels > 1:
        df.columns = df.columns.droplevel(1)
    df = df.dropna(subset=['Close'])
    # Calculate free technical indicators
    df.ta.rsi(append=True)
    df.ta.macd(append=True)
    df.ta.sma(20, append=True)
    df.ta.sma(50, append=True)
    latest = df.iloc[-1]
    
    # Clean indicator parsing due to pandas multi-indexing from yfinance
    rsi_col = [col for col in df.columns if 'RSI' in col]
    rsi = latest[rsi_col[0]] if rsi_col else 50
    
    close_col = [col for col in df.columns if 'Close' in col]
    price = latest[close_col[0]] if close_col else 0.0
    
    macd_col = [col for col in df.columns if 'MACD_' in col and 's_' not in col and 'h_' not in col]
    macd = latest[macd_col[0]] if macd_col else 0.0
    
    macds_col = [col for col in df.columns if 'MACDs_' in col]
    signal_line = latest[macds_col[0]] if macds_col else 0.0

    # Handle series elements
    if hasattr(rsi, 'iloc'): rsi = rsi.iloc[0]
    if hasattr(price, 'iloc'): price = price.iloc[0]
    if hasattr(macd, 'iloc'): macd = macd.iloc[0]
    if hasattr(signal_line, 'iloc'): signal_line = signal_line.iloc[0]

    # Generate signal
    signal = "HOLD"
    reason = ""
    if rsi < 30:
        signal = "🟢 BUY"
        reason = f"RSI oversold at {rsi:.1f}"
    elif rsi > 70:
        signal = "🔴 SELL"
        reason = f"RSI overbought at {rsi:.1f}"
    elif macd > signal_line and macd > 0:
        signal = "🟢 BUY"
        reason = "MACD bullish crossover"
        
    print(f"{symbol}: Price=Rs.{price:.2f}, RSI={rsi:.1f}, MACD={macd:.3f}, Signal={signal}")
    
    # Save signal status to local SQLite database for PWA dashboard
    try:
        import sqlite3
        import math
        conn = sqlite3.connect('agent_empire.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS stock_signals (
            symbol TEXT PRIMARY KEY,
            price REAL,
            rsi REAL,
            macd REAL,
            signal TEXT,
            updated_at TEXT)''')
        
        def clean_val(v):
            if v is None: return None
            try:
                if math.isnan(float(v)): return None
                return float(v)
            except:
                return None
                
        db_price = clean_val(price)
        db_rsi = clean_val(rsi)
        db_macd = clean_val(macd)
        
        conn.execute('''INSERT OR REPLACE INTO stock_signals (symbol, price, rsi, macd, signal, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?)''', (symbol, db_price, db_rsi, db_macd, signal, time.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
    except Exception as db_err:
        print(f"Failed to write database signal for {symbol}: {db_err}")
    
    if signal != "HOLD":
        # Groww deep link — opens Groww app on phone
        groww_link = f"https://groww.in/stocks/{symbol.replace('.NS','').lower()}"
        msg = f"""🟢 {signal}: {symbol}
Price: ₹{price:.2f}
RSI: {rsi:.1f}
Reason: {reason}
⚠️ Paper trade only — verify before buying"""
        send_notification(f"Stock Alert: {signal} {symbol}", msg, groww_link)

def scan_all():
    watchlist = WATCHLIST
    try:
        import sqlite3
        conn = sqlite3.connect('agent_empire.db')
        cursor = conn.cursor()
        cursor.execute("SELECT symbol FROM watchlist")
        rows = cursor.fetchall()
        if rows:
            watchlist = [r[0] for r in rows]
        conn.close()
    except Exception as db_err:
        print(f"Could not load watchlist from SQLite, using default: {db_err}")

    print(f"Scanning {len(watchlist)} stocks...")
    for sym in watchlist:
        try:
            analyse_stock(sym)
        except Exception as e:
            print(f"Error scanning {sym}: {e}")

if __name__ == "__main__":
    scan_all()