import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from data.fetcher import fetch_stock_data, get_stock_info, normalize_ticker, POPULAR_STOCKS, PERIOD_OPTIONS, INTERVAL_OPTIONS
from analysis.indicators import add_all_indicators
from analysis.signals import generate_signals, get_latest_signal_summary

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Technical Analysis Signal Generator",
    page_icon="📈",
    layout="wide",
)

# ── Badge helpers ─────────────────────────────────────────────────────────────
OVERALL_COLOR = {
    "STRONG BUY":     "#00c853",
    "BUY":            "#69f0ae",
    "WATCH (BULLISH)":"#b9f6ca",
    "NEUTRAL":        "#90a4ae",
    "WAIT (CHOPPY)":  "#b0bec5",
    "WATCH (BEARISH)":"#ffccbc",
    "SELL":           "#ff6d00",
    "STRONG SELL":    "#d50000",
}

STATE_COLOR = {
    "BULLISH": "#69f0ae",
    "BEARISH": "#ff6d00",
    "NEUTRAL": "#90a4ae",
}

EVENT_COLOR = {
    "BUY":     "#69f0ae",
    "SELL":    "#ff6d00",
    "NEUTRAL": "#90a4ae",
    "ALERT":   "#ffd600",
}

TREND_COLOR = {
    "BULLISH": "#00c853",
    "BEARISH": "#d50000",
    "MIXED":   "#90a4ae",
}


