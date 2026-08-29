import os
import time
import logging
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests

# ---------------- إعداد اللوج (عشان نشوف الأخطاء بدل ما تتبلع بصمت) ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ---------------- بيانات بوت تليجرام (من environment variables، مش مكتوبة في الكود) ----------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise SystemExit(
        "❌ لازم تحط TELEGRAM_TOKEN و TELEGRAM_CHAT_ID كـ environment variables "
        "(أو GitHub Secrets لو شغال على Actions) قبل ما تشغل البوت."
    )

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def send_telegram_message(message: str) -> None:
    """يبعت رسالة على تليجرام، مع إعادة محاولة بسيطة لو فشل الاتصال."""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    for attempt in range(3):
        try:
            resp = requests.post(TELEGRAM_API_URL, json=payload, timeout=15)
            if resp.status_code == 200:
                return
            log.warning("Telegram API returned status %s: %s", resp.status_code, resp.text)
        except requests.RequestException as e:
            log.warning("Attempt %s: failed to send Telegram message: %s", attempt + 1, e)
        time.sleep(2)
    log.error("Failed to send Telegram message after 3 attempts.")


# ---------------- 1. فحص الاتجاه العام للمؤشرات ----------------
indices = {
    "^EGX30": "مؤشر EGX 30",
    "^EGX70": "مؤشر EGX 70 EWI",
    "^EGX100": "مؤشر EGX 100 EWI",
}

index_status_lines = ["📊 *تقرير حالة المؤشرات الرئيسية (EGX):*"]

for idx_symbol, idx_name in indices.items():
    try:
        idx_df = yf.download(idx_symbol, period="3mo", interval="1d", progress=False)
        if idx_df.empty or len(idx_df) < 50:
            log.warning("Not enough data for index %s, skipping.", idx_symbol)
            continue

        if isinstance(idx_df.columns, pd.MultiIndex):
            idx_df.columns = idx_df.columns.get_level_values(0)

        idx_df["EMA_50"] = ta.ema(idx_df["Close"], length=50)
        last_close = idx_df["Close"].iloc[-1]
        last_ema50 = idx_df["EMA_50"].iloc[-1]

        if pd.isna(last_close) or pd.isna(last_ema50):
            log.warning("NaN values for index %s, skipping.", idx_symbol)
            continue

        status = "🟢 صاعد (أعلى من EMA 50)" if last_close > last_ema50 else "🔴 تصحيحي/هابط (أدنى من EMA 50)"
        index_status_lines.append(f"• *{idx_name}:* {status}")
    except Exception as e:
        log.error("Error processing index %s: %s", idx_symbol, e)
        continue

send_telegram_message("\n".join(index_status_lines))

# ---------------- 2. قائمة الأسهم ----------------
watchlist = [
    "COMI.CA", "FWRY.CA", "HRHO.CA", "CIEB.CA", "ADIB.CA", "TMGH.CA", "HELI.CA",
    "PHDC.CA", "ORAS.CA", "MNHD.CA", "EMFD.CA", "MFPC.CA", "ABUK.CA", "ESRS.CA",
    "SWDY.CA", "GBCO.CA", "ETEL.CA", "EKHO.CA", "AMOC.CA", "DSCW.CA", "OIH.CA",
    "ACGC.CA", "EGAL.CA", "ALCN.CA", "RTVC.CA", "ISPH.CA", "CLHO.CA", "RMDA.CA",
    "PHAR.CA", "RAYA.CA", "EDIT.CA", "JUFO.CA", "DOMT.CA", "EAST.CA", "ORWE.CA",
    "SKPC.CA", "CCRS.CA", "KIMA.CA", "CANA.CA", "EGBE.CA", "ATQA.CA", "UNIT.CA",
    "MPRC.CA", "DCHE.CA", "ASCM.CA", "UEGC.CA", "BLCY.CA",
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
    "ASCM.CA": "أسكوم", "UEGC.CA": "السباعية للصناعات", "BLCY.CA": "بلتون القابضة",
}

log.info("--- Running Full EGX 30 / 70 / 100 Scanner ---")
signals_found = 0

