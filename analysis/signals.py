import pandas as pd

# ── FILTER 1: ADX — Trend Strength ────────────────────────────────────────────
# Answers: "Is the market trending or choppy right now?"
# If choppy, ALL signals are unreliable — sit out regardless of direction.
ADX_THRESHOLD = 25  # Standard: < 25 = choppy, >= 25 = trending


def _adx_filter(row: pd.Series) -> tuple[str, float]:
    """
    Returns (market_condition, adx_value).
    market_condition: "TRENDING" or "CHOPPY"
    """
    adx = row.get("ADX")
    if pd.isna(adx):
        return "TRENDING", None   # Not enough data yet, don't block signals
    if adx >= ADX_THRESHOLD:
        return "TRENDING", round(float(adx), 1)
    return "CHOPPY", round(float(adx), 1)


# ── FILTER 2: EMA 200 — Big Picture Direction ─────────────────────────────────
# Answers: "Is this stock in a long-term uptrend or downtrend?"
# Only allow BUY signals when price is above EMA 200 (long-term uptrend).
# Only allow SELL signals when price is below EMA 200 (long-term downtrend).

def _ema200_filter(row: pd.Series) -> str:
    """
    Returns "ABOVE" (long-term uptrend) or "BELOW" (long-term downtrend).
    """
    close = row.get("Close")
    ema200 = row.get("EMA_200")
    if any(pd.isna(v) for v in [close, ema200]):
        return "ABOVE"   # Not enough data yet, don't block signals
    if close > ema200:
        return "ABOVE"
    return "BELOW"


# ── LAYER 1: STATE signals (trend direction) ──────────────────────────────────
# Answers: "Is the market currently bullish or bearish?"

def _rsi_state(row: pd.Series) -> str:
    rsi = row.get("RSI")
    if pd.isna(rsi):
        return "NEUTRAL"
    if rsi < 35:
        return "BULLISH"
    if rsi > 65:
        return "BEARISH"
    return "NEUTRAL"


def _macd_state(row: pd.Series) -> str:
    macd = row.get("MACD")
    signal = row.get("MACD_Signal")
    if any(pd.isna(v) for v in [macd, signal]):
        return "NEUTRAL"
    if macd > signal:
        return "BULLISH"
    if macd < signal:
        return "BEARISH"
    return "NEUTRAL"


def _bb_state(row: pd.Series) -> str:
    close = row.get("Close")
    lower = row.get("BB_Lower")
    upper = row.get("BB_Upper")
    if any(pd.isna(v) for v in [close, lower, upper]):
        return "NEUTRAL"
    band_width = upper - lower
    if band_width == 0:
        return "NEUTRAL"
    position = (close - lower) / band_width
    if position <= 0.25:
        return "BULLISH"
    if position >= 0.75:
        return "BEARISH"
    return "NEUTRAL"


def _ema_state(row: pd.Series) -> str:
    ema9 = row.get("EMA_9")
    ema21 = row.get("EMA_21")
    if any(pd.isna(v) for v in [ema9, ema21]):
        return "NEUTRAL"
    if ema9 > ema21:
        return "BULLISH"
    if ema9 < ema21:
        return "BEARISH"
    return "NEUTRAL"


# ── LAYER 2: EVENT signals (entry timing) ─────────────────────────────────────
# Answers: "Did a crossover/trigger happen today?"

def _macd_event(row: pd.Series, prev_row: pd.Series) -> str:
    macd = row.get("MACD")
    signal = row.get("MACD_Signal")
    prev_macd = prev_row.get("MACD")
    prev_signal = prev_row.get("MACD_Signal")
    if any(pd.isna(v) for v in [macd, signal, prev_macd, prev_signal]):
        return "NEUTRAL"
    if prev_macd < prev_signal and macd > signal:
        return "BUY"
    if prev_macd > prev_signal and macd < signal:
        return "SELL"
    return "NEUTRAL"


def _ema_event(row: pd.Series, prev_row: pd.Series) -> str:
    ema9 = row.get("EMA_9")
    ema21 = row.get("EMA_21")
    prev_ema9 = prev_row.get("EMA_9")
    prev_ema21 = prev_row.get("EMA_21")
    if any(pd.isna(v) for v in [ema9, ema21, prev_ema9, prev_ema21]):
        return "NEUTRAL"
    if prev_ema9 < prev_ema21 and ema9 > ema21:
        return "BUY"
    if prev_ema9 > prev_ema21 and ema9 < ema21:
        return "SELL"
    return "NEUTRAL"


