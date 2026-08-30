import pandas as pd
import yfinance as yf
import requests
import os
import time
import pytz
import ta
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ==================== إعدادات التليجرام ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("❌ لازم تحط TELEGRAM_TOKEN و TELEGRAM_CHAT_ID في Secrets GitHub")

def send_telegram_message(message):
    """إرسال رسالة مع تقسيمها إذا كانت طويلة"""
    if len(message) > 4000:
        parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for part in parts:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": part, "parse_mode": "Markdown"}
            try:
                requests.post(url, json=payload, timeout=10)
            except Exception as e:
                print(f"❌ خطأ في الإرسال: {e}")
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"❌ خطأ في الإرسال: {e}")

# ==================== جلب البيانات من yfinance ====================
def get_stock_data(ticker, period="6mo"):
    """جلب بيانات السهم من yfinance"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval="1d", progress=False)
        
        if df.empty:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        return df
        
    except Exception as e:
        print(f"❌ خطأ في {ticker}: {e}")
        return None

# ==================== حساب الدعم والمقاومة المتقدم ====================
def calculate_support_resistance_advanced(df, lookback=50, window=5):
    """حساب الدعم والمقاومة بطريقة احترافية"""
    high = df['High'].tail(lookback)
    low = df['Low'].tail(lookback)
    close = df['Close'].tail(lookback)
    current_price = close.iloc[-1]
    
    # قمم محلية
    peaks = []
    troughs = []
    
    for i in range(window, len(high) - window):
        if high.iloc[i] == high.iloc[i-window:i+window+1].max():
            peaks.append(high.iloc[i])
        if low.iloc[i] == low.iloc[i-window:i+window+1].min():
            troughs.append(low.iloc[i])
    
    # أقرب دعم ومقاومة
    resistances = [p for p in peaks if p > current_price]
    resistance = min(resistances) if resistances else high.max()
    
    supports = [t for t in troughs if t < current_price]
    support = max(supports) if supports else low.min()
    
    # متوسط الدعم والمقاومة (آخر 50 يوم)
    avg_resistance = high.mean()
    avg_support = low.mean()
    
    return {
        'support': round(support, 2),
        'resistance': round(resistance, 2),
        'avg_support': round(avg_support, 2),
        'avg_resistance': round(avg_resistance, 2),
        'current_price': round(current_price, 2)
    }

# ==================== تحليل السهم ====================
def analyze_stock(ticker, name):
    """تحليل سهم واحد مع دعم ومقاومة متقدم"""
    try:
        df = get_stock_data(ticker, period="6mo")
        
        if df is None or len(df) < 50:
            return None
        
        # ====== المؤشرات الفنية ======
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        
        # حساب CMF يدوياً
        mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
        mf_volume = mf_multiplier * df['Volume']
        df['CMF'] = mf_volume.rolling(window=20).sum() / df['Volume'].rolling(window=20).sum()
        
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Price_Change_1d'] = df['Close'].pct_change() * 100
        df['Price_Change_5d'] = df['Close'].pct_change(periods=5) * 100
        df['Price_Change_20d'] = df['Close'].pct_change(periods=20) * 100
        
        last = df.iloc[-1]
        
        # ====== حساب الدعم والمقاومة المتقدم ======
        sr = calculate_support_resistance_advanced(df)
        current_price = sr['current_price']
        support = sr['support']
        resistance = sr['resistance']
        avg_support = sr['avg_support']
        avg_resistance = sr['avg_resistance']
        
        # ====== سعر الدخول المثالي ======
        if current_price < support * 1.02:
            entry_price = round(support * 1.01, 2)
            entry_strategy = "الشراء من الدعم"
        elif current_price > resistance * 0.98:
            entry_price = round(resistance * 1.005, 2)
            entry_strategy = "اختراق المقاومة"
        else:
            entry_price = round(current_price * 1.005, 2)
            entry_strategy = "السعر الحالي + 0.5%"
        
        # ====== وقف الخسارة ======
        stop_loss = round(support * 0.98, 2)
        
        # ====== هدف الربح ======
        if resistance > current_price:
            take_profit_1 = round(resistance, 2)
        else:
            take_profit_1 = round(current_price * 1.05, 2)
        
        take_profit_2 = round(take_profit_1 * 1.03, 2)
        
        # ====== نسبة المخاطرة/المكافأة ======
        risk = entry_price - stop_loss
        reward = take_profit_1 - entry_price
        risk_reward = round(reward / risk, 2) if risk > 0 else 0
        
        # ====== شروط الدخول (شراء) ======
        buy_conditions = {
            'ema_crossover': last['EMA_20'] > last['EMA_50'],
            'rsi_ok': 45 < last['RSI'] < 70,
            'cmf_ok': last['CMF'] > 0,
            'volume_ok': last['Volume'] > last['Volume_MA'] * 0.7,
            'above_ema50': last['Close'] > last['EMA_50'],
            'near_support': current_price < support * 1.05
        }
        
        is_buy = all(buy_conditions.values())
        
        # ====== شروط الخروج (بيع) ======
        is_sell = (last['Close'] < support or last['RSI'] > 75 or last['CMF'] < -0.1) and last['RSI'] > 60
        
        # ====== تحديد التوصية ======
        if is_buy:
            recommendation = "🔥 شراء فوري"
        elif is_sell:
            recommendation = "⚠️ بيع/خروج"
        elif last['Close'] < last['EMA_50'] and last['RSI'] < 40:
            recommendation = "🟡 مراقبة للشراء"
        else:
            recommendation = "⏳ انتظار"
        
        # ====== تجميع النتائج ======
        return {
            'ticker': ticker,
            'name': name,
            'price': round(current_price, 2),
            'change_1d': round(last['Price_Change_1d'], 2),
            'change_5d': round(last['Price_Change_5d'], 2),
            'change_20d': round(last['Price_Change_20d'], 2),
            'rsi': round(last['RSI'], 1),
            'cmf': round(last['CMF'], 3),
            'ema_20': round(last['EMA_20'], 2),
            'ema_50': round(last['EMA_50'], 2),
            'volume_ratio': round(last['Volume'] / last['Volume_MA'], 1),
            'support': support,
            'resistance': resistance,
            'avg_support': avg_support,
            'avg_resistance': avg_resistance,
            'entry_price': entry_price,
            'entry_strategy': entry_strategy,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'risk_reward': risk_reward,
            'recommendation': recommendation,
            'is_buy': is_buy,
            'is_sell': is_sell,
            'above_ema50': last['Close'] > last['EMA_50']
        }
        
    except Exception as e:
        print(f"❌ خطأ في {ticker}: {e}")
        return None

# ==================== تنسيق التقرير ====================
def format_stock_report(result):
    """تنسيق تقرير سهم واحد"""
    lines = []
    
    # ====== رأس السهم ======
    lines.append(f"📊 *{result['name']}* (`{result['ticker']}`)")
    lines.append(f"💰 السعر الحالي: {result['price']} جنيه")
    lines.append(f"📈 التغيير اليومي: {result['change_1d']}% | الأسبوعي: {result['change_5d']}% | 20 يوم: {result['change_20d']}%")
    lines.append("")
    
    # ====== المؤشرات الفنية ======
    lines.append("📊 *المؤشرات الفنية:*")
    lines.append(f"• RSI: {result['rsi']} | CMF: {result['cmf']}")
    lines.append(f"• EMA 20: {result['ema_20']} | EMA 50: {result['ema_50']}")
    lines.append(f"• حجم التداول: {result['volume_ratio']}x المتوسط")
    lines.append("")
    
    # ====== الدعم والمقاومة ======
    lines.append("🛡️ *الدعم والمقاومة:*")
    lines.append(f"• أقرب دعم: {result['support']} جنيه")
    lines.append(f"• أقرب مقاومة: {result['resistance']} جنيه")
    lines.append(f"• متوسط الدعم (50 يوم): {result['avg_support']} جنيه")
    lines.append(f"• متوسط المقاومة (50 يوم): {result['avg_resistance']} جنيه")
    lines.append("")
    
    # ====== سعر الدخول والخروج ======
    lines.append("🎯 *سعر الدخول والخروج المثالي:*")
    lines.append(f"• سعر الدخول: {result['entry_price']} جنيه ({result['entry_strategy']})")
    lines.append(f"• وقف الخسارة: {result['stop_loss']} جنيه")
    lines.append(f"• الهدف الأول: {result['take_profit_1']} جنيه")
    lines.append(f"• الهدف الثاني: {result['take_profit_2']} جنيه")
    lines.append(f"• نسبة المخاطرة/المكافأة: 1:{result['risk_reward']}")
    lines.append("")
    
    # ====== التوصية ======
    lines.append(f"📌 *التوصية:* {result['recommendation']}")
    lines.append("")
    lines.append("-" * 40)
    lines.append("")
    
    return "\n".join(lines)

# ==================== الدالة الرئيسية ====================
def main():
    print("🚀 بدء تشغيل البوت...")
    
    # قائمة الأسهم المصرية (المختصرة والموثوقة)
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
        time.sleep(0.5)
    
    # ====== إرسال التقرير ======
    if results:
        # تقرير كامل
        full_report = []
        full_report.append("🌅 *التقرير الصباحي - البورصة المصرية*")
        full_report.append(f"📅 {datetime.now(pytz.timezone('Africa/Cairo')).strftime('%Y-%m-%d %H:%M')}")
        full_report.append("=" * 40)
        full_report.append("")
        
        for result in results:
            full_report.append(format_stock_report(result))
        
        send_telegram_message("\n".join(full_report))
        
        # ====== ملخص الإشارات القوية ======
        buy_signals = [r for r in results if r['is_buy']]
        if buy_signals:
            summary = ["🔥 *إشارات شراء قوية:*"]
            for r in buy_signals[:5]:
                summary.append(f"• {r['name']} - الدخول: {r['entry_price']} | الهدف: {r['take_profit_1']} | وقف: {r['stop_loss']}")
            send_telegram_message("\n".join(summary))
        
        # ====== ملخص التحليل ======
        buy_count = len([r for r in results if r['is_buy']])
        sell_count = len([r for r in results if r['is_sell']])
        
        summary = f"""
📊 *ملخص التحليل:*
• إجمالي الأسهم: {len(results)}
• إشارات شراء: {buy_count}
• إشارات بيع: {sell_count}

💡 *نصائح اليوم:*
• لا تخاطر بأكثر من 2% من رأس المال في صفقة واحدة
• التزم بوقف الخسارة المحدد
• خذ ربح جزئي عند الهدف الأول
"""
        send_telegram_message(summary)
    
    print(f"🏁 انتهى التشغيل. عدد الأسهم: {len(results)}")

if __name__ == "__main__":
    main()
