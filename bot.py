import pandas as pd
import yfinance as yf
import requests
from datetime import datetime

# --------- بيانات بوت تليجرام ---------
TELEGRAM_TOKEN = "8864121301:AAH1phUuns-xr0YZ1z4g"
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

# --------- دالة الفحص الأساسية ---------
def run_egx_scan():
    print("Starting EGX market scan...")
    
    # قائمة الأسهم اللي بتحلل وتتابعها
    stocks = ["COMI.CA", "CIEB.CA", "ABUK.CA", "MFPC.CA", "EDIT.CA", "FWRY.CA", "TMGH.CA"]
    
    results_message = "📊 *تقرير فحص البورصة المصرية (EGX)*\n\n"
    active_signals = 0

    for stock in stocks:
        try:
            print(f"Checking {stock}...")
            data = yf.download(stock, period="1mo", interval="1d", progress=False)
            
            if data.empty or len(data) < 15:
                continue
                
            # حساب المؤشرات ببساطة بدون الحاجة لـ pandas_ta المعقدة
            close_prices = data['Close']
            if isinstance(close_prices, pd.DataFrame):
                close_prices = close_prices.iloc[:, 0]
                
            ema20 = close_prices.ewm(span=20, adjust=False).mean()
            last_close = float(close_prices.iloc[-1])
            last_ema20 = float(ema20.iloc[-1])
            
            results_message += f"🔹 *{stock}*:\n"
            results_message += f"  - السعر الحالي: {last_close:.2f}\n"
            results_message += f"  - المتوسط (EMA20): {last_ema20:.2f}\n\n"
            active_signals += 1
            
        except Exception as e:
            print(f"Error processing {stock}: {e}")

    if active_signals > 0:
        send_telegram_message(results_message)
    else:
        send_telegram_message("⚠️ لم يتم رصد إشارات كافية اليوم لجلسة البورصة.")
        
    print("Scan finished successfully.")

if __name__ == "__main__":
    run_egx_scan()
