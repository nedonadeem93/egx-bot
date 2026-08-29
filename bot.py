import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests
import os
from datetime import datetime
import time
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ==================== إعدادات التليجرام ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    if len(message) > 4000:
        parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for part in parts:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": part, "parse_mode": "Markdown"}
            try:
                requests.post(url, json=payload, timeout=10)
            except Exception as e:
                print(f"❌ خطأ: {e}")
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"❌ خطأ: {e}")

# ==================== حساب الدعم والمقاومة ====================
def calculate_support_resistance(df, lookback=50):
    """حساب مناطق الدعم والمقاومة باستخدام أعلى وأدنى سعر"""
    # أعلى وأدنى سعر خلال الفترة
    high = df['High'].tail(lookback)
    low = df['Low'].tail(lookback)
    
    # المقاومة: أعلى 3 قمم
    resistance_levels = []
    for i in range(3, len(high)):
        if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and \
           high.iloc[i] > high.iloc[i-3] and high.iloc[i] > high.iloc[i+1] if i+1 < len(high) else True:
            resistance_levels.append(high.iloc[i])
    
    # الدعم: أدنى 3 قيعان
    support_levels = []
    for i in range(3, len(low)):
        if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and \
           low.iloc[i] < low.iloc[i-3] and low.iloc[i] < low.iloc[i+1] if i+1 < len(low) else True:
            support_levels.append(low.iloc[i])
    
    # أقرب دعم ومقاومة للسعر الحالي
    current_price = df['Close'].iloc[-1]
    
    closest_resistance = None
    closest_support = None
    
    if resistance_levels:
        # أقرب مقاومة فوق السعر
        above_resistance = [r for r in resistance_levels if r > current_price]
        if above_resistance:
            closest_resistance = min(above_resistance)
    
    if support_levels:
        # أقرب دعم تحت السعر
        below_support = [s for s in support_levels if s < current_price]
        if below_support:
            closest_support = max(below_support)
    
    # حساب متوسط الدعم والمقاومة (للتأكيد)
    avg_resistance = np.mean(resistance_levels) if resistance_levels else None
    avg_support = np.mean(support_levels) if support_levels else None
    
    return {
        'resistance': round(closest_resistance, 2) if closest_resistance else None,
        'support': round(closest_support, 2) if closest_support else None,
        'avg_resistance': round(avg_resistance, 2) if avg_resistance else None,
        'avg_support': round(avg_support, 2) if avg_support else None,
        'current_price': round(current_price, 2)
    }

# ==================== تحديد سعر الدخول والخروج المثالي ====================
def calculate_ideal_entry_exit(df, sr_levels):
    """حساب سعر الدخول والخروج المثالي"""
    current_price = df['Close'].iloc[-1]
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1]
    
    # ====== سعر الدخول المثالي ======
    # استراتيجيات الدخول:
    # 1. الدخول عند اختراق المقاومة (إذا كان السهم قوي)
    # 2. الدخول عند الدعم (إذا كان السهم في تصحيح)
    
    entry_price = current_price  # افتراضي
    
    # استراتيجية 1: الدخول عند اختراق المقاومة + 1% (تأكيد الاختراق)
    if sr_levels['resistance'] and current_price > sr_levels['resistance']:
        entry_price = round(sr_levels['resistance'] * 1.01, 2)
        entry_strategy = "اختراق المقاومة"
    
    # استراتيجية 2: الدخول عند الدعم (في حالة التصحيح)
    elif sr_levels['support'] and current_price < sr_levels['support'] * 1.05:
        entry_price = round(sr_levels['support'] * 1.01, 2)
        entry_strategy = "الشراء من الدعم"
    
    # استراتيجية 3: الدخول عند كسر EMA 20 (في حالة الزخم)
    else:
        ema_20 = ta.ema(df['Close'], length=20).iloc[-1]
        if current_price > ema_20 and current_price < ema_20 * 1.02:
            entry_price = round(ema_20, 2)
            entry_strategy = "عند EMA 20"
        else:
            entry_price = round(current_price, 2)
            entry_strategy = "السعر الحالي"
    
    # ====== سعر الخروج المثالي ======
    # استراتيجيات الخروج:
    # 1. الخروج عند المقاومة التالية (جني أرباح)
    # 2. الخروج عند نسبة ربح محددة (2:1 أو 3:1)
    # 3. الخروج عند كسر الدعم (وقف خسارة)
    
    # Stop Loss (وقف الخسارة)
    if sr_levels['support']:
        stop_loss = round(sr_levels['support'] * 0.98, 2)  # 2% تحت الدعم
    else:
        stop_loss = round(current_price - (2 * atr), 2)
    
    # Take Profit (جني الأرباح)
    if sr_levels['resistance']:
        take_profit_1 = sr_levels['resistance']  # المستوى الأول
        take_profit_2 = round(sr_levels['resistance'] * 1.03, 2)  # 3% فوق المقاومة
    else:
        take_profit_1 = round(current_price + (2 * atr), 2)
        take_profit_2 = round(current_price + (3 * atr), 2)
    
    # حساب نسبة المخاطرة/المكافأة
    risk = entry_price - stop_loss
    reward = take_profit_1 - entry_price
    if risk > 0:
        risk_reward_ratio = round(reward / risk, 2)
    else:
        risk_reward_ratio = 0
    
    return {
        'entry_price': entry_price,
        'entry_strategy': entry_strategy,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'risk_reward': risk_reward_ratio,
        'current_price': current_price
    }

