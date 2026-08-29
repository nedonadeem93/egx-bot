import pandas as pd
import yfinance as yf
import requests
import schedule
import time
from datetime import datetime

# ---------------- بيانات بوت تليجرام ----------------
TELEGRAM_TOKEN = "8864121301:AAH1phUuns-xrOYZ1z4gjQI7Jm6oGXxUIFc"
TELEGRAM_CHAT_ID = "1232173822"

def send_telegram_message(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    payload = dict(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="Markdown"
    )
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Error sending message:", e)

# ---------------- الدالة الأساسية للفحص ----------------
def run_egx_scan():
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    current_time_in_minutes = current_hour * 60 + current_minute
    start_limit = 8 * 60 + 30   # 08:30 AM
    end_limit = 15 * 60         # 03:00 PM
    
    if not (start_limit <= current_time_in_minutes <= end_limit):
        print(f"خارج أوقات العمل الرسمية ({now.strftime('%H:%M')}): تخطي الفحص.")
        return

    print(f"--- Running Hourly EGX Scanner at {now.strftime('%H:%M')} ---")
    
    # 1. فحص الاتجاه العام للمؤشرات
    indices = {
        "^EGX30": "مؤشر EGX 30",
        "^EGX70": "مؤشر EGX 70 EWI",
        "^EGX100": "مؤشر EGX 100 EWI"
    }

    index_status_lines = ["📊 *تقرير حالة المؤشرات الرئيسية (EGX):*"]

    for idx_symbol, idx_name in indices.items():
        try:
            idx_df = yf.download(idx_symbol, period="3mo", interval="1d", progress=False)
            if not idx_df.empty and len(idx_df) >= 50:
                if isinstance(idx_df.columns, pd.MultiIndex):
                    idx_df.columns = idx_df.columns.get_level_values(0)
                
                idx_df['EMA_50'] = ta.ema(idx_df['Close'], length=50)
                last_close = idx_df['Close'].iloc[-1]
                last_ema50 = idx_df['EMA_50'].iloc[-1]
                
                status = "🟢 صاعد (أعلى من EMA 50)" if last_close > last_ema50 else "🔴 تصحيحي/هابط (أدنى من EMA 50)"
                index_status_lines.append(f"• *{idx_name}:* {status}")
        except Exception as e:
            continue

    send_telegram_message("\n".join(index_status_lines))

    # 2. قائمة الأسهم
    watchlist = [
        "COMI.CA", "FWRY.CA", "HRHO.CA", "CIEB.CA", "ADIB.CA", "TMGH.CA", "HELI.CA", 
        "PHDC.CA", "ORAS.CA", "MNHD.CA", "EMFD.CA", "MFPC.CA", "ABUK.CA", "ESRS.CA", 
        "SWDY.CA", "GBCO.CA", "ETEL.CA", "EKHO.CA", "AMOC.CA", "DSCW.CA", "OIH.CA", 
        "ACGC.CA", "EGAL.CA", "ALCN.CA", "RTVC.CA", "ISPH.CA", "CLHO.CA", "RMDA.CA", 
        "PHAR.CA", "RAYA.CA", "EDIT.CA", "JUFO.CA", "DOMT.CA", "EAST.CA", "ORWE.CA", 
        "SKPC.CA", "CCRS.CA", "KIMA.CA", "CANA.CA", "EGBE.CA", "ATQA.CA", "UNIT.CA", 
        "MPRC.CA", "DCHE.CA", "ASCM.CA", "UEGC.CA", "BLCY.CA"
    ]

    names_map = {
        "COMI.CA": "البنك التجاري الدولي", "FWRY.CA": "فوري", "HRHO.CA": "هيرميس",
        "CIEB.CA": "كريدي أجريكول", "EGBE.CA": "المصري للفيشة", "ADIB.CA": "مصرف أبوظبي الإسلامي",
        "CANA.CA": "بنك قناة السويس", "TMGH.CA": "طلعت مصطفى", "HELI.CA": "مصر للجديدة للإسكان",
        "PHDC.CA": "بالم هيلز", "ORAS.CA": "أوراسكوم للإنشاء", "MNHD.CA": "مدينة مصر",
        "EMFD.CA": "إعمار مصر", "CCRS.CA": "سيدي كرير", "MFPC.CA": "موبكو",
        "ABUK.CA": "أبو قير للأسمدة", "KIMA.CA": "كيما", "SKPC.CA": "سيدي كرير للبيتروكيماويات",
        "ESRS.CA": "عز حديد", "AMOC.CA": "أموك", "EDIT.CA": "إيديتا",
        "JUFO.CA": "جهينة", "DOMT.CA": "دومتي", "EAST.CA": "الشرقية للدخان",
        "ORWE.CA": "النساجون الشرقيون", "ISPH.CA": "ابن سينا فارما", "CLHO.CA": "كليوباترا",
        "RMDA.CA": "رامدا", "PHAR.CA": "أيبكس فارما", "ETEL.CA": "المصرية للاتصالات",
        "RAYA.CA": "راية", "RTVC.CA": "رمكو", "EKHO.CA": "القابضة المصرية الكويتية",
        "SWDY.CA": "السويدي إليكتريك", "GBCO.CA": "جي بي كورب", "DSCW.CA": "دايس للملابس", 
        "OIH.CA": "أوراسكوم للاستثمار", "ACGC.CA": "العربية لحجيج القطن", "EGAL.CA": "مصر للألومنيوم", 
        "ALCN.CA": "الإسكندرية لتداول البضائع", "ATQA.CA": "مصر الوطنية للصلب - عتاقة",
        "UNIT.CA": "المتحدة للإسكان", "MPRC.CA": "إم إم جروب", "DCHE.CA": "السماد والصناعات الكيماوية",
        "ASCM.CA": "أسكوم", "UEGC.CA": "السباعية للصناعات", "BLCY.CA": "بلتون القابضة"
    }

    signals_found = 0

    for ticker in watchlist:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo", interval="1d")
            
            if df.empty or len(df) < 50:
                continue

            df['EMA_20'] = ta.ema(df['Close'], length=20)
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['CMF'] = ta.cmf(df['High'], df['Low'], df['Close'], df['Volume'], length=20)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

            last = df.iloc[-1]
            
            recent_df = df.tail(6)
            has_weekly_crossover = False
            for i in range(1, len(recent_df)):
                if (recent_df['EMA_20'].iloc[i-1] <= recent_df['EMA_50'].iloc[i-1]) and \
                   (recent_df['EMA_20'].iloc[i] > recent_df['EMA_50'].iloc[i]):
                    has_weekly_crossover = True
                    break
            
            cond_tech = has_weekly_crossover and (last['RSI'] > 50) and (last['CMF'] > 0)
            
            if cond_tech:
                signals_found += 1
                entry_price = round(last['Close'], 2)
                atr_value = last['ATR']
                
                stop_loss = round(entry_price - (1.5 * atr_value), 2)
                take_profit = round(entry_price + (3.0 * atr_value), 2)
                arabic_name = names_map.get(ticker, ticker)
                
                info = stock.info
                eps = info.get('trailingEps', 'N/A')
                pe_ratio = info.get('trailingPE', 'N/A')
                
                is_high_risk = False
                if isinstance(eps, (int, float)) and eps <= 0:
                    is_high_risk = True
                elif eps == 'N/A':
                    is_high_risk = True
                    
                pe_text = str(round(pe_ratio, 2)) if isinstance(pe_ratio, (int, float)) else "غير متاح"
                eps_text = str(round(eps, 2)) if isinstance(eps, (int, float)) else "غير متاح"

                if is_high_risk:
                    lines = [
                        "⚠️ *إشارة مضاربة سريعة (عالية الخطورة)* ⚡",
                        "📈 *السهم:* " + arabic_name + " (`" + ticker + "`)",
                        "----------------------------------",
                        "📌 *سعر الإغلاق:* " + str(entry_price) + " جنيه",
                        "🎯 *الهدف المقترح:* " + str(take_profit) + " جنيه",
                        "🛑 *وقف الخسارة (الالتزام صارم):* " + str(stop_loss) + " جنيه",
                        "----------------------------------",
                        "🔴 *سبب تنبيه الخطورة:* النتائج المالية ضعيفة أو غير متاحة (EPS: " + eps_text + ")",
                        "💡 *توصية المضاربة:* احرص على التداول بحجم كمية صغير والتزام تام بوقف الخسارة."
                    ]
                else:
                    lines = [
                        "🚀 *إشارة استثمارية / اتجاه مؤكد (مخاطرة متوازنة)* 🔥",
                        "📈 *السهم:* " + arabic_name + " (`" + ticker + "`)",
                        "----------------------------------",
                        "📌 *سعر الإغلاق:* " + str(entry_price) + " جنيه",
                        "🎯 *الهدف المقترح:* " + str(take_profit) + " جنيه",
                        "🛑 *وقف الخسارة:* " + str(stop_loss) + " جنيه",
                        "----------------------------------",
                        "🏛️ *التحليل الأساسي:* EPS: " + eps_text + " | P/E: " + pe_text,
                        "📊 *التحليل الفني:* RSI: " + str(round(last['RSI'], 1)) + " | السيولة (CMF) إيجابية"
                    ]
                    
                msg = "\n".join(lines)
                send_telegram_message(msg)
                print("Signal sent for:", ticker)

        except Exception as e:
            continue

    if signals_found == 0:
        print("✅ Scan Complete. No new signals found in this hour.")

    print("✅ EGX Scan Complete. Total Signals:", signals_found)

# ---------------- الجدولة بالساعة ----------------
schedule.every(1).hours.do(run_egx_scan)

print("🤖 بوت التداول مفعل وسيعمل أوتوماتيكياً كل ساعة (من 8:30 صباحاً حتي 3:00 عصراً)...")

while True:
    schedule.run_pending()
    time.sleep(1)