def badge(label: str, color_map: dict, text: str = None) -> str:
    color = color_map.get(label, "#90a4ae")
    display = text or label
    return (
        f'<span style="background:{color};color:#000;'
        f'padding:3px 10px;border-radius:4px;font-weight:bold;font-size:0.85rem">'
        f'{display}</span>'
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("Stock Settings")

input_method = st.sidebar.radio("Select stock by", ["Popular Stocks", "Manual Ticker"])

if input_method == "Popular Stocks":
    stock_label = st.sidebar.selectbox("Stock", list(POPULAR_STOCKS.keys()))
    ticker = POPULAR_STOCKS[stock_label]
else:
    raw = st.sidebar.text_input("Stock code", value="1155", placeholder="e.g. 1155 or 1155.KL")
    ticker = normalize_ticker(raw)
    st.sidebar.caption(f"Resolved: {ticker}")

period_label = st.sidebar.selectbox("Period", list(PERIOD_OPTIONS.keys()), index=2)
period = PERIOD_OPTIONS[period_label]

interval_label = st.sidebar.selectbox("Interval", list(INTERVAL_OPTIONS.keys()))
interval = INTERVAL_OPTIONS[interval_label]

st.sidebar.markdown("---")
st.sidebar.markdown("**Indicators shown**")
show_ema    = st.sidebar.checkbox("EMA (9 / 21 / 50)", value=True)
show_bb     = st.sidebar.checkbox("Bollinger Bands", value=True)
show_rsi    = st.sidebar.checkbox("RSI", value=True)
show_macd   = st.sidebar.checkbox("MACD", value=True)
show_volume = st.sidebar.checkbox("Volume", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Filters (optional)**")
use_adx_filter   = st.sidebar.checkbox("ADX filter (trending only)", value=False,
                                        help="Block signals when ADX < 25 (choppy market). "
                                             "Stricter but misses many valid moves.")
use_ema200_filter = st.sidebar.checkbox("EMA 200 filter (long-term trend)", value=False,
                                         help="Block BUY signals when price is below EMA 200. "
                                              "Safer but very restrictive for beginners.")

st.sidebar.markdown("---")
st.sidebar.markdown("**Signal legend**")
st.sidebar.markdown(
    "🟢 **STRONG BUY** — event + bullish trend\n\n"
    "🟩 **BUY** — event fired, trend mixed\n\n"
    "⬜ **WATCH (BULLISH)** — uptrend, no entry trigger yet\n\n"
    "⬜ **NEUTRAL** — no clear signal\n\n"
    "⬜ **WAIT (CHOPPY)** — ADX < 25, sit out *(filter on)*\n\n"
    "🟧 **WATCH (BEARISH)** — downtrend, avoid buying\n\n"
    "🟥 **SELL** — event fired, trend mixed\n\n"
    "🔴 **STRONG SELL** — event + bearish trend"
)
st.sidebar.caption("Data source: Yahoo Finance")

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("📈 Technical Analysis Signal Generator")
st.caption("4-gate system: ADX filter → EMA 200 filter → Trend Direction → Entry Timing")

if not ticker:
    st.info("Enter a ticker in the sidebar to get started.")
    st.stop()

# ── Fetch & compute ───────────────────────────────────────────────────────────
with st.spinner(f"Fetching data for {ticker}..."):
    try:
        display_df, full_df = fetch_stock_data(ticker, period=period, interval=interval)
    except ValueError as e:
        st.error(str(e))
        st.stop()

info = get_stock_info(ticker)

# Calculate indicators on full history (ensures EMA200/ADX have enough bars),
# then trim back to the display period for charting and the signal table.
full_df = add_all_indicators(full_df)
full_df = generate_signals(full_df, use_adx_filter=use_adx_filter, use_ema200_filter=use_ema200_filter)
df = full_df[full_df.index >= display_df.index[0]].copy()
s = get_latest_signal_summary(df)

# ── Header ────────────────────────────────────────────────────────────────────
col_name, col_price, col_overall = st.columns([3, 1, 2])
with col_name:
    st.subheader(info["name"])
    st.caption(f"Sector: {info['sector']}  |  {ticker}  |  {period_label} {interval_label}")
with col_price:
    st.metric("Last Close", f"RM {s['close']:.3f}")
with col_overall:
    st.markdown("**Combined Signal**")
    st.markdown(badge(s["signal_overall"], OVERALL_COLOR), unsafe_allow_html=True)
    st.caption(f"As of {s['date']}")

st.divider()

MARKET_COLOR = {"TRENDING": "#00c853", "CHOPPY": "#d50000"}
EMA200_COLOR = {"ABOVE": "#69f0ae",   "BELOW":  "#ff6d00"}

# ── Filter status bar — only shown when at least one filter is ON ─────────────
if use_adx_filter or use_ema200_filter:
    st.markdown("#### Active Filters")
    active_cols = []
    if use_adx_filter:
        active_cols.append("adx")
    if use_ema200_filter:
        active_cols.append("ema200")

    f_cols = st.columns(len(active_cols))

    col_idx = 0
    if use_adx_filter:
        with f_cols[col_idx]:
            adx_val = s["adx_value"]
            adx_str = f"{adx_val:.1f}" if adx_val else "N/A"
            mkt     = s["market_condition"]
            st.markdown(
                f"**ADX Filter** &nbsp; {badge(mkt, MARKET_COLOR, f'{mkt}  (ADX={adx_str})')}",
                unsafe_allow_html=True,
            )
            if mkt == "CHOPPY":
                st.caption("ADX < 25 — choppy market. All signals blocked.")
            else:
                st.caption("ADX ≥ 25 — market is trending. Signals are valid.")
        col_idx += 1

    if use_ema200_filter:
        with f_cols[col_idx]:
            pos     = s["ema200_position"]
            ema_val = f"RM {s['ema200']:.3f}" if s["ema200"] else "N/A"
            st.markdown(
                f"**EMA 200 Filter** &nbsp; {badge(pos, EMA200_COLOR, f'{pos}  ({ema_val})')}",
                unsafe_allow_html=True,
            )
            if pos == "ABOVE":
                st.caption("Price above EMA 200 — long-term uptrend. Only BUY signals pass.")
            else:
                st.caption("Price below EMA 200 — long-term downtrend. Only SELL signals pass.")

    st.divider()

# ── Two-layer signal panel ────────────────────────────────────────────────────
left, right = st.columns(2, gap="large")

# ── Layer 1: Trend Direction (State) ─────────────────────────────────────────
with left:
    trend_score = s["trend_score"]
    trend_dir = s["trend_direction"]
    st.markdown(
        f"#### Layer 1 — Trend Direction &nbsp;&nbsp;"
        + badge(trend_dir, TREND_COLOR, f"{trend_dir}  ({trend_score:+d}/4)"),
        unsafe_allow_html=True,
    )
    st.caption("Is the market currently bullish or bearish? Updates every day.")

    c1, c2, c3, c4 = st.columns(4)
    rsi_val = f"RSI={s['rsi']:.0f}" if s["rsi"] else "RSI=N/A"
    with c1:
        st.markdown("**RSI**")
        st.markdown(badge(s["state_rsi"], STATE_COLOR), unsafe_allow_html=True)
        st.caption(rsi_val)
    with c2:
        st.markdown("**MACD**")
        st.markdown(badge(s["state_macd"], STATE_COLOR), unsafe_allow_html=True)
        st.caption("vs signal line")
    with c3:
        st.markdown("**BB Zone**")
        st.markdown(badge(s["state_bb"], STATE_COLOR), unsafe_allow_html=True)
        st.caption("price position")
    with c4:
        st.markdown("**EMA**")
        st.markdown(badge(s["state_ema"], STATE_COLOR), unsafe_allow_html=True)
        st.caption("EMA9 vs EMA21")

# ── Layer 2: Entry Timing (Events) ───────────────────────────────────────────
with right:
    entry = s["entry_signal"]
    st.markdown(
        f"#### Layer 2 — Entry Timing &nbsp;&nbsp;"
        + badge(entry, EVENT_COLOR),
        unsafe_allow_html=True,
    )
    st.caption("Did a crossover/trigger happen today? Fires only on the exact day.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**MACD X**")
        st.markdown(badge(s["event_macd"], EVENT_COLOR), unsafe_allow_html=True)
        st.caption("line crossover")
    with c2:
        st.markdown("**EMA X**")
        st.markdown(badge(s["event_ema"], EVENT_COLOR), unsafe_allow_html=True)
        st.caption("9/21 crossover")
    with c3:
        st.markdown("**RSI X**")
        st.markdown(badge(s["event_rsi"], EVENT_COLOR), unsafe_allow_html=True)
        st.caption("exits 35/65")
    with c4:
        st.markdown("**BB Bounce**")
        st.markdown(badge(s["event_bb"], EVENT_COLOR), unsafe_allow_html=True)
        st.caption("re-enters band")

# ── Logic explanation box ─────────────────────────────────────────────────────
st.markdown("---")
col_logic, col_vol = st.columns([3, 1])
with col_logic:
    rules = {
        ("BUY",     "BULLISH"): ("STRONG BUY",     "Entry trigger confirmed by bullish trend — best entry"),
        ("BUY",     "MIXED"):   ("BUY",             "Entry trigger fired, trend is mixed — moderate confidence"),
        ("BUY",     "BEARISH"): ("NEUTRAL",         "Entry trigger vs bearish trend — filtered out (false signal)"),
        ("SELL",    "BEARISH"): ("STRONG SELL",     "Exit trigger confirmed by bearish trend — best exit"),
        ("SELL",    "MIXED"):   ("SELL",            "Exit trigger fired, trend is mixed — moderate confidence"),
        ("SELL",    "BULLISH"): ("NEUTRAL",         "Exit trigger vs bullish trend — filtered out (false signal)"),
        ("NEUTRAL", "BULLISH"): ("WATCH (BULLISH)", "Trend is up but no trigger yet — hold or wait for entry"),
        ("NEUTRAL", "BEARISH"): ("WATCH (BEARISH)", "Trend is down, no trigger — avoid or wait to exit"),
        ("NEUTRAL", "MIXED"):   ("NEUTRAL",         "No trigger, no clear trend — sit out"),
    }
    current_key = (entry, trend_dir)
    if current_key in rules:
        result, reason = rules[current_key]
        st.info(f"**Why {result}?** — {reason}")
with col_vol:
    st.markdown("**Volume**")
    st.markdown(badge(s["signal_volume"], EVENT_COLOR), unsafe_allow_html=True)
    st.caption("1.5x avg = spike")

st.divider()

# ── Confidence Meter ──────────────────────────────────────────────────────────
st.subheader("Signal Confidence")

def progress_bar(pct: int, color: str) -> str:
    filled = round(pct / 10)
    empty  = 10 - filled
    bar    = f'<span style="color:{color}">{"█" * filled}</span>{"░" * empty}'
    return bar

trend_score    = s["trend_score"]
buy_events     = s["buy_event_count"]
sell_events    = s["sell_event_count"]
confidence     = s["confidence"]
signal_overall = s["signal_overall"]

# Determine display direction (positive = bullish, negative = bearish)
is_bearish = signal_overall in ("SELL", "STRONG SELL", "WATCH (BEARISH)")
trend_abs  = abs(trend_score)
event_abs  = sell_events if is_bearish else buy_events
t_pct      = round(trend_abs / 4 * 100)
e_pct      = round(event_abs / 4 * 100)

CONF_COLOR = "#00c853" if not is_bearish else "#d50000"

if confidence >= 75:
    conf_label = "Very Strong"
elif confidence >= 50:
    conf_label = "Strong"
elif confidence >= 25:
    conf_label = "Moderate"
elif confidence > 0:
    conf_label = "Weak"
else:
    conf_label = "No Signal"

trend_direction = s["trend_direction"]
entry_signal    = s["entry_signal"]
event_count_str = f"{event_abs}/4"
trend_score_str = f"{'+' if trend_score >= 0 else ''}{trend_score}/4"

cm1, cm2 = st.columns([2, 1])
with cm1:
    st.markdown(
        f"""
<div style="font-family:monospace;font-size:0.95rem;line-height:2">
<b>Trend Score &nbsp;&nbsp;</b> {progress_bar(t_pct, CONF_COLOR)} &nbsp;
<b>{trend_score_str}</b> &nbsp; {badge(trend_direction, TREND_COLOR)}
<br>
<b>Entry Events &nbsp;</b> {progress_bar(e_pct, CONF_COLOR)} &nbsp;
<b>{event_count_str}</b> &nbsp; {badge(entry_signal, EVENT_COLOR)}
<br>
<hr style="border-color:#333;margin:4px 0">
<b>Confidence &nbsp;&nbsp;&nbsp;</b> {progress_bar(confidence, CONF_COLOR)} &nbsp;
<b>{confidence}%</b> &nbsp; {badge(signal_overall, OVERALL_COLOR)}
&nbsp; <span style="color:#90a4ae">({conf_label})</span>
</div>
""",
        unsafe_allow_html=True,
    )
with cm2:
    st.markdown("**How to read:**")
    st.caption("Trend Score — how many indicators agree on direction (max 4)")
    st.caption("Entry Events — how many crossover triggers fired today (max 4)")
    st.caption("Confidence — weighted score: 60% trend + 40% entry events")
    st.caption("≥75% Very Strong · ≥50% Strong · ≥25% Moderate · <25% Weak")

st.divider()

# ── Hidden Formulas ───────────────────────────────────────────────────────────
with st.expander("📐 How signals are calculated (formulas)"):
    st.markdown("""
### Layer 1 — Trend Direction (State)
Runs every day. Checks current market condition.

| Indicator | BULLISH (+1) | BEARISH (-1) | NEUTRAL (0) |
|---|---|---|---|
| **RSI** | RSI < 35 | RSI > 65 | 35 ≤ RSI ≤ 65 |
| **MACD** | MACD > Signal line | MACD < Signal line | Equal |
| **Bollinger Bands** | Price in lower 25% of band | Price in upper 25% of band | Middle 50% |
| **EMA** | EMA9 > EMA21 | EMA9 < EMA21 | Equal |

**Trend Score** = RSI + MACD + BB + EMA &nbsp; (range: −4 to +4)
- Score ≥ +2 → **BULLISH**
- Score ≤ −2 → **BEARISH**
- −1 to +1 → **MIXED**

---

### Layer 2 — Entry Timing (Events)
Fires only on the exact day a trigger happens.

| Event | BUY trigger | SELL trigger |
|---|---|---|
| **MACD Crossover** | MACD crosses above signal line | MACD crosses below signal line |
| **EMA Crossover** | EMA9 crosses above EMA21 | EMA9 crosses below EMA21 |
| **RSI Threshold** | RSI climbs back above 35 (exits oversold) | RSI drops back below 65 (exits overbought) |
| **BB Bounce** | Price re-enters above lower band | Price re-enters below upper band |

**Entry Signal** = BUY if BUY events > SELL events, else SELL or NEUTRAL

---

### Confidence Score
```
Trend %     = abs(Trend Score) / 4 × 100
Entry %     = max(buy events, sell events) / 4 × 100
Confidence  = (Trend % × 60%) + (Entry % × 40%)
```

---

### Combined Signal Logic
```
Entry=BUY  + Trend=BULLISH → STRONG BUY   (best entry)
Entry=BUY  + Trend=MIXED   → BUY          (moderate)
Entry=BUY  + Trend=BEARISH → NEUTRAL      (filtered — against trend)
Entry=SELL + Trend=BEARISH → STRONG SELL  (best exit)
Entry=SELL + Trend=MIXED   → SELL         (moderate)
Entry=SELL + Trend=BULLISH → NEUTRAL      (filtered — against trend)
No entry   + Trend=BULLISH → WATCH (BULLISH)
No entry   + Trend=BEARISH → WATCH (BEARISH)
No entry   + Trend=MIXED   → NEUTRAL
```

---

### Optional Filters
- **ADX Filter (Gate 1):** ADX < 25 → WAIT (CHOPPY) — market not trending, all signals blocked
- **EMA 200 Filter (Gate 2):** Price below EMA 200 → only SELL signals pass; above → only BUY signals pass

---

### Indicator Formulas
- **RSI** = 100 − 100/(1 + avg_gain/avg_loss) over 14 periods
- **MACD** = EMA(12) − EMA(26); Signal = EMA(9) of MACD
- **Bollinger Bands** = SMA(20) ± 2 × standard deviation
- **EMA** = Price × k + prev_EMA × (1−k), where k = 2/(period+1)
- **ADX** = smoothed average of directional movement over 14 periods
- **ATR** = average of (High−Low, High−prev_Close, Low−prev_Close) over 14 periods
""")

# ── Chart ─────────────────────────────────────────────────────────────────────
subplot_rows = 1
row_heights = [0.5]
if show_rsi:
    subplot_rows += 1
    row_heights.append(0.2)
if show_macd:
    subplot_rows += 1
    row_heights.append(0.2)
if show_volume:
    subplot_rows += 1
    row_heights.append(0.15)

subplot_titles = ["Price"]
if show_rsi:
    subplot_titles.append("RSI (14)")
if show_macd:
    subplot_titles.append("MACD")
if show_volume:
    subplot_titles.append("Volume")

fig = make_subplots(
    rows=subplot_rows, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=row_heights,
    subplot_titles=subplot_titles,
)

# Candlestick
fig.add_trace(
    go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    ),
    row=1, col=1,
)

# EMA lines
if show_ema:
    for ema, color, width in [("EMA_9", "#f59e0b", 1.5), ("EMA_21", "#3b82f6", 1.5), ("EMA_50", "#a855f7", 1)]:
        fig.add_trace(
            go.Scatter(x=df.index, y=df[ema], name=ema.replace("_", " "),
                       line=dict(color=color, width=width), opacity=0.85),
            row=1, col=1,
        )
    # EMA 200 — the big picture trend line
    fig.add_trace(
        go.Scatter(x=df.index, y=df["EMA_200"], name="EMA 200",
                   line=dict(color="#ef5350", width=2, dash="dash"), opacity=0.9),
        row=1, col=1,
    )

# Bollinger Bands
if show_bb:
    fig.add_trace(
        go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Bands",
                   line=dict(color="#94a3b8", width=1, dash="dot"), opacity=0.7,
                   legendgroup="bb"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
                   line=dict(color="#94a3b8", width=1, dash="dot"), opacity=0.7,
                   fill="tonexty", fillcolor="rgba(148,163,184,0.08)",
                   legendgroup="bb", showlegend=False),
        row=1, col=1,
    )