# ==================== تحليل السهم المتقدم ====================
def analyze_stock_advanced(ticker, name):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # ====== المؤشرات الفنية الأساسية ======
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
        
        # ====== حساب الدعم والمقاومة ======
        sr_levels = calculate_support_resistance(df)
        
        # ====== حساب سعر الدخول والخروج المثالي ======
        entry_exit = calculate_ideal_entry_exit(df, sr_levels)
        
        # ====== تحديد الإشارة ======
        signal = "انتظار ⏳"
        signal_reasons = []
        
        # شروط الشراء
        if last['Close'] > last['EMA_50'] and last['RSI'] > 50 and last['CMF'] > 0:
            signal = "شراء 🟢"
            signal_reasons.append(f"السهم فوق EMA 50 ({round(last['EMA_50'], 2)})")
            signal_reasons.append(f"RSI {round(last['RSI'], 1)} (زخم إيجابي)")
            signal_reasons.append("CMF موجب (سيولة داخلة)")
        elif last['Close'] < last['EMA_50'] and last['RSI'] < 40:
            signal = "مراقبة للشراء 🟡"
            signal_reasons.append("السهم تحت EMA 50 (تصحيح)")
            signal_reasons.append(f"RSI {round(last['RSI'], 1)} (قريب من التشبع البيعي)")
        
        # ====== المعلومات الأساسية ======
        info = stock.info
        eps = info.get('trailingEps', 'غير متاح')
        pe = info.get('trailingPE', 'غير متاح')
        market_cap = info.get('marketCap', 'غير متاح')
        if market_cap != 'غير متاح':
            market_cap = f"{round(market_cap / 1e9, 2)} مليار جنيه"
        
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
            'signal': signal,
            'signal_reasons': signal_reasons,
            'eps': eps,
            'pe': pe,
            'market_cap': market_cap,
            'support': sr_levels['support'],
            'resistance': sr_levels['resistance'],
            'avg_support': sr_levels['avg_support'],
            'avg_resistance': sr_levels['avg_resistance'],
            'entry_price': entry_exit['entry_price'],
            'entry_strategy': entry_exit['entry_strategy'],
            'stop_loss': entry_exit['stop_loss'],
            'take_profit_1': entry_exit['take_profit_1'],
            'take_profit_2': entry_exit['take_profit_2'],
            'risk_reward': entry_exit['risk_reward']
        }
        
    except Exception as e:
        print(f"❌ خطأ في {ticker}: {e}")
        return None

