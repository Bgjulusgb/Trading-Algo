# Trading-Algo

This project provides a multi-strategy trading bot with live order routing to Alpaca and a Streamlit charting app.

## Features
- Multiple strategies: SMA crossover, RSI, MACD, Donchian breakout, VWAP reversion
- Signal aggregation with majority/consensus rules
- Risk controls: long-only option, bracket orders with stop loss / take profit
- Data provider supporting Alpaca (preferred) and yfinance fallback
- CLI loop for live/paper trading
- Existing Streamlit momentum visualizer (`Algorithmic-Trading-Python.py`)

## Setup
1. Python 3.10+
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create a `.env` from `.env.example` and fill Alpaca credentials:
```bash
cp .env.example .env
# edit .env
```
4. Optional: ensure your Alpaca account is in paper mode for testing.

## Run CLI Trading Bot
```bash
python -m trader.cli --env-file .env --symbols AAPL,MSFT --timeframe 1Min --poll 60
```
- To just test data and signals without placing orders, leave Alpaca keys blank in `.env`.

## Streamlit App (existing)
```bash
streamlit run Algorithmic-Trading-Python.py
```

## Notes
- Orders are submitted as bracket orders anchored to the latest close, using the configured `STOP_LOSS_PCT` and `TAKE_PROFIT_PCT`.
- Set `LONG_ONLY=false` to allow short signals.
- `MAX_NOTIONAL_PER_TRADE` caps position size per symbol.

## Disclaimer
This is for educational purposes. Trading involves risk. Use paper trading first.