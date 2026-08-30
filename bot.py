import pandas as pd
import yfinance as yf
import requests
import os
import json
import time
import pytz
import ta
from datetime import datetime, timedelta
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
def get_stock_data_yfinance(ticker, period="6mo"):
    """جلب بيانات السهم من yfinance"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval="1d", progress=False)
        
        if df.empty:
            print(f"⚠️ مفيش بيانات لـ {ticker}")
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        return df
        
    except Exception as e:
        print(f"❌ yfinance خطأ في {ticker}: {e}")
        return None

# ==================== حساب CMF يدوياً ====================
def calculate_cmf(df, length=20):
    """حساب مؤشر CMF (Chaikin Money Flow)"""
    mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
    mf_volume = mf_multiplier * df['Volume']
    cmf = mf_volume.rolling(window=length).sum() / df['Volume'].rolling(window=length).sum()
    return cmf

# ==================== الحصول على أعلى الأسهم سيولة ====================
def get_top_liquid_stocks(limit=8):
    """جلب الأسهم الأعلى سيولة (حسب حجم التداول)"""
    all_stocks = {
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
        "RAYA.CA": "راية",
        "FWRY.CA": "فوري",
        "SKPC.CA": "سيدي كرير للبتروكيماويات",
        "GBCO.CA": "جي بي كورب",
        "BLCY.CA": "بلتون القابضة"
    }
    
    print("🔍 جاري حساب السيولة...")
    stock_volumes = []
    
    for ticker, name in all_stocks.items():
        try:
            df = get_stock_data_yfinance(ticker, period="5d")
            
            if df is None or df.empty:
                continue
            
            last_day = df.iloc[-1]
            volume = last_day['Volume']
            price = last_day['Close']
            
            if volume > 0 and price > 0:
                value = volume * price
                stock_volumes.append((ticker, name, value))
                print(f"  ✅ {name}: {value:,.0f} جنيه")
                
        except Exception as e:
            print(f"  ❌ فشل {ticker}: {str(e)[:50]}")
            continue
        
        time.sleep(0.3)
    
    stock_volumes.sort(key=lambda x: x[2], reverse=True)
    
    top_stocks = {}
    for ticker, name, value in stock_volumes[:limit]:
        top_stocks[ticker] = name
        print(f"  🏆 {name}: {value:,.0f} جنيه")
    
    return top_stocks

# ==================== تحليل السوق العام ====================
def market_trend():
    """تحديد اتجاه السوق العام"""
    try:
        df = get_stock_data_yfinance("^EGX30", period="3mo")
        if df is None or df.empty:
            return "محايد 🟡"
        
        df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
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

# ==================== حساب الدعم والمقاومة المحسن ====================
def calculate_support_resistance_enhanced(df, lookback=30):
    """حساب الدعم والمقاومة بطريقة محسنة"""
    last = df.iloc[-1]
    current_price = last['Close']
    
    # أعلى وأدنى 30 يوم
    high_30 = df['High'].tail(lookback)
    low_30 = df['Low'].tail(lookback)
    
    resistance = high_30.max()
    support = low_30.min()
    
    # حساب القمم والقيعان المحلية (أدق)
    peaks = []
    troughs = []
    
    for i in range(5, len(high_30) - 5):
        if high_30.iloc[i] == high_30.iloc[i-5:i+6].max():
            peaks.append(high_30.iloc[i])
        if low_30.iloc[i] == low_30.iloc[i-5:i+6].min():
            troughs.append(low_30.iloc[i])
    
    # أقرب مقاومة فوق السعر
    resistances_above = [p for p in peaks if p > current_price]
    closest_resistance = min(resistances_above) if resistances_above else resistance
    
    # أقرب دعم تحت السعر
    supports_below = [t for t in troughs if t < current_price]
    closest_support = max(supports_below) if supports_below else support
    
    return {
        'support': round(closest_support, 2),
        'resistance': round(closest_resistance, 2),
        'main_support': round(support, 2),
        'main_resistance': round(resistance, 2),
        'current_price': round(current_price, 2)
    }

# ==================== تحليل السهم ====================
def analyze_stock(ticker, name):
    """تحليل سهم واحد مع دعم ومقاومة محسنة"""
    try:
        df = get_stock_data_yfinance(ticker, period="6mo")
        
        if df is None or df.empty or len(df) < 50:
            return None
        
        # ====== المؤشرات الفنية ======
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
        df['CMF'] = calculate_cmf(df, length=20)
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Price_Change_1d'] = df['Close'].pct_change() * 100
        df['Price_Change_5d'] = df['Close'].pct_change(periods=5) * 100
        df['Price_Change_20d'] = df['Close'].pct_change(periods=20) * 100
        
        last = df.iloc[-1]
        
        # ====== حساب الدعم والمقاومة المحسن ======
        sr = calculate_support_resistance_enhanced(df)
        current_price = sr['current_price']
        support = sr['support']
        resistance = sr['resistance']
        main_support = sr['main_support']
        main_resistance = sr['main_resistance']
        
        # ====== سعر الدخول المثالي ======
        if current_price < support * 1.02:
            entry_price = round(support * 1.01, 2)
            entry_strategy = "الارتداد من الدعم"
        elif current_price > resistance * 0.98:
            entry_price = round(resistance * 1.005, 2)
            entry_strategy = "اختراق المقاومة"
        else:
            entry_price = round(current_price * 1.005, 2)
            entry_strategy = "السعر الحالي + 0.5%"
        
        # ====== وقف الخسارة ======
        stop_loss = round(main_support * 0.97, 2)
        
        # ====== هدف الربح ======
        if main_resistance > current_price:
            take_profit_1 = round(main_resistance * 0.995, 2)
        else:
            take_profit_1 = round(current_price * 1.05, 2)
        
        take_profit_2 = round(take_profit_1 * 1.02, 2)
        
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
        is_sell = (last['Close'] < main_support or last['RSI'] > 75 or last['CMF'] < -0.1) and last['RSI'] > 60
        
        # ====== تحديد الإشارة ======
        signal = "انتظار ⏳"
        signal_type = "none"
        reasons = []
        
        if is_buy:
            signal = "🔥 شراء فوري"
            signal_type = "buy"
            reasons = [
                f"تقاطع EMA 20 فوق 50 ({round(last['EMA_20'], 2)} > {round(last['EMA_50'], 2)})",
                f"RSI {round(last['RSI'], 1)} (زخم إيجابي)",
                f"دعم عند {support}",
                f"حجم التداول {round(last['Volume'] / last['Volume_MA'], 1)}x المتوسط"
            ]
        elif is_sell:
            signal = "⚠️ بيع/خروج"
            signal_type = "sell"
            reasons = [
                f"كسر الدعم {main_support}" if last['Close'] < main_support else f"RSI {round(last['RSI'], 1)} (تشبع)",
                "CMF سالب (سيولة خارجة)" if last['CMF'] < -0.1 else "تحت المتوسط 50"
            ]
        
        return {
            'ticker': ticker,
            'name': name,
            'price': round(current_price, 2),
            'ema_20': round(last['EMA_20'], 2),
            'ema_50': round(last['EMA_50'], 2),
            'rsi': round(last['RSI'], 1),
            'cmf': round(last['CMF'], 3),
            'atr': round(last['ATR'], 2),
            'volume_ratio': round(last['Volume'] / last['Volume_MA'], 1),
            'change_1d': round(last['Price_Change_1d'], 2),
            'change_5d': round(last['Price_Change_5d'], 2),
            'change_20d': round(last['Price_Change_20d'], 2),
            'support': support,
            'resistance': resistance,
            'main_support': main_support,
            'main_resistance': main_resistance,
            'entry_price': entry_price,
            'entry_strategy': entry_strategy,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'risk_reward': risk_reward,
            'signal': signal,
            'signal_type': signal_type,
            'reasons': reasons,
            'is_buy': is_buy,
            'is_sell': is_sell,
            'above_ema50': last['Close'] > last['EMA_50']
        }
        
    except Exception as e:
        print(f"❌ خطأ في {ticker}: {e}")
        return None

# ==================== التقرير الصباحي ====================
def morning_report(top_liquid, all_results, trend):
    """توليد التقرير الصباحي المحسن"""
    lines = []
    
    egypt_tz = pytz.timezone('Africa/Cairo')
    now = datetime.now(egypt_tz)
    
    lines.append("🌅 *التقرير الصباحي - البورصة المصرية*")
    lines.append(f"📅 {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"🌍 *اتجاه السوق العام:* {trend}")
    lines.append("=" * 50)
    lines.append("")
    
    # ====== الأسهم الأكثر سيولة ======
    if top_liquid:
        lines.append("🔥 *الأسهم الأكثر سيولة (للمراقبة اليومية):*")
        for i, (ticker, name) in enumerate(top_liquid.items(), 1):
            stock_result = next((r for r in all_results if r and r['ticker'] == ticker), None)
            if stock_result:
                trend_emoji = "📈" if stock_result['above_ema50'] else "📉"
                lines.append(f"{i}. {trend_emoji} *{name}* (`{ticker}`)")
                lines.append(f"   💰 السعر: {stock_result['price']} جنيه")
                lines.append(f"   📊 RSI: {stock_result['rsi']} | CMF: {stock_result['cmf']}")
                lines.append(f"   📈 حجم: {stock_result['volume_ratio']}x المتوسط")
                lines.append(f"   🛡️ دعم قريب: {stock_result['support']} | 🚀 مقاومة قريبة: {stock_result['resistance']}")
                lines.append(f"   🛡️ الدعم الرئيسي: {stock_result['main_support']} | 🚀 المقاومة الرئيسية: {stock_result['main_resistance']}")
            else:
                lines.append(f"{i}. {name} (`{ticker}`)")
        lines.append("")
    else:
        lines.append("⚠️ *تعذر حساب السيولة - استخدم القائمة اليدوية:*")
        default_liquid = ["COMI.CA", "TMGH.CA", "HRHO.CA", "CIEB.CA", "ADIB.CA"]
        for ticker in default_liquid:
            stock_result = next((r for r in all_results if r and r['ticker'] == ticker), None)
            if stock_result:
                lines.append(f"• {stock_result['name']} (`{ticker}`) - {stock_result['price']} جنيه")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append("")
    
    # ====== إشارات الشراء ======
    buy_signals = [r for r in all_results if r and r['is_buy']]
    if buy_signals:
        lines.append("🟢 *إشارات شراء قوية:*")
        for r in buy_signals[:8]:
            lines.append(f"• *{r['name']}* (`{r['ticker']}`)")
            lines.append(f"  💰 السعر: {r['price']} جنيه")
            lines.append(f"  📊 RSI: {r['rsi']} | CMF: {r['cmf']}")
            lines.append(f"  📈 حجم التداول: {r['volume_ratio']}x المتوسط")
            lines.append(f"  📈 الأداء 20 يوم: {r['change_20d']}%")
            lines.append(f"  🎯 الدخول: {r['entry_price']} | وقف: {r['stop_loss']} | هدف: {r['take_profit_1']}")
            lines.append(f"  🛡️ دعم: {r['support']} | 🚀 مقاومة: {r['resistance']}")
            if r['reasons']:
                lines.append(f"  ✅ {r['reasons'][0]}")
        lines.append("")
    else:
        lines.append("🟡 *لا توجد إشارات شراء قوية حالياً.*")
        lines.append("")
    
    # ====== إشارات البيع ======
    sell_signals = [r for r in all_results if r and r['is_sell']]
    if sell_signals:
        lines.append("🔴 *إشارات بيع/خروج:*")
        for r in sell_signals[:5]:
            lines.append(f"• *{r['name']}* (`{r['ticker']}`)")
            lines.append(f"  💰 السعر: {r['price']} جنيه")
            lines.append(f"  📊 RSI: {r['rsi']} | CMF: {r['cmf']}")
            if r['reasons']:
                lines.append(f"  ⚠️ {r['reasons'][0]}")
        lines.append("")
    
    # ====== ملخص ======
    lines.append("=" * 50)
    lines.append("📊 *ملخص سريع:*")
    lines.append(f"• إجمالي الأسهم: {len(all_results)}")
    lines.append(f"• إشارات شراء: {len(buy_signals)}")
    lines.append(f"• إشارات بيع: {len(sell_signals)}")
    lines.append("")
    
    # ====== نصائح ======
    lines.append("💡 *نصائح اليوم:*")
    if trend == "صاعد 🟢":
        lines.append("• السوق في اتجاه صاعد - ركز على إشارات الشراء")
    elif trend == "هابط 🔴":
        lines.append("• السوق في اتجاه هابط - قلل حجم الصفقات")
    else:
        lines.append("• السوق في حالة محايدة - انتظر وضوح الاتجاه")
    
    lines.append("• لا تدخل في صفقة بدون وقف خسارة")
    lines.append("• خذ ربح جزئي عند تحقيق الهدف الأول")
    
    return "\n".join(lines)

# ==================== تنبيه فوري ====================
def alert_message(r):
    """تنسيق رسالة التنبيه الفوري"""
    if r['is_buy']:
        emoji = "🔥"
        title = "تنبيه شراء فوري"
        color = "🟢"
    elif r['is_sell']:
        emoji = "⚠️"
        title = "تنبيه بيع/خروج"
        color = "🔴"
    else:
        return None
    
    lines = [
        f"{emoji} *{title} - {r['name']}*",
        f"{color} السهم: `{r['ticker']}`",
        "----------------------------------",
        f"💰 السعر الحالي: {r['price']} جنيه",
        f"🎯 سعر الدخول: {r['entry_price']} جنيه ({r['entry_strategy']})",
        f"🛑 وقف الخسارة: {r['stop_loss']} جنيه",
        f"🏆 الهدف الأول: {r['take_profit_1']} جنيه",
        f"🏆 الهدف الثاني: {r['take_profit_2']} جنيه",
        f"📊 نسبة المخاطرة/المكافأة: 1:{r['risk_reward']}",
        "----------------------------------",
        f"🛡️ أقرب دعم: {r['support']} جنيه",
        f"🚀 أقرب مقاومة: {r['resistance']} جنيه",
        f"📊 RSI: {r['rsi']} | CMF: {r['cmf']}",
        f"📈 حجم التداول: {r['volume_ratio']}x المتوسط",
    ]
    
    if r['reasons']:
        lines.append("📝 الأسباب:")
        for reason in r['reasons'][:4]:
            lines.append(f"  ✅ {reason}")
    
    egypt_tz = pytz.timezone('Africa/Cairo')
    now = datetime.now(egypt_tz)
    lines.append("")
    lines.append(f"⏰ {now.strftime('%H:%M:%S')}")
    
    return "\n".join(lines)

# ==================== منع التكرار ====================
def is_duplicate_run():
    lock_file = "last_run.json"
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                data = json.load(f)
                last_run = datetime.fromisoformat(data['last_run'])
                if (datetime.now() - last_run).seconds < 300:
                    return True
        except:
            pass
    return False

def save_run_time():
    lock_file = "last_run.json"
    with open(lock_file, 'w') as f:
        json.dump({'last_run': datetime.now().isoformat()}, f)

# ==================== الدالة الرئيسية ====================
def main():
    print("🚀 بدء تشغيل النظام المتكامل...")
    
    if is_duplicate_run():
        print("⏳ تم التشغيل مؤخراً، تخطي...")
        return
    
    top_liquid = get_top_liquid_stocks(limit=8)
    print(f"✅ تم اختيار {len(top_liquid)} سهم عالي السيولة")
    
    trend = market_trend()
    print(f"🌍 اتجاه السوق: {trend}")
    
    all_stocks = {
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
        "RAYA.CA": "راية",
        "FWRY.CA": "فوري",
        "SKPC.CA": "سيدي كرير للبتروكيماويات",
        "GBCO.CA": "جي بي كورب",
        "BLCY.CA": "بلتون القابضة"
    }
    
    all_results = []
    alerts_sent = 0
    
    for ticker, name in all_stocks.items():
        print(f"🔍 تحليل: {name}")
        result = analyze_stock(ticker, name)
        if result:
            all_results.append(result)
            
            if ticker in top_liquid and (result['is_buy'] or result['is_sell']):
                alert = alert_message(result)
                if alert:
                    send_telegram_message(f"🔔 *تنبيه فوري*\n\n{alert}")
                    alerts_sent += 1
                    print(f"✅ تم إرسال تنبيه لـ {name}")
            
            time.sleep(0.3)
    
    report = morning_report(top_liquid, all_results, trend)
    send_telegram_message(report)
    print("✅ تم إرسال التقرير الصباحي")
    
    buy_count = len([r for r in all_results if r and r['is_buy']])
    sell_count = len([r for r in all_results if r and r['is_sell']])
    
    egypt_tz = pytz.timezone('Africa/Cairo')
    now = datetime.now(egypt_tz)
    
    summary = f"""
📊 *ملخص التحليل:*
• إجمالي الأسهم المحللة: {len(all_results)}
• إشارات شراء: {buy_count}
• إشارات بيع: {sell_count}
• تنبيهات مرسلة: {alerts_sent}
• اتجاه السوق: {trend}

⏰ {now.strftime('%Y-%m-%d %H:%M:%S')}
"""
    send_telegram_message(summary)
    print("✅ تم إرسال الملخص")
    
    save_run_time()
    
    print(f"🏁 انتهى التشغيل. الإشارات: شراء {buy_count} | بيع {sell_count} | تنبيهات {alerts_sent}")

if __name__ == "__main__":
    main()