# ==================== تنسيق التقرير المتقدم ====================
def format_detailed_report(results):
    lines = []
    
    lines.append("📊 *تقرير تحليل البورصة المصرية (EGX)*")
    lines.append(f"📅 *التاريخ:* {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 50)
    lines.append("")
    
    # إحصائيات عامة
    buy_signals = [r for r in results if r and r['signal'] == 'شراء 🟢']
    monitor_signals = [r for r in results if r and r['signal'] == 'مراقبة للشراء 🟡']
    
    lines.append(f"📈 *إجمالي الأسهم:* {len(results)}")
    lines.append(f"🟢 *إشارات شراء:* {len(buy_signals)}")
    lines.append(f"🟡 *إشارات مراقبة:* {len(monitor_signals)}")
    lines.append("")
    lines.append("=" * 50)
    lines.append("")
    
    # ====== تفاصيل كل سهم ======
    for r in results:
        if not r:
            continue
        
        signal_emoji = "🟢" if r['signal'] == 'شراء 🟢' else "🟡" if r['signal'] == 'مراقبة للشراء 🟡' else "⚪"
        
        lines.append(f"{signal_emoji} *{r['name']}* (`{r['ticker']}`)")
        lines.append(f"  💰 السعر الحالي: {r['price']} جنيه")
        lines.append(f"  📈 التغيير اليومي: {r['change_1d']}% | الأسبوعي: {r['change_5d']}% | 20 يوم: {r['change_20d']}%")
        lines.append("")
        lines.append(f"  📊 *المؤشرات الفنية:*")
        lines.append(f"  • RSI: {r['rsi']} | CMF: {r['cmf']}")
        lines.append(f"  • EMA 20: {r['ema_20']} | EMA 50: {r['ema_50']}")
        lines.append(f"  • حجم التداول: {r['volume_ratio']}x المتوسط")
        lines.append("")
        lines.append(f"  🏛️ *الدعم والمقاومة:*")
        if r['support']:
            lines.append(f"  • أقرب دعم: {r['support']} جنيه")
        if r['resistance']:
            lines.append(f"  • أقرب مقاومة: {r['resistance']} جنيه")
        if r['avg_support']:
            lines.append(f"  • متوسط الدعم (50 يوم): {r['avg_support']} جنيه")
        if r['avg_resistance']:
            lines.append(f"  • متوسط المقاومة (50 يوم): {r['avg_resistance']} جنيه")
        lines.append("")
        lines.append(f"  🎯 *سعر الدخول والخروج المثالي:*")
        lines.append(f"  • سعر الدخول: {r['entry_price']} جنيه ({r['entry_strategy']})")
        lines.append(f"  • وقف الخسارة: {r['stop_loss']} جنيه")
        lines.append(f"  • الهدف الأول: {r['take_profit_1']} جنيه")
        lines.append(f"  • الهدف الثاني: {r['take_profit_2']} جنيه")
        lines.append(f"  • نسبة المخاطرة/المكافأة: 1:{r['risk_reward']}")
        lines.append("")
        lines.append(f"  📌 *التوصية:* {r['signal']}")
        if r['signal_reasons']:
            lines.append(f"  📝 الأسباب: {', '.join(r['signal_reasons'])}")
        lines.append("")
        lines.append("-" * 50)
        lines.append("")
    
    # خاتمة
    if buy_signals:
        lines.append("💡 *الخلاصة:* توجد فرص شراء جيدة.")
        lines.append("⚠️ *تذكير المخاطر:*")
        lines.append("• لا تخاطر بأكثر من 2% من رأس المال في صفقة واحدة")
        lines.append("• التزم بوقف الخسارة المحدد")
        lines.append("• قسم الأهداف (خذ ربح جزئي عند الهدف الأول)")
    
    return "\n".join(lines)

# ==================== الدالة الرئيسية ====================
def main():
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
    
    print("🚀 بدء تحليل الأسهم...")
    results = []
    
    for ticker, name in watchlist.items():
        print(f"🔍 تحليل: {name} ({ticker})")
        result = analyze_stock_advanced(ticker, name)
        if result:
            results.append(result)
        time.sleep(0.5)
    
    report = format_detailed_report(results)
    send_telegram_message(report)
    print("✅ تم إرسال التقرير")
    
    buy_signals = [r for r in results if r and r['signal'] == 'شراء 🟢']
    if buy_signals:
        summary = "🔥 *إشارات شراء قوية:*\n"
        for r in buy_signals[:5]:
            summary += f"• {r['name']} - الدخول: {r['entry_price']} | الهدف: {r['take_profit_1']} | وقف: {r['stop_loss']}\n"
        send_telegram_message(summary)
    
    print(f"🏁 انتهى التحليل. عدد الأسهم: {len(results)}")

if __name__ == "__main__":
    main()
