import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests
import os
from datetime import datetime
import time
from dotenv import load_dotenv

load_dotenv()

# ==================== إعدادات التليجرام ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ خطأ في الإرسال: {e}")

# ==================== تحليل السوق العام ====================
def market_trend():
    """تحديد اتجاه السوق العام"""
    try:
        df = yf.download("^EGX30", period="3mo", interval="1d", progress=False)
        if df.empty:
            return "محايد 🟡"
        
        # تنظيف الأعمدة
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # حساب EMA 50
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        last_close = df['Close'].iloc[-1]
        last_ema = df['EMA_50'].iloc[-1]
        
        # حساب أداء آخر 20 يوم
        performance = ((df['Close'].iloc[-1] / df['Close'].iloc[-20]) - 1) * 100
        
        if last_close > last_ema and performance > 0:
            return "صاعد 🟢"
        elif last_close < last_ema and performance < 0:
            return "هابط 🔴"
        else:
            return "محايد 🟡"
    except:
        return "محايد 🟡"

# ==================== تحليل السهم ====================
def analyze_stock(ticker, name):
    """تحليل سهم واحد وتوليد إشارة الدخول"""
    try:
        # جلب البيانات
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
        
        # تنظيف الأعمدة
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # ====== المؤشرات الفنية ======
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['CMF'] = ta.cmf(df['High'], df['Low'], df['Close'], df['Volume'], length=20)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # ====== مؤشر القوة النسبية للسهم ======
        df['Stock_Performance'] = (df['Close'] / df['Close'].shift(20) - 1) * 100
        
        last = df.iloc[-1]
        
        # ====== الشروط ======
        # 1. تقاطع EMA
        recent = df.tail(6)
        crossover = False
        for i in range(1, len(recent)):
            if (recent['EMA_20'].iloc[i-1] <= recent['EMA_50'].iloc[i-1]) and \
               (recent['EMA_20'].iloc[i] > recent['EMA_50'].iloc[i]):
                crossover = True
                break
        
        # 2. RSI (متوسط)
        rsi_ok = 45 < last['RSI'] < 70
        
        # 3. CMF موجب
        cmf_ok = last['CMF'] > 0
        
        # 4. حجم التداول فوق المتوسط
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
        volume_ok = last['Volume'] > avg_volume * 0.7
        
        # 5. السهم أقوى من السوق
        stock_strong = last['Stock_Performance'] > 0
        
        # ====== المعلومات الأساسية ======
        info = stock.info
        eps = info.get('trailingEps', None)
        pe = info.get('trailingPE', None)
        
        # ====== تقييم المخاطر ======
        is_risky = False
        if eps is None or eps <= 0:
            is_risky = True
        
        # ====== القرار النهائي ======
        if crossover and rsi_ok and cmf_ok and volume_ok and stock_strong:
            entry_price = round(last['Close'], 2)
            atr_value = last['ATR']
            stop_loss = round(entry_price - (1.5 * atr_value), 2)
            take_profit = round(entry_price + (3 * atr_value), 2)
            
            return {
                'signal': True,
                'ticker': ticker,
                'name': name,
                'entry': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'rsi': round(last['RSI'], 1),
                'cmf': round(last['CMF'], 3),
                'atr': atr_value,
                'volume_ratio': round(last['Volume'] / avg_volume, 1),
                'performance': round(last['Stock_Performance'], 1),
                'market_trend': market_trend(),
                'is_risky': is_risky,
                'eps': eps,
                'pe': pe
            }
        
        return None
        
    except Exception as e:
        print(f"❌ خطأ في {ticker}: {e}")
        return None

# ==================== تنسيق الرسالة ====================
def format_signal(data):
    """تنسيق رسالة التوصية"""
    if data['is_risky']:
        lines = [
            "⚠️ *إشارة مضاربة قصيرة الأجل* ⚡",
            f"📈 {data['name']} (`{data['ticker']}`)",
            "----------------------------------",
            f"📌 *السعر:* {data['entry']} جنيه",
            f"🎯 *الهدف:* {data['take_profit']} جنيه",
            f"🛑 *وقف الخسارة:* {data['stop_loss']} جنيه",
            "----------------------------------",
            f"📊 *RSI:* {data['rsi']} | *CMF:* {data['cmf']}",
            f"📈 *أداء 20 يوم:* {data['performance']}%",
            f"📊 *حجم التداول:* {data['volume_ratio']}x المتوسط",
            f"🌍 *اتجاه السوق:* {data['market_trend']}",
            "⚠️ *ملاحظة:* نتائج مالية ضعيفة - مضاربة فقط"
        ]
    else:
        lines = [
            "🚀 *إشارة استثمارية قوية* 🔥",
            f"📈 {data['name']} (`{data['ticker']}`)",
            "----------------------------------",
            f"📌 *السعر:* {data['entry']} جنيه",
            f"🎯 *الهدف:* {data['take_profit']} جنيه",
            f"🛑 *وقف الخسارة:* {data['stop_loss']} جنيه",
            "----------------------------------",
            f"📊 *RSI:* {data['rsi']} | *CMF:* {data['cmf']}",
            f"📈 *أداء 20 يوم:* {data['performance']}%",
            f"📊 *حجم التداول:* {data['volume_ratio']}x المتوسط",
            f"🌍 *اتجاه السوق:* {data['market_trend']}",
            f"🏛️ *P/E:* {data['pe']} | *EPS:* {data['eps']}"
        ]
    return "\n".join(lines)

# ==================== تشغيل البوت ====================
def main():
    # قائمة الأسهم المصرية
    watchlist = {
        "COMI.CA": "البنك التجاري الدولي",
        "TMGH.CA": "طلعت مصطفى",
        "HRHO.CA": "هيرميس",
        "CIEB.CA": "كريدي أجريكول",
        "ADIB.CA": "مصرف أبوظبي الإسلامي",
        "HELI.CA": "مصر للجديدة للإسكان",
        "PHDC.CA": "بالم هيلز",
        "ORAS.CA": "أوراسكوم للإنشاء",
        "MNHD.CA": "مدينة مصر",
        "EMFD.CA": "إعمار مصر",
        "ABUK.CA": "أبو قير للأسمدة",
        "KIMA.CA": "كيما",
        "ESRS.CA": "عز حديد",
        "AMOC.CA": "أموك",
        "EDIT.CA": "إيديتا",
        "JUFO.CA": "جهينة",
        "DOMT.CA": "دومتي",
        "EAST.CA": "الشرقية للدخان",
        "ISPH.CA": "ابن سينا فارما",
        "ETEL.CA": "المصرية للاتصالات",
        "SWDY.CA": "السويدي إليكتريك",
        "RAYA.CA": "راية"
    }
    
    # عرض حالة السوق
    trend = market_trend()
    send_telegram_message(f"🌍 *اتجاه السوق العام:* {trend}")
    
    # تحليل الأسهم
    signals = 0
    for ticker, name in watchlist.items():
        print(f"🔍 تحليل: {name} ({ticker})")
        result = analyze_stock(ticker, name)
        
        if result and result['signal']:
            msg = format_signal(result)
            send_telegram_message(msg)
            signals += 1
            print(f"✅ تم إرسال إشارة لـ {name}")
        
        time.sleep(0.5)  # تجنب الحظر
    
    if signals == 0:
        send_telegram_message("✅ لا توجد إشارات جديدة حالياً.")
    
    print(f"🏁 انتهى المسح. الإشارات: {signals}")

if __name__ == "__main__":
    main()
