import pandas as pd
import yfinance as yf
import requests
import os
from datetime import datetime
import time
import ta
from dotenv import load_dotenv

load_dotenv()

# ==================== إعدادات التليجرام ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("❌ يجب تعيين TELEGRAM_TOKEN و TELEGRAM_CHAT_ID")

def send_telegram_message(message):
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

# ==================== حساب CMF يدوياً ====================
def calculate_cmf(df, length=20):
    mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
    mf_volume = mf_multiplier * df['Volume']
    cmf = mf_volume.rolling(window=length).sum() / df['Volume'].rolling(window=length).sum()
    return cmf

# ==================== تحليل السوق العام ====================
def market_trend():
    try:
        df = yf.download("^EGX30", period="3mo", interval="1d", progress=False)
        if df.empty:
            return "محايد 🟡"
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
        last_close = df['Close'].iloc[-1]
        last_ema = df['EMA_50'].iloc[-1]
        
        if last_close > last_ema:
            return "صاعد 🟢"
        else:
            return "هابط 🔴"
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
        
        # ====== المؤشرات الفنية ======
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
        df['CMF'] = calculate_cmf(df, length=20)
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        
        # ====== الأداء ======
        df['Change_1d'] = df['Close'].pct_change() * 100
        df['Change_5d'] = df['Close'].pct_change(periods=5) * 100
        df['Change_20d'] = df['Close'].pct_change(periods=20) * 100
        
        last = df.iloc[-1]
        
        # ====== حجم التداول بالجنيه ======
        trading_value = last['Volume'] * last['Close']
        avg_trading_value = df['Volume_MA'].iloc[-1] * df['Close'].iloc[-1]
        
        # ====== الدعم والمقاومة ======
        high_30 = df['High'].tail(30)
        low_30 = df['Low'].tail(30)
        resistance = high_30.max()
        support = low_30.min()
        
        # ====== سعر الدخول ======
        entry_price = round(last['Close'] * 1.005, 2)
        stop_loss = round(support * 0.97, 2)
        take_profit = round(resistance * 0.995 if resistance > last['Close'] else last['Close'] * 1.05, 2)
        
        # ====== حساب المخاطرة/المكافأة ======
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        risk_reward = round(reward / risk, 2) if risk > 0 else 0
        
        # ====== شروط الشراء ======
        buy_conditions = {
            'ema_crossover': last['EMA_20'] > last['EMA_50'],
            'rsi_ok': 45 < last['RSI'] < 70,
            'cmf_ok': last['CMF'] > 0,
            'volume_ok': last['Volume'] > last['Volume_MA'] * 0.7,
            'above_ema50': last['Close'] > last['EMA_50']
        }
        is_buy = all(buy_conditions.values())
        
        # ====== شروط البيع ======
        is_sell = (last['Close'] < support or last['RSI'] > 75) and last['RSI'] > 60
        
        # ====== التوصية ======
        if is_buy:
            recommendation = "🔥 شراء"
            recommendation_emoji = "🟢"
        elif is_sell:
            recommendation = "🔴 بيع"
            recommendation_emoji = "🔴"
        else:
            recommendation = "⏳ انتظار"
            recommendation_emoji = "⚪"
        
        # ====== أسباب التوصية ======
        reasons = []
        if is_buy:
            reasons.append(f"✅ تقاطع EMA 20 فوق 50")
            reasons.append(f"✅ RSI {round(last['RSI'], 1)} (زخم إيجابي)")
            reasons.append(f"✅ CMF {round(last['CMF'], 3)} (سيولة داخلة)")
            reasons.append(f"✅ حجم التداول {round(last['Volume'] / last['Volume_MA'], 1)}x المتوسط")
        elif is_sell:
            if last['Close'] < support:
                reasons.append(f"⚠️ كسر الدعم {support}")
            if last['RSI'] > 75:
                reasons.append(f"⚠️ RSI {round(last['RSI'], 1)} (تشبع شرائي)")
        else:
            if last['Close'] < last['EMA_50']:
                reasons.append(f"📉 السهم تحت EMA 50 ({round(last['EMA_50'], 2)})")
            if last['RSI'] < 45:
                reasons.append(f"📉 RSI {round(last['RSI'], 1)} (ضعيف)")
        
        return {
            'ticker': ticker,
            'name': name,
            'price': round(last['Close'], 2),
            'change_1d': round(last['Change_1d'], 2),
            'change_5d': round(last['Change_5d'], 2),
            'change_20d': round(last['Change_20d'], 2),
            'rsi': round(last['RSI'], 1),
            'cmf': round(last['CMF'], 3),
            'volume_ratio': round(last['Volume'] / last['Volume_MA'], 1),
            'trading_value': round(trading_value, 0),
            'avg_trading_value': round(avg_trading_value, 0),
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': risk_reward,
            'recommendation': recommendation,
            'recommendation_emoji': recommendation_emoji,
            'reasons': reasons,
            'is_buy': is_buy,
            'is_sell': is_sell,
            'above_ema50': last['Close'] > last['EMA_50'],
            'ema_20': round(last['EMA_20'], 2),
            'ema_50': round(last['EMA_50'], 2)
        }
        
    except Exception as e:
        print(f"❌ خطأ في {ticker}: {e}")
        return None

