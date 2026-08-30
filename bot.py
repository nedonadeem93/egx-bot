import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests
import os
import json
import time
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ==================== إعدادات التليجرام ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("❌ يجب تعيين TELEGRAM_TOKEN و TELEGRAM_CHAT_ID")

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
            stock = yf.Ticker(ticker)
            df = stock.history(period="5d", interval="1d", progress=False)
            
            if df.empty:
                continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if 'Volume' in df.columns and 'Close' in df.columns:
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
        
        time.sleep(0.5)
    
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

# ==================== حساب الدعم والمقاومة المتقدم ====================
def calculate_support_resistance_advanced(df, lookback=50, window=5):
    """حساب الدعم والمقاومة بطريقة احترافية"""
    high = df['High'].tail(lookback)
    low = df['Low'].tail(lookback)
    close = df['Close'].tail(lookback)
    current_price = close.iloc[-1]
    
    peaks = []
    troughs = []
    
    for i in range(window, len(high) - window):
        if high.iloc[i] == high.iloc[i-window:i+window+1].max():
            peaks.append(high.iloc[i])
        if low.iloc[i] == low.iloc[i-window:i+window+1].min():
            troughs.append(low.iloc[i])
    
    resistances = [p for p in peaks if p > current_price]
    resistance = min(resistances) if resistances else high.max()
    
    supports = [t for t in troughs if t < current_price]
    support = max(supports) if supports else low.min()
    
    avg_resistance = sum(peaks[-3:]) / 3 if len(peaks) >= 3 else high.mean()
    avg_support = sum(troughs[-3:]) / 3 if len(troughs) >= 3 else low.mean()
    
    highest_50 = high.max()
    lowest_50 = low.min()
    range_50 = highest_50 - lowest_50
    
    fib_levels = {
        '0.0': lowest_50,
        '0.236': lowest_50 + 0.236 * range_50,
        '0.382': lowest_50 + 0.382 * range_50,
        '0.5': lowest_50 + 0.5 * range_50,
        '0.618': lowest_50 + 0.618 * range_50,
        '0.786': lowest_50 + 0.786 * range_50,
        '1.0': highest_50
    }
    
    closest_fib = None
    closest_fib_level = None
    for level, price in fib_levels.items():
        if closest_fib is None or abs(price - current_price) < abs(closest_fib - current_price):
            closest_fib = price
            closest_fib_level = level
    
    return {
        'support': round(support, 2),
        'resistance': round(resistance, 2),
        'avg_support': round(avg_support, 2),
        'avg_resistance': round(avg_resistance, 2),
        'highest_50': round(highest_50, 2),
        'lowest_50': round(lowest_50, 2),
        'fib_levels': {k: round(v, 2) for k, v in fib_levels.items()},
        'closest_fib': round(closest_fib, 2),
        'closest_fib_level': closest_fib_level,
        'current_price': current_price
    }

