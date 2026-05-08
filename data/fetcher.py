import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


# Common Malaysian blue-chip stocks (Bursa Malaysia)
POPULAR_STOCKS = {
    "Maybank (1155)": "1155.KL",
    "Public Bank (1295)": "1295.KL",
    "CIMB (1023)": "1023.KL",
    "Tenaga (5347)": "5347.KL",
    "Petronas Gas (6033)": "6033.KL",
    "IHH Healthcare (5225)": "5225.KL",
    "Axiata (6888)": "6888.KL",
    "Maxis (6012)": "6012.KL",
    "Digi (6947)": "6947.KL",
    "Top Glove (7113)": "7113.KL",
    "Press Metal (8869)": "8869.KL",
    "Hong Leong Bank (5819)": "5819.KL",
}

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
