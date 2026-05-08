import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


# Popular Bursa Malaysia stocks organised by sector with icons
POPULAR_STOCKS = {
    # ── Banking & Finance ─────────────────────────────────────────────────────
    "🏦 Maybank (1155)":              "1155.KL",
    "🏦 Public Bank (1295)":          "1295.KL",
    "🏦 CIMB Group (1023)":           "1023.KL",
    "🏦 RHB Bank (1066)":             "1066.KL",
    "🏦 Hong Leong Bank (5819)":      "5819.KL",
    "🏦 AMMB Holdings (1015)":        "1015.KL",
    # ── Telecommunications ────────────────────────────────────────────────────
    "📡 Maxis (6012)":                "6012.KL",
    "📡 CelcomDigi (6947)":           "6947.KL",
    "📡 Telekom Malaysia (4863)":     "4863.KL",
    "📡 Axiata (6888)":               "6888.KL",
    # ── Energy & Utilities ────────────────────────────────────────────────────
    "⚡ Tenaga Nasional (5347)":      "5347.KL",
    "⚡ Petronas Gas (6033)":         "6033.KL",
    "⚡ Petronas Chemicals (5183)":   "5183.KL",
    "⚡ YTL Power (6742)":            "6742.KL",
    "⚡ Dialog Group (7277)":         "7277.KL",
    # ── Plantation ────────────────────────────────────────────────────────────
    "🌴 IOI Corporation (1961)":      "1961.KL",
    "🌴 KL Kepong (2445)":            "2445.KL",
    "🌴 Sime Darby (4197)":           "4197.KL",
    # ── Consumer & Retail ─────────────────────────────────────────────────────
    "🛒 Nestle Malaysia (4707)":      "4707.KL",
    "🛒 99 Speed Mart (5326)":        "5326.KL",
    "🛒 Mr DIY (5296)":               "5296.KL",
    "🛒 PPB Group (4065)":            "4065.KL",
    # ── Healthcare ────────────────────────────────────────────────────────────
    "🏥 IHH Healthcare (5225)":       "5225.KL",
    "🏥 Hartalega (5168)":            "5168.KL",
    "🏥 Top Glove (7113)":            "7113.KL",
    # ── Technology & Industrial ───────────────────────────────────────────────
    "💻 Inari Amertron (0166)":       "0166.KL",
    "💻 Press Metal (8869)":          "8869.KL",
    # ── Gaming & Leisure ──────────────────────────────────────────────────────
    "🎰 Genting (3182)":              "3182.KL",
    "🎰 Genting Malaysia (4715)":     "4715.KL",
}

# Company domain mapping for logo lookup via Clearbit
# Streamlit selectbox is text-only so logos are shown in the header instead
STOCK_DOMAINS = {
    "1155.KL": "maybank.com",
    "1295.KL": "pbebank.com",
    "1023.KL": "cimb.com",
    "1066.KL": "rhbgroup.com",
    "5819.KL": "hlb.com.my",
    "1015.KL": "ambankgroup.com",
    "6012.KL": "maxis.com.my",
    "6947.KL": "celcomdigi.com",
    "4863.KL": "tm.com.my",
    "6888.KL": "axiata.com",
    "5347.KL": "tnb.com.my",
    "6033.KL": "petronasgas.com.my",
    "5183.KL": "petronaschemicals.com",
    "6742.KL": "ytlpower.com",
    "7277.KL": "dialoggroup.com.my",
    "1961.KL": "ioicorp.com",
    "2445.KL": "klk.com.my",
    "4197.KL": "simedarby.com",
    "4707.KL": "nestle.com.my",
    "5326.KL": "99speedmart.com.my",
    "5296.KL": "mrdiy.com",
    "4065.KL": "ppbgroup.com",
    "5225.KL": "ihhhealthcare.com",
    "5168.KL": "hartalega.com.my",
    "7113.KL": "topglove.com",
    "0166.KL": "inari.com.my",
    "8869.KL": "pressmetal.com",
    "3182.KL": "genting.com",
    "4715.KL": "gentingmalaysia.com",
}


def get_stock_logo_url(ticker: str) -> str | None:
    """
    Return a logo image URL for the given ticker using Clearbit's free logo API.
    Returns None if no domain mapping exists.
    """
    domain = STOCK_DOMAINS.get(ticker.upper())
    if not domain:
        return None
    return f"https://logo.clearbit.com/{domain}"

PERIOD_OPTIONS = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "2 Years": "2y",
}

INTERVAL_OPTIONS = {
    "Daily": "1d",
    "Weekly": "1wk",
}

# EMA 200 needs at least 200 bars. We always fetch this many extra bars
# for indicator warmup, then trim back to the user's selected display period.
_WARMUP_DAYS = 300


def _period_to_days(period: str) -> int:
    mapping = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730}
    return mapping.get(period, 180)


def normalize_ticker(ticker: str) -> str:
    """
    Auto-append .KL for Bursa Malaysia stock codes entered as plain numbers.
    Examples:
      '1155'     → '1155.KL'
      '5326'     → '5326.KL'
      '1155.KL'  → '1155.KL'  (unchanged)
      'AAPL'     → 'AAPL'     (non-Bursa, unchanged)
    """
    ticker = ticker.strip().upper()
    if ticker.isdigit():
        return ticker + ".KL"
    return ticker


def fetch_stock_data(ticker: str, period: str = "6mo", interval: str = "1d") -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch OHLCV data from Yahoo Finance.

    Returns (display_df, full_df):
      - full_df:    longer history used for indicator calculation (ensures EMA200 has enough data)
      - display_df: trimmed to the user-selected period, used for charting

    Raises ValueError if no data is returned or rate limited.
    """
    display_days = _period_to_days(period)
    total_days   = display_days + _WARMUP_DAYS

    end   = datetime.today()
    start = end - timedelta(days=total_days)

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start.strftime("%Y-%m-%d"),
                           end=end.strftime("%Y-%m-%d"),
                           interval=interval)
    except Exception as e:
        err = str(e)
        if "RateLimit" in err or "rate limit" in err.lower() or "429" in err:
            raise ValueError(
                "Yahoo Finance rate limit reached — too many requests. "
                "Please wait 1-2 minutes and try again."
            )
        raise ValueError(f"Failed to fetch data for '{ticker}': {err}")

    if df.empty:
        raise ValueError(
            f"No data found for ticker '{ticker}'. "
            "For Bursa stocks use format like '1155.KL' or just enter '1155'. "
            "Check the stock code is correct."
        )

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Date"

    # Drop rows where Close is NaN (e.g. incomplete current-day bar)
    df = df.dropna(subset=["Close"])

    # full_df for indicator calculation
    full_df = df.copy()

    # display_df trimmed to the user-selected period
    cutoff = end - timedelta(days=display_days)
    display_df = df[df.index >= pd.Timestamp(cutoff)].copy()

    return display_df, full_df


def get_stock_info(ticker: str) -> dict:
    """Return basic stock info (name, sector, market cap)."""
    try:
        info = yf.Ticker(ticker).info
        return {
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "N/A"),
            "market_cap": info.get("marketCap", None),
            "currency": info.get("currency", "MYR"),
            "previous_close": info.get("previousClose", None),
        }
    except Exception:
        return {"name": ticker, "sector": "N/A", "market_cap": None, "currency": "MYR"}
