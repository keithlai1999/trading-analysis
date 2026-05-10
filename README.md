# 📈 Technical Analysis Signal Generator

A web-based stock analysis tool for **Bursa Malaysia** stocks. Built with Python and Streamlit, it combines multiple technical indicators into a structured two-layer signal system that tells you whether a stock is trending and whether it's a good time to enter.

**Live app:** [keith-trading-analysis.streamlit.app](https://keith-trading-analysis.streamlit.app)

---

## What it does

- Fetches real-time OHLCV data from Yahoo Finance
- Calculates RSI, MACD, Bollinger Bands, EMA, ADX, ATR, and Volume indicators
- Generates a structured **BUY / SELL / WATCH / NEUTRAL** signal using a two-layer system
- Shows a **confidence score (0–100%)** so you know how strong the signal is
- Displays an interactive candlestick chart with all indicators
- Shows a signal history table for the last 20 trading days
- Works on both desktop and mobile

---

## How the signal system works

### Layer 1 — Trend Direction (State)
Runs every day. Checks whether the current market condition is bullish or bearish.

| Indicator | BULLISH (+1) | BEARISH (−1) | NEUTRAL (0) |
|---|---|---|---|
| **RSI** | RSI < 30 | RSI > 70 | 30 ≤ RSI ≤ 70 |
| **MACD** | MACD > Signal line | MACD < Signal line | Equal |
| **Bollinger Bands** | Price in lower 25% of band | Price in upper 25% of band | Middle 50% |
| **EMA** | EMA7 > EMA20 | EMA7 < EMA20 | Equal |

**Trend Score** = sum of all four (range: −4 to +4)
- ≥ +2 → **BULLISH**
- ≤ −2 → **BEARISH**
- −1 to +1 → **MIXED**

### Layer 2 — Entry Timing (Events)
Fires only on the exact day a crossover or trigger happens.

| Event | BUY trigger | SELL trigger |
|---|---|---|
| **MACD Crossover** | MACD crosses above signal line | MACD crosses below signal line |
| **EMA Crossover** | EMA7 crosses above EMA20 | EMA7 crosses below EMA20 |
| **RSI Threshold** | RSI climbs back above 30 (exits oversold) | RSI drops back below 70 (exits overbought) |
| **BB Bounce** | Price re-enters above lower band | Price re-enters below upper band |

### Combined Signal Logic

```
Entry=BUY  + Trend=BULLISH → STRONG BUY      ✅ best entry
Entry=BUY  + Trend=MIXED   → BUY             🟩 moderate confidence
Entry=BUY  + Trend=BEARISH → NEUTRAL         ⬜ filtered (against trend)
Entry=SELL + Trend=BEARISH → STRONG SELL     🔴 best exit
Entry=SELL + Trend=MIXED   → SELL            🟥 moderate confidence
Entry=SELL + Trend=BULLISH → NEUTRAL         ⬜ filtered (against trend)
No entry   + Trend=BULLISH → WATCH (BULLISH) 👀 uptrend, wait for entry trigger
No entry   + Trend=BEARISH → WATCH (BEARISH) ⚠️ downtrend, avoid buying
No entry   + Trend=MIXED   → NEUTRAL         ⬜ no signal
```

### Confidence Score (0–100%)
```
Trend %    = abs(Trend Score) / 4 × 100
Entry %    = max(buy events, sell events) / 4 × 100
Confidence = (Trend % × 60%) + (Entry % × 40%)
```

### Optional Filters
Both are **off by default** (can be turned on in the sidebar):

- **ADX Filter** — blocks all signals when ADX < 25 (choppy/sideways market). Good for avoiding false signals, but may miss valid moves.
- **EMA 200 Filter** — only allows BUY signals when price is above EMA 200 (long-term uptrend), and only SELL signals when below. Safer but very restrictive.

---

## How to use it

1. **Select a stock** — choose from 29 popular Bursa Malaysia stocks in the dropdown, or type any stock code manually (e.g. `1155` or `1155.KL`)
2. **Set period & interval** — 1 month to 2 years; daily or weekly bars
3. **Read Layer 1** — is the overall trend bullish, bearish, or mixed?
4. **Read Layer 2** — did an entry trigger fire today?
5. **Check the confidence score** — higher % means more indicators agree
6. **Check volume** — ALERT means unusual volume spike (1.5× average), which can confirm a move

**Practical guide:**
- **STRONG BUY + high confidence** → strongest buy signal; all indicators aligned
- **WATCH (BULLISH)** → trend is up but no entry trigger yet; wait before buying
- **NEUTRAL** → no clear direction; sit out and check again tomorrow
- **WATCH (BEARISH)** → trend is down; avoid buying new positions
- **STRONG SELL** → strongest exit signal; consider reducing position

> ⚠️ This tool is for **educational purposes only**. Technical signals do not guarantee future performance. Always do your own research before making investment decisions.

---

## Supported stocks

29 Bursa Malaysia stocks across 8 sectors:

| Sector | Stocks |
|---|---|
| 🏦 Banking & Finance | Maybank, Public Bank, CIMB, RHB Bank, Hong Leong Bank, AMMB |
| 📡 Telecommunications | Maxis, CelcomDigi, Telekom Malaysia, Axiata |
| ⚡ Energy & Utilities | Tenaga Nasional, Petronas Gas, Petronas Chemicals, YTL Power, Dialog Group |
| 🌴 Plantation | IOI Corporation, KL Kepong, Sime Darby |
| 🛒 Consumer & Retail | Nestle Malaysia, 99 Speed Mart, Mr DIY, PPB Group |
| 🏥 Healthcare | IHH Healthcare, Hartalega, Top Glove |
| 💻 Technology & Industrial | Inari Amertron, Press Metal |
| 🎰 Gaming & Leisure | Genting, Genting Malaysia |

Any other Bursa stock can be entered manually using its 4-digit code (e.g. `5347` for Tenaga).

---

## Tech stack

| Layer | Library |
|---|---|
| UI & deployment | [Streamlit](https://streamlit.io) |
| Data source | [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance) |
| Technical indicators | [ta](https://github.com/bukosabino/ta) |
| Charts | [Plotly](https://plotly.com) |
| Data processing | [pandas](https://pandas.pydata.org) |

---

## Project structure

```
trading_analysis/
├── app.py                  # Streamlit UI
├── data/
│   └── fetcher.py          # Yahoo Finance data fetching, stock list
├── analysis/
│   ├── indicators.py       # RSI, MACD, BB, EMA, ADX, ATR calculation
│   └── signals.py          # Two-layer signal generation, confidence score
└── requirements.txt
```

---

## Run locally

```bash
git clone https://github.com/keithlai1999/trading-analysis.git
cd trading-analysis
pip install -r requirements.txt
streamlit run app.py
```

Requires Python 3.10+.
