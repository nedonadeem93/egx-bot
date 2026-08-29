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
    """إرسال رسالة مع تقسيمها إذا كانت طويلة"""
    if len(message) > 4000:
        # تقسيم الرسالة الطويلة
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

# ==================== تحليل السهم المتقدم ====================
def analyze_stock_advanced(ticker, name):
    """تحليل متقدم لكل سهم"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo", interval="1d")
        
        if df.empty or len(df) < 30:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # ====== المؤشرات الفنية ======
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['CMF'] = ta.cmf(df['High'], df['Low'], df['Close'], df['Volume'], length=20)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # ====== المؤشرات الإضافية ======
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Price_Change_1d'] = df['Close'].pct_change() * 100
        df['Price_Change_5d'] = df['Close'].pct_change(periods=5) * 100
        df['Price_Change_20d'] = df['Close'].pct_change(periods=20) * 100
        
        last = df.iloc[-1]
        
        # ====== حساب الأداء النسبي ======
        # مقارنة أداء السهم مع EGX30
        try:
            egx = yf.download("^EGX30", period="3mo", interval="1d", progress=False)
            if not egx.empty:
                if isinstance(egx.columns, pd.MultiIndex):
                    egx.columns = egx.columns.get_level_values(0)
                egx_perf = ((egx['Close'].iloc[-1] / egx['Close'].iloc[-20]) - 1) * 100
                stock_perf = last['Price_Change_20d']
                relative_perf = stock_perf - egx_perf
            else:
                relative_perf = 0
        except:
            relative_perf = 0
        
        # ====== تحديد حالة السهم ======
        # 1. اتجاه السعر
        if last['Close'] > last['EMA_50']:
            trend = "صاعد 📈"
        elif last['Close'] < last['EMA_50']:
            trend = "هابط 📉"
        else:
            trend = "محايد ➡️"
        
        # 2. قوة السهم (RSI)
        if last['RSI'] > 70:
            rsi_status = "تشبع شرائي 🔴"
        elif last['RSI'] < 30:
            rsi_status = "تشبع بيعي 🟢"
        elif 50 <= last['RSI'] <= 70:
            rsi_status = "زخم إيجابي 🟡"
        else:
            rsi_status = "ضعيف ⚪"
        
        # 3. السيولة (CMF)
        if last['CMF'] > 0.1:
            cmf_status = "سيولة داخلة بقوة 💰"
        elif last['CMF'] > 0:
            cmf_status = "سيولة داخلة 💵"
        elif last['CMF'] > -0.1:
            cmf_status = "سيولة محايدة ⚖️"
        else:
            cmf_status = "سيولة خارجة 🚫"
        
        # 4. حجم التداول
        volume_ratio = last['Volume'] / last['Volume_MA']
        if volume_ratio > 2:
            volume_status = "نشاط استثنائي 🔥"
        elif volume_ratio > 1.5:
            volume_status = "نشاط عالي 📊"
        elif volume_ratio > 0.8:
            volume_status = "نشاط متوسط 📉"
        else:
            volume_status = "نشاط ضعيف 😴"
        
        # ====== التوصية ======
        signal = "انتظار ⏳"
        signal_reasons = []
        
        if last['Close'] > last['EMA_50'] and last['RSI'] > 50 and last['CMF'] > 0:
            signal = "شراء 🟢"
            signal_reasons.append("السهم فوق EMA 50 (اتجاه صاعد)")
            signal_reasons.append(f"RSI {round(last['RSI'], 1)} (زخم إيجابي)")
            signal_reasons.append("CMF موجب (سيولة داخلة)")
            if volume_ratio > 1.5:
                signal_reasons.append("حجم تداول عالي (نشاط)")
            if relative_perf > 0:
                signal_reasons.append(f"أداء أفضل من السوق بـ {round(relative_perf, 1)}%")
        elif last['Close'] < last['EMA_50'] and last['RSI'] < 40:
            signal = "مراقبة للشراء 🟡"
            signal_reasons.append("السهم تحت EMA 50 (تصحيح)")
            signal_reasons.append(f"RSI {round(last['RSI'], 1)} (قريب من التشبع البيعي)")
            if last['CMF'] > 0:
                signal_reasons.append("سيولة داخلة رغم التراجع (علامة إيجابية)")
        elif last['RSI'] > 75:
            signal = "جني أرباح 🔴"
            signal_reasons.append(f"RSI {round(last['RSI'], 1)} (تشبع شرائي)")
            signal_reasons.append("خطر تصحيح")
        
        # ====== المعلومات الأساسية ======
        info = stock.info
        eps = info.get('trailingEps', 'غير متاح')
        pe = info.get('trailingPE', 'غير متاح')
        market_cap = info.get('marketCap', 'غير متاح')
        if market_cap != 'غير متاح':
            market_cap = f"{round(market_cap / 1e9, 2)} مليار جنيه"
        
        # ====== تجميع النتائج ======
        return {
            'ticker': ticker,
            'name': name,
            'price': round(last['Close'], 2),
            'ema_20': round(last['EMA_20'], 2),
            'ema_50': round(last['EMA_50'], 2),
            'rsi': round(last['RSI'], 1),
            'cmf': round(last['CMF'], 3),
            'atr': round(last['ATR'], 2),
            'volume_ratio': round(volume_ratio, 1),
            'change_1d': round(last['Price_Change_1d'], 2),
            'change_5d': round(last['Price_Change_5d'], 2),
            'change_20d': round(last['Price_Change_20d'], 2),
            'relative_perf': round(relative_perf, 1),
            'trend': trend,
            'rsi_status': rsi_status,
            'cmf_status': cmf_status,
            'volume_status': volume_status,
            'signal': signal,
            'signal_reasons': signal_reasons,
            'eps': eps,
            'pe': pe,
            'market_cap': market_cap
        }
        
    except Exception as e:
        print(f"❌ خطأ في {ticker}: {e}")
        return None

# ==================== تنسيق التقرير المحسن ====================
def format_detailed_report(results):
    """تنسيق تقرير مفصل لكل الأسهم"""
    lines = []
    
    # ====== العنوان ======
    lines.append("📊 *تقرير تحليل البورصة المصرية (EGX)*")
    lines.append(f"📅 *التاريخ:* {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 40)
    lines.append("")
    
    # ====== إحصائيات عامة ======
    buy_signals = [r for r in results if r and r['signal'] == 'شراء 🟢']
    monitor_signals = [r for r in results if r and r['signal'] == 'مراقبة للشراء 🟡']
    sell_signals = [r for r in results if r and r['signal'] == 'جني أرباح 🔴']
    
    lines.append(f"📈 *إجمالي الأسهم:* {len(results)}")
    lines.append(f"🟢 *إشارات شراء:* {len(buy_signals)}")
    lines.append(f"🟡 *إشارات مراقبة:* {len(monitor_signals)}")
    lines.append(f"🔴 *إشارات جني أرباح:* {len(sell_signals)}")
    lines.append("")
    lines.append("=" * 40)
    lines.append("")
    
    # ====== توصيات الشراء ======
    if buy_signals:
        lines.append("🟢 *توصيات الشراء الأقوى:*")
        lines.append("")
        for r in buy_signals[:5]:  # أهم 5 إشارات
            lines.append(f"• *{r['name']}* (`{r['ticker']}`)")
            lines.append(f"  📌 السعر: {r['price']} جنيه | RSI: {r['rsi']}")
            lines.append(f"  📈 الأداء 20 يوم: {r['change_20d']}%")
            if r['relative_perf'] > 0:
                lines.append(f"  ⭐ أفضل من السوق بـ {r['relative_perf']}%")
            for reason in r['signal_reasons'][:2]:
                lines.append(f"  ✅ {reason}")
        lines.append("")
        lines.append("=" * 40)
        lines.append("")
    
    # ====== تفاصيل كل سهم ======
    lines.append("📋 *تفاصيل الأسهم:*")
    lines.append("")
    
    for r in results:
        if not r:
            continue
        
        # إشارة السهم
        signal_emoji = "🟢" if r['signal'] == 'شراء 🟢' else "🟡" if r['signal'] == 'مراقبة للشراء 🟡' else "🔴" if r['signal'] == 'جني أرباح 🔴' else "⚪"
        
        lines.append(f"{signal_emoji} *{r['name']}* (`{r['ticker']}`)")
        lines.append(f"  💰 السعر: {r['price']} جنيه | التغيير اليومي: {r['change_1d']}%")
        lines.append(f"  📊 RSI: {r['rsi']} | {r['rsi_status']}")
        lines.append(f"  💵 CMF: {r['cmf']} | {r['cmf_status']}")
        lines.append(f"  📊 حجم التداول: {r['volume_ratio']}x المتوسط | {r['volume_status']}")
        lines.append(f"  📈 الأداء (20 يوم): {r['change_20d']}%")
        if r['relative_perf'] != 0:
            lines.append(f"  📊 الأداء النسبي: {r['relative_perf']}% مقابل السوق")
        lines.append(f"  🏛️ P/E: {r['pe']} | EPS: {r['eps']}")
        lines.append(f"  💼 القيمة السوقية: {r['market_cap']}")
        lines.append(f"  📌 التوصية: {r['signal']}")
        if r['signal_reasons']:
            lines.append(f"  📝 الأسباب: {', '.join(r['signal_reasons'])}")
        lines.append("")
    
    lines.append("=" * 40)
    lines.append("")
    
    # ====== خاتمة ======
    if buy_signals:
        lines.append("💡 *الخلاصة:* توجد فرص شراء جيدة. راجع التوصيات أعلاه.")
        lines.append("⚠️ *تذكير:* استخدم وقف خسارة 2-3% ولا تخاطر بأكثر من 2% من رأس المال في صفقة واحدة.")
    elif monitor_signals:
        lines.append("💡 *الخلاصة:* السوق في حالة ترقب. راقب الأسهم التي في منطقة شراء.")
        lines.append("👀 *نصيحة:* انتظر تأكيد الاتجاه قبل الدخول.")
    else:
        lines.append("💡 *الخلاصة:* لا توجد فرص واضحة حالياً. استمر في المراقبة.")
    
    return "\n".join(lines)

# ==================== الدالة الرئيسية ====================
def main():
    """تشغيل البوت مع التقرير المحسن"""
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
    
    # إرسال التقرير المحسن
    report = format_detailed_report(results)
    send_telegram_message(report)
    print("✅ تم إرسال التقرير")
    
    # إرسال ملخص مختصر للإشارات القوية
    buy_signals = [r for r in results if r and r['signal'] == 'شراء 🟢']
    if buy_signals:
        summary = "🔥 *إشارات شراء قوية:*\n"
        for r in buy_signals[:3]:
            summary += f"• {r['name']} ({r['ticker']}) - {r['price']} جنيه\n"
        send_telegram_message(summary)
    
    print(f"🏁 انتهى التحليل. عدد الأسهم: {len(results)}")

if __name__ == "__main__":
    main()