# ==================== تحليل السهم ====================
def analyze_stock(ticker, name):
    """تحليل سهم واحد مع دعم ومقاومة متقدم"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['CMF'] = ta.cmf(df['High'], df['Low'], df['Close'], df['Volume'], length=20)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Price_Change_1d'] = df['Close'].pct_change() * 100
        df['Price_Change_5d'] = df['Close'].pct_change(periods=5) * 100
        df['Price_Change_20d'] = df['Close'].pct_change(periods=20) * 100
        
        last = df.iloc[-1]
        
        sr = calculate_support_resistance_advanced(df)
        
        # حساب سعر الدخول
        if last['Close'] > sr['resistance'] * 0.98:
            entry_price = round(sr['resistance'] * 1.005, 2)
            entry_strategy = "اختراق المقاومة"
        elif last['Close'] < sr['support'] * 1.02:
            entry_price = round(sr['support'] * 1.01, 2)
            entry_strategy = "الارتداد من الدعم"
        else:
            entry_price = round(sr['closest_fib'] * 1.002, 2)
            entry_strategy = f"مستوى فيبوناتشي {sr['closest_fib_level']}"
        
        stop_loss = round(min(sr['support'] * 0.98, last['Close'] - (1.5 * last['ATR'])), 2)
        take_profit_1 = round(sr['resistance'] * 0.995, 2) if sr['resistance'] > last['Close'] else round(last['Close'] + (2.5 * last['ATR']), 2)
        take_profit_2 = round(take_profit_1 * 1.02, 2)
        
        risk = entry_price - stop_loss
        reward = take_profit_1 - entry_price
        risk_reward = round(reward / risk, 2) if risk > 0 else 0
        
        # شروط الشراء
        buy_conditions = {
            'ema_crossover': last['EMA_20'] > last['EMA_50'],
            'rsi_ok': 45 < last['RSI'] < 70,
            'cmf_ok': last['CMF'] > 0,
            'volume_ok': last['Volume'] > last['Volume_MA'] * 0.7,
            'above_ema50': last['Close'] > last['EMA_50'],
            'near_support': last['Close'] < sr['support'] * 1.05
        }
        
        is_buy = all(buy_conditions.values())
        
        # شروط البيع
        is_sell = (last['Close'] < sr['support'] or last['RSI'] > 75 or last['CMF'] < -0.1) and last['RSI'] > 60
        
        signal = "انتظار ⏳"
        signal_type = "none"
        reasons = []
        
        if is_buy:
            signal = "🔥 شراء فوري"
            signal_type = "buy"
            reasons = [
                f"تقاطع EMA 20 فوق 50 ({round(last['EMA_20'], 2)} > {round(last['EMA_50'], 2)})",
                f"RSI {round(last['RSI'], 1)} (زخم إيجابي)",
                f"دعم عند {sr['support']} | فيبوناتشي {sr['closest_fib_level']} عند {sr['closest_fib']}",
                f"حجم التداول {round(last['Volume'] / last['Volume_MA'], 1)}x المتوسط"
            ]
        elif is_sell:
            signal = "⚠️ بيع/خروج"
            signal_type = "sell"
            reasons = [
                f"كسر الدعم {sr['support']}" if last['Close'] < sr['support'] else f"RSI {round(last['RSI'], 1)} (تشبع)",
                "CMF سالب (سيولة خارجة)" if last['CMF'] < -0.1 else "تحت المتوسط 50"
            ]
        
        info = stock.info
        eps = info.get('trailingEps', 'غير متاح')
        pe = info.get('trailingPE', 'غير متاح')
        
        return {
            'ticker': ticker,
            'name': name,
            'price': round(last['Close'], 2),
            'ema_20': round(last['EMA_20'], 2),
            'ema_50': round(last['EMA_50'], 2),
            'rsi': round(last['RSI'], 1),
            'cmf': round(last['CMF'], 3),
            'atr': round(last['ATR'], 2),
            'volume_ratio': round(last['Volume'] / last['Volume_MA'], 1),
            'change_1d': round(last['Price_Change_1d'], 2),
            'change_5d': round(last['Price_Change_5d'], 2),
            'change_20d': round(last['Price_Change_20d'], 2),
            'support': sr['support'],
            'resistance': sr['resistance'],
            'avg_support': sr['avg_support'],
            'avg_resistance': sr['avg_resistance'],
            'highest_50': sr['highest_50'],
            'lowest_50': sr['lowest_50'],
            'closest_fib': sr['closest_fib'],
            'closest_fib_level': sr['closest_fib_level'],
            'entry_price': entry_price,
            'entry_strategy': entry_strategy,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'risk_reward': risk_reward,
            'signal': signal,
            'signal_type': signal_type,
            'reasons': reasons,
            'eps': eps,
            'pe': pe,
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
    
    # توقيت مصر
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
                lines.append(f"   💰 {stock_result['price']} جنيه")
                lines.append(f"   📊 RSI: {stock_result['rsi']} | CMF: {stock_result['cmf']}")
                lines.append(f"   📈 حجم: {stock_result['volume_ratio']}x المتوسط")
                lines.append(f"   📉 دعم: {stock_result['support']} | مقاومة: {stock_result['resistance']}")
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
        f"📉 أقرب دعم: {r['support']} جنيه",
        f"📈 أقرب مقاومة: {r['resistance']} جنيه",
        f"📊 مستوى فيبوناتشي: {r['closest_fib_level']} عند {r['closest_fib']} جنيه",
        f"📊 RSI: {r['rsi']} | CMF: {r['cmf']}",
        f"📈 حجم التداول: {r['volume_ratio']}x المتوسط",
    ]
    
    if r['reasons']:
        lines.append("📝 الأسباب:")
        for reason in r['reasons'][:4]:
            lines.append(f"  ✅ {reason}")
    
    # توقيت مصر
    egypt_tz = pytz.timezone('Africa/Cairo')
    now = datetime.now(egypt_tz)
    lines.append("")
    lines.append(f"⏰ {now.strftime('%H:%M:%S')}")
    
    return "\n".join(lines)

# ==================== منع التكرار ====================
def is_duplicate_run():
    """التحقق من عدم تكرار التشغيل خلال 5 دقائق"""
    lock_file = "last_run.json"
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                data = json.load(f)
                last_run = datetime.fromisoformat(data['last_run'])
                if (datetime.now() - last_run).seconds < 300:  # 5 دقائق
                    return True
        except:
            pass
    return False

def save_run_time():
    """حفظ وقت التشغيل الحالي"""
    lock_file = "last_run.json"
    with open(lock_file, 'w') as f:
        json.dump({'last_run': datetime.now().isoformat()}, f)

# ==================== الدالة الرئيسية ====================
def main():
    print("🚀 بدء تشغيل النظام المتكامل...")
    
    # منع التكرار
    if is_duplicate_run():
        print("⏳ تم التشغيل مؤخراً، تخطي...")
        return
    
    # ====== المرحلة 1: حساب السيولة ======
    top_liquid = get_top_liquid_stocks(limit=8)
    print(f"✅ تم اختيار {len(top_liquid)} سهم عالي السيولة")
    
    # ====== المرحلة 2: تحليل السوق العام ======
    trend = market_trend()
    print(f"🌍 اتجاه السوق: {trend}")
    
    # ====== المرحلة 3: تحليل الأسهم ======
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
            
            time.sleep(0.5)
    
    # ====== المرحلة 4: التقرير الصباحي ======
    report = morning_report(top_liquid, all_results, trend)
    send_telegram_message(report)
    print("✅ تم إرسال التقرير الصباحي")
    
    # ====== المرحلة 5: ملخص ======
    buy_count = len([r for r in all_results if r and r['is_buy']])
    sell_count = len([r for r in all_results if r and r['is_sell']])
    
    # توقيت مصر
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
    
    # حفظ وقت التشغيل
    save_run_time()
    
    print(f"🏁 انتهى التشغيل. الإشارات: شراء {buy_count} | بيع {sell_count} | تنبيهات {alerts_sent}")

if __name__ == "__main__":
    main()
