import pandas as pd
import ta


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all technical indicators and add them as columns to the DataFrame.
    Input df must have columns: Open, High, Low, Close, Volume.
    """
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # --- RSI (14-period) ---
    df["RSI"] = ta.momentum.RSIIndicator(close=close, window=14).rsi()

    # --- MACD (12, 26, 9) ---
    macd_obj = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd_obj.macd()
    df["MACD_Signal"] = macd_obj.macd_signal()
    df["MACD_Hist"] = macd_obj.macd_diff()

    # --- Bollinger Bands (20-period, 2 std) ---
    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Middle"] = bb.bollinger_mavg()
    df["BB_Lower"] = bb.bollinger_lband()
    df["BB_Width"] = bb.bollinger_wband()

    # --- Exponential Moving Averages (4 / 7 / 10 / 20 / 200) ---
    df["EMA_4"]  = ta.trend.EMAIndicator(close=close, window=4).ema_indicator()
    df["EMA_7"]  = ta.trend.EMAIndicator(close=close, window=7).ema_indicator()
    df["EMA_10"] = ta.trend.EMAIndicator(close=close, window=10).ema_indicator()
    df["EMA_20"] = ta.trend.EMAIndicator(close=close, window=20).ema_indicator()
    df["EMA_200"] = ta.trend.EMAIndicator(close=close, window=200).ema_indicator()

    # --- Simple Moving Average ---
    df["SMA_20"] = ta.trend.SMAIndicator(close=close, window=20).sma_indicator()
    df["SMA_50"] = ta.trend.SMAIndicator(close=close, window=50).sma_indicator()

    # --- Average True Range (volatility) ---
    df["ATR"] = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()

    # --- ADX (Average Directional Index, 14-period) ---
    # ADX > 25 = trending market (signals valid)
    # ADX < 25 = choppy/sideways market (signals unreliable)
    adx_obj = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
    df["ADX"] = adx_obj.adx()
    df["ADX_Plus"] = adx_obj.adx_pos()   # +DI: buying pressure
    df["ADX_Minus"] = adx_obj.adx_neg()  # -DI: selling pressure

    # --- Volume SMA (to detect volume spikes) ---
    df["Volume_SMA"] = df["Volume"].rolling(window=20).mean()

    return df