# ── Signal markers — differentiate STRONG vs regular ─────────────────────────
strong_buy_mask  = df["Signal_Overall"] == "STRONG BUY"
buy_mask         = df["Signal_Overall"] == "BUY"
strong_sell_mask = df["Signal_Overall"] == "STRONG SELL"
sell_mask        = df["Signal_Overall"] == "SELL"

if strong_buy_mask.any():
    fig.add_trace(go.Scatter(
        x=df.index[strong_buy_mask], y=df["Low"][strong_buy_mask] * 0.985,
        mode="markers", marker=dict(symbol="triangle-up", size=14, color="#00c853"),
        name="Strong Buy",
    ), row=1, col=1)

if buy_mask.any():
    fig.add_trace(go.Scatter(
        x=df.index[buy_mask], y=df["Low"][buy_mask] * 0.992,
        mode="markers", marker=dict(symbol="triangle-up", size=9, color="#69f0ae"),
        name="Buy",
    ), row=1, col=1)

if strong_sell_mask.any():
    fig.add_trace(go.Scatter(
        x=df.index[strong_sell_mask], y=df["High"][strong_sell_mask] * 1.015,
        mode="markers", marker=dict(symbol="triangle-down", size=14, color="#d50000"),
        name="Strong Sell",
    ), row=1, col=1)