# ==================== تنسيق التقرير ====================
def format_stock_report(r):
    lines = []
    
    lines.append(f"{r['recommendation_emoji']} *{r['name']}* (`{r['ticker']}`)")
    lines.append(f"💰 السعر: {r['price']} جنيه")
    lines.append(f"📈 الأداء: اليوم {r['change_1d']}% | أسبوع {r['change_5d']}% | شهر {r['change_20d']}%")
    lines.append("")
    lines.append(f"📊 RSI: {r['rsi']} | CMF: {r['cmf']}")
    lines.append(f"📊 EMA 20: {r['ema_20']} | EMA 50: {r['ema_50']}")
    lines.append(f"📊 حجم التداول: {r['volume_ratio']}x المتوسط")
    lines.append(f"💰 قيمة التداول: {r['trading_value']:,.0f} جنيه (المتوسط: {r['avg_trading_value']:,.0f})")
    lines.append("")
    lines.append(f"🛡️ دعم: {r['support']} | مقاومة: {r['resistance']}")
    lines.append(f"🎯 دخول: {r['entry_price']} | وقف: {r['stop_loss']} | هدف: {r['take_profit']}")
    lines.append(f"📊 المخاطرة/المكافأة: 1:{r['risk_reward']}")
    lines.append("")
    lines.append(f"📌 *التوصية:* {r['recommendation']}")
    if r['reasons']:
        lines.append("📝 الأسباب:")
        for reason in r['reasons']:
            lines.append(f"  {reason}")
    lines.append("")
    lines.append("-" * 40)
    
    return "\n".join(lines)

# ==================== الدالة الرئيسية ====================
def main():
    print("🚀 بدء تشغيل البوت...")
    
    send_telegram_message("✅ *البوت شغال وجاري التحليل...*")
    
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
    
    if results:
        # ====== التقرير الكامل ======
        lines = []
        lines.append("🌅 *التقرير الصباحي - البورصة المصرية*")
        lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 40)
        lines.append("")
        
        for r in results:
            lines.append(format_stock_report(r))
        
        send_telegram_message("\n".join(lines))
        
        # ====== تنبيهات الشراء ======
        buy_signals = [r for r in results if r['is_buy']]
        if buy_signals:
            alert = "🔥 *تنبيه شراء فوري:*\n"
            for r in buy_signals[:5]:
                alert += f"• {r['name']} - دخول: {r['entry_price']} | هدف: {r['take_profit']} | وقف: {r['stop_loss']}\n"
            send_telegram_message(alert)
        else:
            send_telegram_message("🟡 *لا توجد إشارات شراء قوية حالياً.*")
        
        # ====== ملخص ======
        buy_count = len([r for r in results if r['is_buy']])
        sell_count = len([r for r in results if r['is_sell']])
        
        summary = f"""
📊 *ملخص التحليل:*
• إجمالي الأسهم: {len(results)}
• 🟢 إشارات شراء: {buy_count}
• 🔴 إشارات بيع: {sell_count}

💡 *نصائح اليوم:*
• لا تخاطر بأكثر من 2% من رأس المال في صفقة واحدة
• التزم بوقف الخسارة المحدد
• خذ ربح جزئي عند الهدف الأول
"""
        send_telegram_message(summary)
    
    print(f"🏁 انتهى التشغيل. عدد الأسهم المحللة: {len(results)}")

if __name__ == "__main__":
    main()
