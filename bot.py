import pandas as pd
import yfinance as yf
import requests

# --------- بيانات بوت تليجرام ---------
TELEGRAM_TOKEN = "8864121301:AAH1phUuns-xr0YZ1z4gQI7Jm6oGXxUIFc"
TELEGRAM_CHAT_ID = "1232173822"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        print("Telegram response status:", response.status_code)
        print("Telegram response body:", response.text)
    except Exception as e:
        print("Error sending message:", e)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def run_egx_scan():
    print("Starting EGX scan...")
    stocks = ["COMI.CA", "CIEB.CA", "ABUK.CA", "MFPC.CA", "FWRY.CA", "TMGH.CA"]
    
    results_message = "تقرير فحص البورصة المصرية (EGX)\n\n"
    success_count = 0

    for stock in stocks:
        try:
            print(f"Checking {stock}...")
            data = yf.download(stock, period="2mo", interval="1d", progress=False)
            
            if data.empty or len(data) < 25:
                continue
                
            close_prices = data['Close']
            if isinstance(close_prices, pd.DataFrame):
                close_prices = close_prices.iloc[:, 0]
                
            ema20 = close_prices.ewm(span=20, adjust=False).mean()
            rsi14 = calculate_rsi(close_prices, 14)
            
            last_close = float(close_prices.iloc[-1])
            last_ema20 = float(ema20.iloc[-1])
            last_rsi = float(rsi14.iloc[-1])
            
            status = "عرضي / مترقب"
            if last_close > last_ema20 and last_rsi > 50:
                status = "إشارة إيجابية صعود"
            elif last_close < last_ema20 and last_rsi < 45:
                status = "إشارة سلبية حذر"

            results_message += f"السهم: {stock}\n"
            results_message += f"السعر: {last_close:.2f}\n"
            results_message += f"EMA20: {last_ema20:.2f}\n"
            results_message += f"RSI: {last_rsi:.1f}\n"
            results_message += f"الحالة: {status}\n"
            results_message += "-------------------\n"
            success_count += 1
            
        except Exception as e:
            print(f"Error with {stock}: {e}")

    if success_count > 0:
        send_telegram_message(results_message)
    else:
        send_telegram_message("لم يتم رصد بيانات كافية اليوم.")
        
    print("Finished.")

if __name__ == "__main__":
    run_egx_scan()