def _rsi_event(row: pd.Series, prev_row: pd.Series) -> str:
    rsi = row.get("RSI")
    prev_rsi = prev_row.get("RSI")
    if any(pd.isna(v) for v in [rsi, prev_rsi]):
        return "NEUTRAL"
    if prev_rsi < 35 and rsi >= 35:
        return "BUY"
    if prev_rsi > 65 and rsi <= 65:
        return "SELL"
    return "NEUTRAL"


def _bb_event(row: pd.Series, prev_row: pd.Series) -> str:
    close = row.get("Close")
    prev_close = prev_row.get("Close")
    lower = row.get("BB_Lower")
    upper = row.get("BB_Upper")
    prev_lower = prev_row.get("BB_Lower")
    prev_upper = prev_row.get("BB_Upper")
    if any(pd.isna(v) for v in [close, prev_close, lower, upper, prev_lower, prev_upper]):
        return "NEUTRAL"
    if prev_close <= prev_lower and close > lower:
        return "BUY"
    if prev_close >= prev_upper and close < upper:
        return "SELL"
    return "NEUTRAL"


def _volume_signal(row: pd.Series) -> str:
    volume = row.get("Volume")
    vol_sma = row.get("Volume_SMA")
    if pd.isna(volume) or pd.isna(vol_sma) or vol_sma == 0:
        return "NEUTRAL"
    if volume > vol_sma * 1.5:
        return "ALERT"
    return "NEUTRAL"


# ── COMBINED logic ────────────────────────────────────────────────────────────
_STATE_SCORE = {"BULLISH": 1, "BEARISH": -1, "NEUTRAL": 0}


def _combine(trend: str, entry: str, market: str, ema200: str,
             use_adx_filter: bool = False, use_ema200_filter: bool = False) -> str:
    """
    Combine all layers into a final signal.

    Filters are optional:
      use_adx_filter   — when ON, CHOPPY market blocks all signals → WAIT (CHOPPY)
      use_ema200_filter — when ON, EMA200 direction gates BUY/SELL signals

    Without filters (default): uses only trend + entry for the signal.
    """
    # Gate 1: ADX filter (only active when toggled on)
    if use_adx_filter and market == "CHOPPY":
        return "WAIT (CHOPPY)"

    # Gate 2: EMA 200 filter (only active when toggled on)
    if use_ema200_filter:
        if ema200 == "ABOVE":
            if entry == "BUY":
                return "STRONG BUY" if trend == "BULLISH" else "BUY"
            if entry == "SELL":
                return "NEUTRAL"   # filtered out — sell signal in uptrend
            return "WATCH (BULLISH)" if trend == "BULLISH" else "NEUTRAL"
        else:
            if entry == "SELL":
                return "STRONG SELL" if trend == "BEARISH" else "SELL"
            if entry == "BUY":
                return "NEUTRAL"   # filtered out — buy signal in downtrend
            return "WATCH (BEARISH)" if trend == "BEARISH" else "NEUTRAL"

    # No EMA200 filter — use trend + entry directly
    if entry == "BUY":
        return "STRONG BUY" if trend == "BULLISH" else "BUY"
    if entry == "SELL":
        return "STRONG SELL" if trend == "BEARISH" else "SELL"
    if trend == "BULLISH":
        return "WATCH (BULLISH)"
    if trend == "BEARISH":
        return "WATCH (BEARISH)"
    return "NEUTRAL"


