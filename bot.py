import os
import time
import logging
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests

# ---------------- ط¥ط¹ط¯ط§ط¯ ط§ظ„ظ„ظˆط¬ (ط¹ط´ط§ظ† ظ†ط´ظˆظپ ط§ظ„ط£ط®ط·ط§ط، ط¨ط¯ظ„ ظ…ط§ طھطھط¨ظ„ط¹ ط¨طµظ…طھ) ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ---------------- ط¨ظٹط§ظ†ط§طھ ط¨ظˆطھ طھظ„ظٹط¬ط±ط§ظ… (ظ…ظ† environment variablesطŒ ظ…ط´ ظ…ظƒطھظˆط¨ط© ظپظٹ ط§ظ„ظƒظˆط¯) ----------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise SystemExit(
        "â‌Œ ظ„ط§ط²ظ… طھط­ط· TELEGRAM_TOKEN ظˆ TELEGRAM_CHAT_ID ظƒظ€ environment variables "
        "(ط£ظˆ GitHub Secrets ظ„ظˆ ط´ط؛ط§ظ„ ط¹ظ„ظ‰ Actions) ظ‚ط¨ظ„ ظ…ط§ طھط´ط؛ظ„ ط§ظ„ط¨ظˆطھ."
    )

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def send_telegram_message(message: str) -> None:
    """ظٹط¨ط¹طھ ط±ط³ط§ظ„ط© ط¹ظ„ظ‰ طھظ„ظٹط¬ط±ط§ظ…طŒ ظ…ط¹ ط¥ط¹ط§ط¯ط© ظ…ط­ط§ظˆظ„ط© ط¨ط³ظٹط·ط© ظ„ظˆ ظپط´ظ„ ط§ظ„ط§طھطµط§ظ„."""
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


# ---------------- 1. ظپط­طµ ط§ظ„ط§طھط¬ط§ظ‡ ط§ظ„ط¹ط§ظ… ظ„ظ„ظ…ط¤ط´ط±ط§طھ ----------------
indices = {
    "^EGX30": "ظ…ط¤ط´ط± EGX 30",
    "^EGX70": "ظ…ط¤ط´ط± EGX 70 EWI",
    "^EGX100": "ظ…ط¤ط´ط± EGX 100 EWI",
}

index_status_lines = ["ًں“ٹ *طھظ‚ط±ظٹط± ط­ط§ظ„ط© ط§ظ„ظ…ط¤ط´ط±ط§طھ ط§ظ„ط±ط¦ظٹط³ظٹط© (EGX):*"]

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

        status = "ًںں¢ طµط§ط¹ط¯ (ط£ط¹ظ„ظ‰ ظ…ظ† EMA 50)" if last_close > last_ema50 else "ًں”´ طھطµط­ظٹط­ظٹ/ظ‡ط§ط¨ط· (ط£ط¯ظ†ظ‰ ظ…ظ† EMA 50)"
        index_status_lines.append(f"â€¢ *{idx_name}:* {status}")
    except Exception as e:
        log.error("Error processing index %s: %s", idx_symbol, e)
        continue

send_telegram_message("\n".join(index_status_lines))

