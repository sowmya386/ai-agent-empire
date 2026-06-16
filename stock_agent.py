# stock_agent.py — pip install nsepython yfinance pandas-ta requests
import yfinance as yf
import pandas_ta as ta
import requests
import os
import schedule
import time

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # Free: @BotFather on Telegram
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

WATCHLIST = ['HDFCBANK.NS', 'RELIANCE.NS', 'INFY.NS', 'TCS.NS', 'ICICIBANK.NS']

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n--- Telegram Notification (Not Configured) ---")
        print(msg)
        print("--------------------------------------------\n")
        return
    # Free Telegram Bot API
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'})
        print("Telegram alert sent.")
    except Exception as e:
        print(f"Failed to send telegram message: {e}")

def analyse_stock(symbol):
    # Get free historical data
    df = yf.download(symbol, period='3mo', interval='1d', progress=False)
    if df.empty:
        print(f"No data retrieved for {symbol}")
        return
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
        
    print(f"{symbol}: Price=₹{price:.2f}, RSI={rsi:.1f}, MACD={macd:.3f}, Signal={signal}")
    
    if signal != "HOLD":
        # Groww deep link — opens Groww app on phone
        groww_link = f"https://groww.in/stocks/{symbol.replace('.NS','').lower()}"
        msg = f"""<b>{signal}: {symbol}</b>
Price: ₹{price:.2f}
RSI: {rsi:.1f}
Reason: {reason}
<a href="{groww_link}">Open in Groww</a>
⚠️ Paper trade only — verify before buying"""
        send_telegram(msg)

def scan_all():
    print(f"Scanning {len(WATCHLIST)} stocks...")
    for sym in WATCHLIST:
        try:
            analyse_stock(sym)
        except Exception as e:
            print(f"Error scanning {sym}: {e}")

if __name__ == "__main__":
    scan_all()