# ── Main signal generator ─────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame,
                     use_adx_filter: bool = False,
                     use_ema200_filter: bool = False) -> pd.DataFrame:
    df = df.copy()

    state_rsi, state_macd, state_bb, state_ema = [], [], [], []
    trend_scores, trend_directions = [], []
    event_macd, event_ema, event_rsi, event_bb = [], [], [], []
    entry_signals = []
    buy_event_counts, sell_event_counts = [], []
    confidence_scores = []
    volume_signals = []
    adx_values, market_conditions = [], []
    ema200_positions = []
    overall_signals = []

    for i in range(len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i - 1] if i > 0 else row

        # ── Filters ───────────────────────────────────────────────────────────
        market, adx_val = _adx_filter(row)
        ema200 = _ema200_filter(row)
        market_conditions.append(market)
        adx_values.append(adx_val)
        ema200_positions.append(ema200)

        # ── Layer 1: State ────────────────────────────────────────────────────
        s_rsi  = _rsi_state(row)
        s_macd = _macd_state(row)
        s_bb   = _bb_state(row)
        s_ema  = _ema_state(row)

        state_rsi.append(s_rsi)
        state_macd.append(s_macd)
        state_bb.append(s_bb)
        state_ema.append(s_ema)

        trend_score = _STATE_SCORE[s_rsi] + _STATE_SCORE[s_macd] + _STATE_SCORE[s_bb] + _STATE_SCORE[s_ema]
        trend_scores.append(trend_score)
        trend = "BULLISH" if trend_score >= 2 else "BEARISH" if trend_score <= -2 else "MIXED"
        trend_directions.append(trend)

        # ── Layer 2: Events ───────────────────────────────────────────────────
        e_macd = _macd_event(row, prev_row)
        e_ema  = _ema_event(row, prev_row)
        e_rsi  = _rsi_event(row, prev_row)
        e_bb   = _bb_event(row, prev_row)

        event_macd.append(e_macd)
        event_ema.append(e_ema)
        event_rsi.append(e_rsi)
        event_bb.append(e_bb)

        events = [e_macd, e_ema, e_rsi, e_bb]
        buy_count  = events.count("BUY")
        sell_count = events.count("SELL")
        entry = "BUY" if buy_count > sell_count else \
                "SELL" if sell_count > buy_count else "NEUTRAL"
        entry_signals.append(entry)
        buy_event_counts.append(buy_count)
        sell_event_counts.append(sell_count)

        # ── Confidence score (0–100%) ─────────────────────────────────────────
        # Measures how strong the current signal is regardless of direction.
        # Trend contributes 60%, Entry events contribute 40%.
        abs_trend   = abs(trend_score) / 4        # 0.0 – 1.0
        event_count = max(buy_count, sell_count)
        abs_entry   = event_count / 4             # 0.0 – 1.0
        confidence  = round((0.6 * abs_trend + 0.4 * abs_entry) * 100)
        confidence_scores.append(confidence)

        volume_signals.append(_volume_signal(row))
        overall_signals.append(_combine(trend, entry, market, ema200,
                                         use_adx_filter, use_ema200_filter))

    df["Market_Condition"] = market_conditions
    df["ADX_Value"]        = adx_values
    df["EMA200_Position"]  = ema200_positions

    df["State_RSI"]        = state_rsi
    df["State_MACD"]       = state_macd
    df["State_BB"]         = state_bb
    df["State_EMA"]        = state_ema
    df["Trend_Score"]      = trend_scores
    df["Trend_Direction"]  = trend_directions

    df["Event_MACD"]       = event_macd
    df["Event_EMA"]        = event_ema
    df["Event_RSI"]        = event_rsi
    df["Event_BB"]         = event_bb
    df["Entry_Signal"]     = entry_signals
    df["Buy_Event_Count"]  = buy_event_counts
    df["Sell_Event_Count"] = sell_event_counts
    df["Confidence"]       = confidence_scores

    df["Signal_Volume"]    = volume_signals
    df["Signal_Overall"]   = overall_signals

    return df


def get_latest_signal_summary(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    return {
        "date":             df.index[-1].strftime("%Y-%m-%d"),
        "close":            last["Close"],
        "rsi":              round(last["RSI"], 2) if not pd.isna(last["RSI"]) else None,
        # Filters
        "market_condition": last["Market_Condition"],
        "adx_value":        last["ADX_Value"],
        "ema200_position":  last["EMA200_Position"],
        "ema200":           round(last["EMA_200"], 3) if not pd.isna(last["EMA_200"]) else None,
        # Layer 1
        "state_rsi":        last["State_RSI"],
        "state_macd":       last["State_MACD"],
        "state_bb":         last["State_BB"],
        "state_ema":        last["State_EMA"],
        "trend_score":      int(last["Trend_Score"]),
        "trend_direction":  last["Trend_Direction"],
        # Layer 2
        "event_macd":       last["Event_MACD"],
        "event_ema":        last["Event_EMA"],
        "event_rsi":        last["Event_RSI"],
        "event_bb":         last["Event_BB"],
        "entry_signal":     last["Entry_Signal"],
        "buy_event_count":  int(last["Buy_Event_Count"]),
        "sell_event_count": int(last["Sell_Event_Count"]),
        # Confidence
        "confidence":       int(last["Confidence"]),
        # Volume
        "signal_volume":    last["Signal_Volume"],
        # Combined
        "signal_overall":   last["Signal_Overall"],
    }
