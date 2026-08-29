import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests
import os
from datetime import datetime, timedelta
import time
import json
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
def get_top_liquid_stocks(limit=10):
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
        "BLCY.CA": "بلتون القابضة",
        "ACGC.CA": "العربية لحجيج القطن",
        "EGAL.CA": "مصر للألومنيوم",
        "ALCN.CA": "الإسكندرية لتداول البضائع",
        "ATQA.CA": "مصر الوطنية للصلب",
        "UNIT.CA": "المتحدة للإسكان",
        "MPRC.CA": "إم إم جروب",
        "DCHE.CA": "السماد والصناعات الكيماوية",
        "ASCM.CA": "أسكوم",
        "UEGC.CA": "السباعية للصناعات"
    }
    
    print("🔍 جاري حساب السيولة...")
    stock_volumes = []
    
    for ticker, name in all_stocks.items():
        try:
            # جلب آخر 5 أيام
            stock = yf.Ticker(ticker)
            df = stock.history(period="5d", interval="1d", progress=False)
            
            if df.empty:
                print(f"  ⚠️ {name}: لا توجد بيانات")
                continue
            
            # تنظيف الأعمدة
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # حساب متوسط قيمة التداول (السعر × الحجم)
            if 'Volume' in df.columns and 'Close' in df.columns:
                # استخدام آخر 3 أيام فقط (لتجنب الأيام الفارغة)
                recent_df = df.tail(3)
                avg_volume = recent_df['Volume'].mean()
                avg_price = recent_df['Close'].mean()
                
                if avg_volume > 0 and avg_price > 0:
                    avg_value = avg_volume * avg_price
                    stock_volumes.append((ticker, name, avg_value))
                    print(f"  ✅ {name}: {avg_value:,.0f} جنيه")
                else:
                    print(f"  ⚠️ {name}: حجم أو سعر صفر")
            else:
                print(f"  ⚠️ {name}: أعمدة غير مكتملة")
                
        except Exception as e:
            print(f"  ❌ فشل {ticker}: {str(e)[:50]}")
        
        time.sleep(0.5)  # تأخير لتجنب الحظر
    
    # ترتيب حسب قيمة التداول (تنازلي)
    stock_volumes.sort(key=lambda x: x[2], reverse=True)
    
    # اختيار الأعلى سيولة
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