for ticker in watchlist:
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo", interval="1d")

        if df.empty or len(df) < 50:
            log.info("Skipping %s: not enough historical data.", ticker)
            continue

        # 1. المؤشرات الفنية
        df["EMA_20"] = ta.ema(df["Close"], length=20)
        df["EMA_50"] = ta.ema(df["Close"], length=50)
        df["RSI"] = ta.rsi(df["Close"], length=14)
        df["CMF"] = ta.cmf(df["High"], df["Low"], df["Close"], df["Volume"], length=20)
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)

        last = df.iloc[-1]

        # تأكيد إن المؤشرات مالهاش قيم ناقصة قبل ما نكمل
        required_fields = ["EMA_20", "EMA_50", "RSI", "CMF", "ATR", "Close"]
        if last[required_fields].isna().any():
            log.info("Skipping %s: NaN values in indicators.", ticker)
            continue

        # 2. فحص التقاطع الأسبوعي (آخر 5 جلسات تداول)
        recent_df = df.tail(6)
        has_weekly_crossover = False
        for i in range(1, len(recent_df)):
            prev_ema20, prev_ema50 = recent_df["EMA_20"].iloc[i - 1], recent_df["EMA_50"].iloc[i - 1]
            curr_ema20, curr_ema50 = recent_df["EMA_20"].iloc[i], recent_df["EMA_50"].iloc[i]
            if pd.isna(prev_ema20) or pd.isna(prev_ema50) or pd.isna(curr_ema20) or pd.isna(curr_ema50):
                continue
            if prev_ema20 <= prev_ema50 and curr_ema20 > curr_ema50:
                has_weekly_crossover = True
                break

        # 3. الشرط الفني المكتمل
        cond_tech = has_weekly_crossover and (last["RSI"] > 50) and (last["CMF"] > 0)

        if not cond_tech:
            continue

        signals_found += 1
        entry_price = round(last["Close"], 2)
        atr_value = last["ATR"]

        stop_loss = round(entry_price - (1.5 * atr_value), 2)
        take_profit = round(entry_price + (3.0 * atr_value), 2)
        arabic_name = names_map.get(ticker, ticker)

        # 4. فحص المالية وتحديد درجة الخطورة
        try:
            info = stock.info
        except Exception as e:
            log.warning("Could not fetch info for %s: %s", ticker, e)
            info = {}

        eps = info.get("trailingEps", "N/A")
        pe_ratio = info.get("trailingPE", "N/A")

        is_high_risk = not isinstance(eps, (int, float)) or eps <= 0

        pe_text = str(round(pe_ratio, 2)) if isinstance(pe_ratio, (int, float)) else "غير متاح"
        eps_text = str(round(eps, 2)) if isinstance(eps, (int, float)) else "غير متاح"

        # 5. صياغة التنبيه حسب نوع الصفقة
        if is_high_risk:
            lines = [
                "⚠️ *إشارة مضاربة سريعة (عالية الخطورة)* ⚡",
                f"📈 *السهم:* {arabic_name} (`{ticker}`)",
                "----------------------------------",
                f"📌 *سعر الإغلاق:* {entry_price} جنيه",
                f"🎯 *الهدف المقترح:* {take_profit} جنيه",
                f"🛑 *وقف الخسارة (الالتزام صارم):* {stop_loss} جنيه",
                "----------------------------------",
                f"🔴 *سبب تنبيه الخطورة:* النتائج المالية ضعيفة أو غير متاحة (EPS: {eps_text})",
                "💡 *توصية المضاربة:* احرص على التداول بحجم كمية صغير والتزام تام بوقف الخسارة.",
            ]
        else:
            lines = [
                "🚀 *إشارة استثمارية / اتجاه مؤكد (مخاطرة متوازنة)* 🔥",
                f"📈 *السهم:* {arabic_name} (`{ticker}`)",
                "----------------------------------",
                f"📌 *سعر الإغلاق:* {entry_price} جنيه",
                f"🎯 *الهدف المقترح:* {take_profit} جنيه",
                f"🛑 *وقف الخسارة:* {stop_loss} جنيه",
                "----------------------------------",
                f"🏛️ *التحليل الأساسي:* EPS: {eps_text} | P/E: {pe_text}",
                f"📊 *التحليل الفني:* RSI: {round(last['RSI'], 1)} | السيولة (CMF) إيجابية",
            ]

        msg = "\n".join(lines)
        send_telegram_message(msg)
        log.info("Signal sent for: %s", ticker)

    except Exception as e:
        log.error("Error processing %s: %s", ticker, e)
        continue

    # مهلة بسيطة بين كل سهم والتاني عشان نقلل احتمال rate limiting من Yahoo Finance
    time.sleep(1)

if signals_found == 0:
    send_telegram_message(
        "✅ *تقرير الفحص الأسبوعي:* لم تُكتشف أي إشارات دخول جديدة (استثمارية أو مضاربة) تنطبق عليها الشروط."
    )

log.info("EGX Scan Complete. Total Signals: %s", signals_found)
