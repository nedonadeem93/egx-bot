import pandas as pd
import yfinance as yf
import requests
from datetime import datetime

# --------- بيانات بوت تليجرام ---------
TELEGRAM_TOKEN = "8864121301:AAH1phUuns-xr0YZ1z4gQI7Jm6oGXxUIFc"
TELEGRAM_CHAT_ID = "1232173822"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        print("Telegram response:", response.status_code)
    except Exception as e:
        print("Error sending message:", e)

# --------- دالة حساب مؤشر RSI يدوياً وبدقة ---------
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --------- دالة الفحص الفني المتقدمة ---------
def run_egx_scan():
    print("Starting advanced EGX market scan...")
    
    # قائمة الأسهم 
    stocks = ["COMI.CA", "CIEB.CA", "ABUK.CA", "MFPC.CA", "EDIT.CA", "FWRY.CA", "TMGH.CA"]
    
    results_message = "📊 *التقرير الفني المتقدم للبورصة المصرية (EGX)*\n\n"
    active_signals = 0

    for stock in stocks:
        try:
            print(f"Analyzing {stock}...")
            data = yf.download(stock, period="2mo", interval="1d", progress=False)
            
            if data.empty or len(data) < 25:
                continue
                
            close_prices = data['Close']
            if isinstance(close_prices, pd.DataFrame):
                close_prices = close_prices.iloc[:, 0]
                
            volume = data['Volume']
            if isinstance(volume, pd.DataFrame):
                volume = volume.iloc[:, 0]

            # حساب المؤشرات الفنية
            ema20 = close_prices.ewm(span=20, adjust=False).mean()
            ema50 = close_prices.ewm(span=50, adjust=False).mean()
            rsi14 = calculate_rsi(close_prices, 14)
            
            last_close = float(close_prices.iloc[-1])
            last_ema20 = float(ema20.iloc[-1])
            last_ema50 = float(ema50.iloc[-1])
            last_rsi = float(rsi14.iloc[-1])
            last_vol = float(volume.iloc[-1])
            
            # تحديد الإشارة الفنية
            signal_status = "مترقب / عُرضي ⚖️"
            if last_close > last_ema20 and last_rsi > 50:
                signal_status = "إشارة إيجابية / صعود 🟢"
            elif last_close < last_ema20 and last_rsi < 45:
                signal_status = "إشارة سلبية / حذر 🔴"

            results_message += f"🔹 *{stock}*:\n"
            results_message += f"  - السعر: {last_close:.2f}\n"
            results_message += f"  - EMA20: {last_ema20:.2f} | EMA50: {last_ema50:.2f}\n"
            results_message += f"  - RSI(14): {last_rsi:.1f}\n"
            results_message += f"  - الحالة: *{signal_status}*\n\n"
            active_signals += 1
            
        except Exception as e:
            print(f"Error processing {stock}: {e}")

    if active_signals > 0:
        send_telegram_message(results_message)
    else:
        send_telegram_message("⚠️ لم يتم رصد بيانات كافية للتحليل اليوم.")
        
    print("Advanced scan finished successfully.")

if __name__ == "__main__":
    run_egx_scan()