if sell_mask.any():
    fig.add_trace(go.Scatter(
        x=df.index[sell_mask], y=df["High"][sell_mask] * 1.008,
        mode="markers", marker=dict(symbol="triangle-down", size=9, color="#ff6d00"),
        name="Sell",
    ), row=1, col=1)

# Sub-charts
current_row = 2

if show_rsi:
    fig.add_trace(
        go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="#f59e0b", width=1.5)),
        row=current_row, col=1,
    )
    fig.add_hline(y=65, line_dash="dot", line_color="red",   opacity=0.5, row=current_row, col=1)
    fig.add_hline(y=35, line_dash="dot", line_color="green", opacity=0.5, row=current_row, col=1)
    fig.add_hrect(y0=35, y1=65, fillcolor="rgba(255,255,255,0.03)", row=current_row, col=1)
    fig.update_yaxes(range=[0, 100], row=current_row, col=1)
    current_row += 1

if show_macd:
    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_Hist"].fillna(0)]
    fig.add_trace(
        go.Bar(x=df.index, y=df["MACD_Hist"], name="MACD Hist", marker_color=colors, opacity=0.7),
        row=current_row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#3b82f6", width=1.5)),
        row=current_row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal", line=dict(color="#f59e0b", width=1.5)),
        row=current_row, col=1,
    )
    current_row += 1