# ---------------- 2. ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط³ظ‡ظ… ----------------
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
    "COMI.CA": "ط§ظ„ط¨ظ†ظƒ ط§ظ„طھط¬ط§ط±ظٹ ط§ظ„ط¯ظˆظ„ظٹ", "FWRY.CA": "ظپظˆط±ظٹ", "HRHO.CA": "ظ‡ظٹط±ظ…ظٹط³",
    "CIEB.CA": "ظƒط±ظٹط¯ظٹ ط£ط¬ط±ظٹظƒظˆظ„", "EGBE.CA": "ط§ظ„ظ…طµط±ظٹ ظ„ظ„ظپظٹط´ط©", "ADIB.CA": "ظ…طµط±ظپ ط£ط¨ظˆط¸ط¨ظٹ ط§ظ„ط¥ط³ظ„ط§ظ…ظٹ",
    "CANA.CA": "ط¨ظ†ظƒ ظ‚ظ†ط§ط© ط§ظ„ط³ظˆظٹط³", "TMGH.CA": "ط·ظ„ط¹طھ ظ…طµط·ظپظ‰", "HELI.CA": "ظ…طµط± ظ„ظ„ط¬ط¯ظٹط¯ط© ظ„ظ„ط¥ط³ظƒط§ظ†",
    "PHDC.CA": "ط¨ط§ظ„ظ… ظ‡ظٹظ„ط²", "ORAS.CA": "ط£ظˆط±ط§ط³ظƒظˆظ… ظ„ظ„ط¥ظ†ط´ط§ط،", "MNHD.CA": "ظ…ط¯ظٹظ†ط© ظ…طµط±",
    "EMFD.CA": "ط¥ط¹ظ…ط§ط± ظ…طµط±", "CCRS.CA": "ط³ظٹط¯ظٹ ظƒط±ظٹط±", "MFPC.CA": "ظ…ظˆط¨ظƒظˆ",
    "ABUK.CA": "ط£ط¨ظˆ ظ‚ظٹط± ظ„ظ„ط£ط³ظ…ط¯ط©", "KIMA.CA": "ظƒظٹظ…ط§", "SKPC.CA": "ط³ظٹط¯ظٹ ظƒط±ظٹط± ظ„ظ„ط¨ظٹطھط±ظˆظƒظٹظ…ط§ظˆظٹط§طھ",
    "ESRS.CA": "ط¹ط² ط­ط¯ظٹط¯", "AMOC.CA": "ط£ظ…ظˆظƒ", "EDIT.CA": "ط¥ظٹط¯ظٹطھط§",
    "JUFO.CA": "ط¬ظ‡ظٹظ†ط©", "DOMT.CA": "ط¯ظˆظ…طھظٹ", "EAST.CA": "ط§ظ„ط´ط±ظ‚ظٹط© ظ„ظ„ط¯ط®ط§ظ†",
    "ORWE.CA": "ط§ظ„ظ†ط³ط§ط¬ظˆظ† ط§ظ„ط´ط±ظ‚ظٹظˆظ†", "ISPH.CA": "ط§ط¨ظ† ط³ظٹظ†ط§ ظپط§ط±ظ…ط§", "CLHO.CA": "ظƒظ„ظٹظˆط¨ط§طھط±ط§",
    "RMDA.CA": "ط±ط§ظ…ط¯ط§", "PHAR.CA": "ط£ظٹط¨ظƒط³ ظپط§ط±ظ…ط§", "ETEL.CA": "ط§ظ„ظ…طµط±ظٹط© ظ„ظ„ط§طھطµط§ظ„ط§طھ",
    "RAYA.CA": "ط±ط§ظٹط©", "RTVC.CA": "ط±ظ…ظƒظˆ", "EKHO.CA": "ط§ظ„ظ‚ط§ط¨ط¶ط© ط§ظ„ظ…طµط±ظٹط© ط§ظ„ظƒظˆظٹطھظٹط©",
    "SWDY.CA": "ط§ظ„ط³ظˆظٹط¯ظٹ ط¥ظ„ظٹظƒطھط±ظٹظƒ", "GBCO.CA": "ط¬ظٹ ط¨ظٹ ظƒظˆط±ط¨", "DSCW.CA": "ط¯ط§ظٹط³ ظ„ظ„ظ…ظ„ط§ط¨ط³",
    "OIH.CA": "ط£ظˆط±ط§ط³ظƒظˆظ… ظ„ظ„ط§ط³طھط«ظ…ط§ط±", "ACGC.CA": "ط§ظ„ط¹ط±ط¨ظٹط© ظ„ط­ط¬ظٹط¬ ط§ظ„ظ‚ط·ظ†", "EGAL.CA": "ظ…طµط± ظ„ظ„ط£ظ„ظˆظ…ظ†ظٹظˆظ…",
    "ALCN.CA": "ط§ظ„ط¥ط³ظƒظ†ط¯ط±ظٹط© ظ„طھط¯ط§ظˆظ„ ط§ظ„ط¨ط¶ط§ط¦ط¹", "ATQA.CA": "ظ…طµط± ط§ظ„ظˆط·ظ†ظٹط© ظ„ظ„طµظ„ط¨ - ط¹طھط§ظ‚ط©",
    "UNIT.CA": "ط§ظ„ظ…طھط­ط¯ط© ظ„ظ„ط¥ط³ظƒط§ظ†", "MPRC.CA": "ط¥ظ… ط¥ظ… ط¬ط±ظˆط¨", "DCHE.CA": "ط§ظ„ط³ظ…ط§ط¯ ظˆط§ظ„طµظ†ط§ط¹ط§طھ ط§ظ„ظƒظٹظ…ط§ظˆظٹط©",
    "ASCM.CA": "ط£ط³ظƒظˆظ…", "UEGC.CA": "ط§ظ„ط³ط¨ط§ط¹ظٹط© ظ„ظ„طµظ†ط§ط¹ط§طھ", "BLCY.CA": "ط¨ظ„طھظˆظ† ط§ظ„ظ‚ط§ط¨ط¶ط©",
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

        # 1. ط§ظ„ظ…ط¤ط´ط±ط§طھ ط§ظ„ظپظ†ظٹط©
        df["EMA_20"] = ta.ema(df["Close"], length=20)
        df["EMA_50"] = ta.ema(df["Close"], length=50)
        df["RSI"] = ta.rsi(df["Close"], length=14)
        df["CMF"] = ta.cmf(df["High"], df["Low"], df["Close"], df["Volume"], length=20)
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)

        last = df.iloc[-1]

        # طھط£ظƒظٹط¯ ط¥ظ† ط§ظ„ظ…ط¤ط´ط±ط§طھ ظ…ط§ظ„ظ‡ط§ط´ ظ‚ظٹظ… ظ†ط§ظ‚طµط© ظ‚ط¨ظ„ ظ…ط§ ظ†ظƒظ…ظ„
        required_fields = ["EMA_20", "EMA_50", "RSI", "CMF", "ATR", "Close"]
        if last[required_fields].isna().any():
            log.info("Skipping %s: NaN values in indicators.", ticker)
            continue

        # 2. ظپط­طµ ط§ظ„طھظ‚ط§ط·ط¹ ط§ظ„ط£ط³ط¨ظˆط¹ظٹ (ط¢ط®ط± 5 ط¬ظ„ط³ط§طھ طھط¯ط§ظˆظ„)
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

        # 3. ط§ظ„ط´ط±ط· ط§ظ„ظپظ†ظٹ ط§ظ„ظ…ظƒطھظ…ظ„
        cond_tech = has_weekly_crossover and (last["RSI"] > 50) and (last["CMF"] > 0)

        if not cond_tech:
            continue

        signals_found += 1
        entry_price = round(last["Close"], 2)
        atr_value = last["ATR"]

        stop_loss = round(entry_price - (1.5 * atr_value), 2)
        take_profit = round(entry_price + (3.0 * atr_value), 2)
        arabic_name = names_map.get(ticker, ticker)

        # 4. ظپط­طµ ط§ظ„ظ…ط§ظ„ظٹط© ظˆطھط­ط¯ظٹط¯ ط¯ط±ط¬ط© ط§ظ„ط®ط·ظˆط±ط©
        try:
            info = stock.info
        except Exception as e:
            log.warning("Could not fetch info for %s: %s", ticker, e)
            info = {}

        eps = info.get("trailingEps", "N/A")
        pe_ratio = info.get("trailingPE", "N/A")

        is_high_risk = not isinstance(eps, (int, float)) or eps <= 0

        pe_text = str(round(pe_ratio, 2)) if isinstance(pe_ratio, (int, float)) else "ط؛ظٹط± ظ…طھط§ط­"
        eps_text = str(round(eps, 2)) if isinstance(eps, (int, float)) else "ط؛ظٹط± ظ…طھط§ط­"

        # 5. طµظٹط§ط؛ط© ط§ظ„طھظ†ط¨ظٹظ‡ ط­ط³ط¨ ظ†ظˆط¹ ط§ظ„طµظپظ‚ط©
        if is_high_risk:
            lines = [
                "âڑ ï¸ڈ *ط¥ط´ط§ط±ط© ظ…ط¶ط§ط±ط¨ط© ط³ط±ظٹط¹ط© (ط¹ط§ظ„ظٹط© ط§ظ„ط®ط·ظˆط±ط©)* âڑ،",
                f"ًں“ˆ *ط§ظ„ط³ظ‡ظ…:* {arabic_name} (`{ticker}`)",
                "----------------------------------",
                f"ًں“Œ *ط³ط¹ط± ط§ظ„ط¥ط؛ظ„ط§ظ‚:* {entry_price} ط¬ظ†ظٹظ‡",
                f"ًںژ¯ *ط§ظ„ظ‡ط¯ظپ ط§ظ„ظ…ظ‚طھط±ط­:* {take_profit} ط¬ظ†ظٹظ‡",
                f"ًں›‘ *ظˆظ‚ظپ ط§ظ„ط®ط³ط§ط±ط© (ط§ظ„ط§ظ„طھط²ط§ظ… طµط§ط±ظ…):* {stop_loss} ط¬ظ†ظٹظ‡",
                "----------------------------------",
                f"ًں”´ *ط³ط¨ط¨ طھظ†ط¨ظٹظ‡ ط§ظ„ط®ط·ظˆط±ط©:* ط§ظ„ظ†طھط§ط¦ط¬ ط§ظ„ظ…ط§ظ„ظٹط© ط¶ط¹ظٹظپط© ط£ظˆ ط؛ظٹط± ظ…طھط§ط­ط© (EPS: {eps_text})",
                "ًں’، *طھظˆطµظٹط© ط§ظ„ظ…ط¶ط§ط±ط¨ط©:* ط§ط­ط±طµ ط¹ظ„ظ‰ ط§ظ„طھط¯ط§ظˆظ„ ط¨ط­ط¬ظ… ظƒظ…ظٹط© طµط؛ظٹط± ظˆط§ظ„طھط²ط§ظ… طھط§ظ… ط¨ظˆظ‚ظپ ط§ظ„ط®ط³ط§ط±ط©.",
            ]
        else:
            lines = [
                "ًںڑ€ *ط¥ط´ط§ط±ط© ط§ط³طھط«ظ…ط§ط±ظٹط© / ط§طھط¬ط§ظ‡ ظ…ط¤ظƒط¯ (ظ…ط®ط§ط·ط±ط© ظ…طھظˆط§ط²ظ†ط©)* ًں”¥",
                f"ًں“ˆ *ط§ظ„ط³ظ‡ظ…:* {arabic_name} (`{ticker}`)",
                "----------------------------------",
                f"ًں“Œ *ط³ط¹ط± ط§ظ„ط¥ط؛ظ„ط§ظ‚:* {entry_price} ط¬ظ†ظٹظ‡",
                f"ًںژ¯ *ط§ظ„ظ‡ط¯ظپ ط§ظ„ظ…ظ‚طھط±ط­:* {take_profit} ط¬ظ†ظٹظ‡",
                f"ًں›‘ *ظˆظ‚ظپ ط§ظ„ط®ط³ط§ط±ط©:* {stop_loss} ط¬ظ†ظٹظ‡",
                "----------------------------------",
                f"ًںڈ›ï¸ڈ *ط§ظ„طھط­ظ„ظٹظ„ ط§ظ„ط£ط³ط§ط³ظٹ:* EPS: {eps_text} | P/E: {pe_text}",
                f"ًں“ٹ *ط§ظ„طھط­ظ„ظٹظ„ ط§ظ„ظپظ†ظٹ:* RSI: {round(last['RSI'], 1)} | ط§ظ„ط³ظٹظˆظ„ط© (CMF) ط¥ظٹط¬ط§ط¨ظٹط©",
            ]

        msg = "\n".join(lines)
        send_telegram_message(msg)
        log.info("Signal sent for: %s", ticker)

    except Exception as e:
        log.error("Error processing %s: %s", ticker, e)
        continue

    # ظ…ظ‡ظ„ط© ط¨ط³ظٹط·ط© ط¨ظٹظ† ظƒظ„ ط³ظ‡ظ… ظˆط§ظ„طھط§ظ†ظٹ ط¹ط´ط§ظ† ظ†ظ‚ظ„ظ„ ط§ط­طھظ…ط§ظ„ rate limiting ظ…ظ† Yahoo Finance
    time.sleep(1)

if signals_found == 0:
    send_telegram_message(
        "âœ… *طھظ‚ط±ظٹط± ط§ظ„ظپط­طµ ط§ظ„ط£ط³ط¨ظˆط¹ظٹ:* ظ„ظ… طھظڈظƒطھط´ظپ ط£ظٹ ط¥ط´ط§ط±ط§طھ ط¯ط®ظˆظ„ ط¬ط¯ظٹط¯ط© (ط§ط³طھط«ظ…ط§ط±ظٹط© ط£ظˆ ظ…ط¶ط§ط±ط¨ط©) طھظ†ط·ط¨ظ‚ ط¹ظ„ظٹظ‡ط§ ط§ظ„ط´ط±ظˆط·."
    )

log.info("EGX Scan Complete. Total Signals: %s", signals_found)
