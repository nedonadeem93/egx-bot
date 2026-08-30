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

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("❌ يجب تعيين TELEGRAM_TOKEN و TELEGRAM_CHAT_ID")

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
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        last_close = df['Close'].iloc[-1]
        last_ema = df['EMA_50'].iloc[-1]
        
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
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # المؤشرات الفنية
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['CMF'] = ta.cmf(df['High'], df['Low'], df['Close'], df['Volume'], length=20)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        
        # حساب الدعم والمقاومة
        high = df['High'].tail(30)
        low = df['Low'].tail(30)
        resistance = high.max()
        support = low.min()
        
        # سعر الدخول
        entry_price = round(last['Close'] * 1.005, 2)
        stop_loss = round(support * 0.97, 2)
        take_profit = round(resistance * 0.995 if resistance > last['Close'] else last['Close'] * 1.05, 2)
        
        # شروط الشراء
        is_buy = all([
            last['EMA_20'] > last['EMA_50'],
            45 < last['RSI'] < 70,
            last['CMF'] > 0,
            last['Volume'] > df['Volume'].rolling(20).mean().iloc[-1] * 0.7,
            last['Close'] > last['EMA_50']
        ])
        
        # شروط البيع
        is_sell = (last['Close'] < support or last['RSI'] > 75) and last['RSI'] > 60
        
        return {
            'ticker': ticker,
            'name': name,
            'price': round(last['Close'], 2),
            'rsi': round(last['RSI'], 1),
            'cmf': round(last['CMF'], 3),
            'volume_ratio': round(last['Volume'] / df['Volume'].rolling(20).mean().iloc[-1], 1),
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'is_buy': is_buy,
            'is_sell': is_sell,
            'above_ema50': last['Close'] > last['EMA_50']
        }
        
    except Exception as e:
        print(f"❌ خطأ في {ticker}: {e}")
        return None

# ==================== الدالة الرئيسية ====================
def main():
    print("🚀 بدء تشغيل البوت...")
    
    all_stocks = {
        "COMI.CA": "البنك التجاري الدولي",
        "TMGH.CA": "طلعت مصطفى",
        "HRHO.CA": "هيرميس",
        "CIEB.CA": "كريدي أجريكول",
        "ADIB.CA": "مصرف أبوظبي الإسلامي",
        "PHDC.CA": "بالم هيلز",
        "ORAS.CA": "أوراسكوم للإنشاء",
        "ETEL.CA": "المصرية للاتصالات",
        "SWDY.CA": "السويدي إليكتريك",
        "ABUK.CA": "أبو قير للأسمدة",
        "EMFD.CA": "إعمار مصر",
        "MNHD.CA": "مدينة مصر",
        "HELI.CA": "مصر للجديدة للإسكان",
        "KIMA.CA": "كيما",
        "AMOC.CA": "أموك",
        "ESRS.CA": "عز حديد",
        "JUFO.CA": "جهينة",
        "DOMT.CA": "دومتي",
        "EAST.CA": "الشرقية للدخان",
        "ISPH.CA": "ابن سينا فارما",
        "RAYA.CA": "راية",
        "FWRY.CA": "فوري"
    }
    
    results = []
    
    for ticker, name in all_stocks.items():
        print(f"🔍 تحليل: {name} ({ticker})")
        result = analyze_stock(ticker, name)
        if result:
            results.append(result)
            print(f"  ✅ تم تحليل {name}")
        time.sleep(0.5)
    
    if results:
        # ====== تقرير كامل ======
        lines = []
        lines.append("🌅 *التقرير الصباحي - البورصة المصرية*")
        lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 40)
        lines.append("")
        
        for r in results:
            emoji = "🟢" if r['is_buy'] else "🔴" if r['is_sell'] else "⚪"
            lines.append(f"{emoji} *{r['name']}* (`{r['ticker']}`)")
            lines.append(f"  💰 السعر: {r['price']} جنيه")
            lines.append(f"  📊 RSI: {r['rsi']} | CMF: {r['cmf']}")
            lines.append(f"  📈 حجم: {r['volume_ratio']}x المتوسط")
            lines.append(f"  🛡️ دعم: {r['support']} | 🚀 مقاومة: {r['resistance']}")
            if r['is_buy']:
                lines.append(f"  🎯 دخول: {r['entry_price']} | وقف: {r['stop_loss']} | هدف: {r['take_profit']}")
                lines.append("  ✅ إشارة شراء")
            elif r['is_sell']:
                lines.append("  ⚠️ إشارة بيع")
            lines.append("")
        
        lines.append("=" * 40)
        buy_signals = [r for r in results if r['is_buy']]
        lines.append(f"📊 *ملخص:*")
        lines.append(f"• إجمالي الأسهم: {len(results)}")
        lines.append(f"• 🟢 إشارات شراء: {len(buy_signals)}")
        lines.append(f"• 🔴 إشارات بيع: {len([r for r in results if r['is_sell']])}")
        lines.append("")
        lines.append("💡 *نصائح اليوم:*")
        lines.append("• لا تدخل بدون وقف خسارة")
        lines.append("• خذ ربح جزئي عند الهدف")
        
        send_telegram_message("\n".join(lines))
        
        # ====== تنبيهات الشراء ======
        if buy_signals:
            alert = "🔥 *تنبيه شراء فوري:*\n"
            for r in buy_signals[:5]:
                alert += f"• {r['name']} - دخول: {r['entry_price']} | هدف: {r['take_profit']} | وقف: {r['stop_loss']}\n"
            send_telegram_message(alert)
    
    print(f"🏁 انتهى التشغيل. عدد الأسهم المحللة: {len(results)}")

if __name__ == "__main__":
    main()