if show_volume:
    vol_colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(
        go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=vol_colors, opacity=0.7),
        row=current_row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["Volume_SMA"], name="Vol SMA20",
                   line=dict(color="#f59e0b", width=1.5, dash="dot"),
                   legendgroup="volume", showlegend=False),
        row=current_row, col=1,
    )

fig.update_layout(
    height=700 + subplot_rows * 60,
    template="plotly_dark",
    showlegend=True,
    legend=dict(
        orientation="v", yanchor="top", y=1, xanchor="left", x=1.01,
        bgcolor="rgba(30,30,30,0.8)", bordercolor="rgba(255,255,255,0.15)",
        borderwidth=1, font=dict(size=11), tracegroupgap=4,
    ),
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=160, t=40, b=10),
)

st.plotly_chart(fig, use_container_width=True)

# ── Signal history table ──────────────────────────────────────────────────────
st.subheader("Recent Signal History")

history_cols = ["Close", "ADX_Value", "Market_Condition", "EMA200_Position", "Trend_Direction", "Entry_Signal", "Signal_Overall"]
recent = df[history_cols].tail(20).iloc[::-1].copy()
recent.index = recent.index.strftime("%Y-%m-%d")
recent["Close"]     = recent["Close"].map(lambda x: f"RM {x:.3f}")
recent["ADX_Value"] = recent["ADX_Value"].map(lambda x: f"{x:.1f}" if pd.notna(x) else "—")

st.dataframe(
    recent.rename(columns={
        "ADX_Value":        "ADX",
        "Market_Condition": "Gate1: ADX",
        "EMA200_Position":  "Gate2: EMA200",
        "Trend_Direction":  "Gate3: Trend",
        "Entry_Signal":     "Gate4: Entry",
        "Signal_Overall":   "Final Signal",
    }),
    use_container_width=True,
    height=400,
)

st.divider()
st.caption(
    "Disclaimer: This tool is for educational purposes only. "
    "Technical signals do not guarantee future performance. "
    "Always do your own research before making investment decisions."
)