# ==================== تحليل السهم ====================
def analyze_stock(ticker, name, is_alert=False):
    """تحليل سهم واحد وتوليد إشارة"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # ====== المؤشرات الفنية ======
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
        high = df['High'].tail(30)
        low = df['Low'].tail(30)
        resistance = high.max()
        support = low.min()
        
        # ====== حساب سعر الدخول ======
        entry_price = last['Close']
        
        # ====== شروط الدخول (شراء) ======
        buy_conditions = {
            'ema_crossover': last['EMA_20'] > last['EMA_50'],
            'rsi_ok': 45 < last['RSI'] < 70,
            'cmf_ok': last['CMF'] > 0,
            'volume_ok': last['Volume'] > last['Volume_MA'] * 0.7,
            'above_ema50': last['Close'] > last['EMA_50']
        }
        
        is_buy = all(buy_conditions.values())
        
        # ====== شروط الخروج (بيع) ======
        sell_conditions = {
            'below_ema50': last['Close'] < last['EMA_50'],
            'rsi_sell': last['RSI'] > 75,
            'cmf_sell': last['CMF'] < -0.1,
            'below_support': last['Close'] < support
        }
        
        is_sell = any(sell_conditions.values()) and last['RSI'] > 60
        
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
                "CMF موجب (سيولة داخلة)",
                f"حجم التداول {round(last['Volume'] / last['Volume_MA'], 1)}x المتوسط"
            ]
        elif is_sell:
            signal = "⚠️ بيع/خروج"
            signal_type = "sell"
            reasons = [
                f"RSI {round(last['RSI'], 1)} (تشبع شرائي)" if last['RSI'] > 75 else "كسر الدعم",
                "CMF سالب (سيولة خارجة)" if last['CMF'] < -0.1 else "تحت المتوسط 50"
            ]
        
        # ====== المعلومات الأساسية ======
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
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'entry_price': round(last['Close'] * 1.002, 2),
            'stop_loss': round(last['Close'] - (1.5 * last['ATR']), 2),
            'take_profit': round(last['Close'] + (2.5 * last['ATR']), 2),
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
    
    lines.append("🌅 *التقرير الصباحي - البورصة المصرية*")
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"🌍 *اتجاه السوق العام:* {trend}")
    lines.append("=" * 50)
    lines.append("")
    
    # ====== الأسهم الأكثر سيولة ======
    if top_liquid:
        lines.append("🔥 *الأسهم الأكثر سيولة (للمراقبة اليومية):*")
        for i, (ticker, name) in enumerate(top_liquid.items(), 1):
            # البحث عن السهم في النتائج
            stock_result = next((r for r in all_results if r and r['ticker'] == ticker), None)
            if stock_result:
                # تحديد اتجاه السهم
                trend_emoji = "📈" if stock_result['above_ema50'] else "📉"
                lines.append(f"{i}. {trend_emoji} *{name}* (`{ticker}`)")
                lines.append(f"   💰 {stock_result['price']} جنيه | حجم: {stock_result['volume_ratio']}x | RSI: {stock_result['rsi']}")
                lines.append(f"   📊 الدعم: {stock_result['support']} | المقاومة: {stock_result['resistance']}")
            else:
                lines.append(f"{i}. {name} (`{ticker}`)")
        lines.append("")
    else:
        lines.append("⚠️ *تعذر حساب السيولة - استخدم القائمة اليدوية:*")
        default_liquid = ["COMI.CA", "TMGH.CA", "HRHO.CA", "CIEB.CA", "ADIB.CA", "PHDC.CA", "ORAS.CA"]
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
            lines.append(f"  💰 {r['price']} جنيه | RSI: {r['rsi']} | حجم: {r['volume_ratio']}x")
            lines.append(f"  📈 الأداء 20 يوم: {r['change_20d']}%")
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
            lines.append(f"  💰 {r['price']} جنيه | RSI: {r['rsi']}")
            if r['reasons']:
                lines.append(f"  ⚠️ {r['reasons'][0]}")
        lines.append("")
    
    # ====== ملخص سريع ======
    lines.append("=" * 50)
    lines.append("📊 *ملخص سريع:*")
    lines.append(f"• إجمالي الأسهم: {len(all_results)}")
    lines.append(f"• إشارات شراء: {len(buy_signals)}")
    lines.append(f"• إشارات بيع: {len(sell_signals)}")
    lines.append("")
    
    # ====== نصائح اليوم ======
    lines.append("💡 *نصائح اليوم:*")
    if trend == "صاعد 🟢":
        lines.append("• السوق في اتجاه صاعد - ركز على إشارات الشراء")
        lines.append("• استهدف الأسهم القيادية عالية السيولة")
    elif trend == "هابط 🔴":
        lines.append("• السوق في اتجاه هابط - قلل حجم الصفقات")
        lines.append("• ركز على حماية رأس المال")
        lines.append("• انتظر تأكيد انعكاس الاتجاه قبل الشراء")
    else:
        lines.append("• السوق في حالة محايدة - انتظر وضوح الاتجاه")
        lines.append("• ركز على الأسهم القوية نسبياً")
    
    lines.append("• لا تدخل في صفقة بدون وقف خسارة")
    lines.append("• خذ ربح جزئي عند تحقيق الهدف الأول")
    lines.append(f"• وقت التحديث القادم: {datetime.now().strftime('%H:%M')}")
    
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
        f"🎯 سعر الدخول المقترح: {r['entry_price']} جنيه",
        f"🛑 وقف الخسارة: {r['stop_loss']} جنيه",
        f"🏆 الهدف الأول: {r['take_profit']} جنيه",
        "----------------------------------",
        f"📊 RSI: {r['rsi']} | CMF: {r['cmf']}",
        f"📈 حجم التداول: {r['volume_ratio']}x المتوسط",
        f"📉 الدعم: {r['support']} | المقاومة: {r['resistance']}",
    ]
    
    if r['reasons']:
        lines.append("📝 الأسباب:")
        for reason in r['reasons'][:3]:
            lines.append(f"  ✅ {reason}")
    
    lines.append("")
    lines.append(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    
    return "\n".join(lines)

# ==================== الدالة الرئيسية ====================
def main():
    print("🚀 بدء تشغيل النظام المتكامل...")
    
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
            
            # ====== تنبيهات فورية للأسهم عالية السيولة ======
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
    
    # ====== المرحلة 5: تقرير التنبيهات ======
    if alerts_sent > 0:
        alert_summary = f"🔔 *تنبيهات اليوم:* {alerts_sent} تنبيه تم إرسالها"
        send_telegram_message(alert_summary)
    
    # ====== المرحلة 6: ملخص التحليل ======
    buy_count = len([r for r in all_results if r and r['is_buy']])
    sell_count = len([r for r in all_results if r and r['is_sell']])
    
    summary = f"""
📊 *ملخص التحليل:*
• إجمالي الأسهم المحللة: {len(all_results)}
• إشارات شراء: {buy_count}
• إشارات بيع: {sell_count}
• تنبيهات مرسلة: {alerts_sent}
• اتجاه السوق: {trend}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    send_telegram_message(summary)
    print("✅ تم إرسال الملخص")
    
    print(f"🏁 انتهى التشغيل. الإشارات: شراء {buy_count} | بيع {sell_count} | تنبيهات {alerts_sent}")

if __name__ == "__main__":
    main()
