from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import pytz
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

try:
	from alpaca_trade_api.rest import REST as AlpacaREST
	except_import_error = None
except Exception as e:
	except_import_error = e
	AlpacaREST = None  # type: ignore

from .config import TradingConfig


@dataclass
class MarketData:
	symbol: str
	bars: pd.DataFrame  # index datetime, columns [Open, High, Low, Close, Volume]


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
	if df is None or df.empty:
		return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"]).astype(
			{"Open": float, "High": float, "Low": float, "Close": float, "Volume": float}
		)
	# Ensure proper column capitalization
	cols = {c.lower(): c for c in ["Open", "High", "Low", "Close", "Volume"]}
	out = pd.DataFrame(index=df.index)
	for name in ["Open", "High", "Low", "Close", "Volume"]:
		cand = [c for c in df.columns if c.lower() == name.lower()]
		if cand:
			out[name] = df[cand[0]].astype(float)
		else:
			out[name] = float("nan")
	return out.sort_index()


def _yf_interval(timeframe: str) -> str:
	mapping = {
		"1Min": "1m",
		"5Min": "5m",
		"15Min": "15m",
		"30Min": "30m",
		"60Min": "60m",
		"1H": "60m",
		"1D": "1d",
	}
	return mapping.get(timeframe, "1m")


def _alpaca_tf_str(timeframe: str) -> str:
	# Alpaca SDK accepts strings like "1Min", "5Min", "1Hour", "1Day"
	mapping = {
		"1Min": "1Min",
		"5Min": "5Min",
		"15Min": "15Min",
		"30Min": "30Min",
		"60Min": "60Min",
		"1H": "60Min",
		"1D": "1Day",
	}
	return mapping.get(timeframe, "1Min")


@retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(3))
def fetch_yf(symbol: str, timeframe: str, lookback_bars: int) -> pd.DataFrame:
	interval = _yf_interval(timeframe)
	period_map = {
		"1m": "7d",
		"5m": "30d",
		"15m": "60d",
		"30m": "60d",
		"60m": "60d",
		"1d": "2y",
	}
	period = period_map.get(interval, "30d")
	df = yf.download(tickers=symbol, interval=interval, period=period, auto_adjust=False, progress=False)
	if isinstance(df.columns, pd.MultiIndex):
		df.columns = [c[0] for c in df.columns]
	return _normalize_df(df).tail(lookback_bars)


def fetch_alpaca(rest: AlpacaREST, symbol: str, timeframe: str, lookback_bars: int) -> pd.DataFrame:
	now = dt.datetime.now(tz=pytz.UTC)
	start = now - dt.timedelta(days=30)
	bar_timeframe = _alpaca_tf_str(timeframe)
	bars = rest.get_bars(symbol, bar_timeframe, start=start, end=now, adjustment="raw").df
	if not bars.empty and "symbol" in bars.columns:
		bars = bars[bars["symbol"] == symbol]
	bars.index = pd.to_datetime(bars.index)
	bars.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
	return _normalize_df(bars).tail(lookback_bars)


class DataProvider:
	def __init__(self, config: TradingConfig):
		self.config = config
		self.alpaca: Optional[AlpacaREST] = None
		if config.use_alpaca_data and AlpacaREST is not None and not isinstance(except_import_error, Exception):
			try:
				self.alpaca = AlpacaREST(
					key_id=config.alpaca_api_key_id,
					secret_key=config.alpaca_api_secret_key,
					base_url=config.alpaca_base_url,
				)
			except Exception as e:
				print(f"Warning: Failed to init Alpaca REST for data: {e}. Falling back to yfinance.")
				self.alpaca = None

	def get_bars(self, symbol: str) -> MarketData:
		if self.alpaca is not None:
			try:
				df = fetch_alpaca(self.alpaca, symbol, self.config.timeframe, self.config.lookback_bars)
				if not df.empty:
					return MarketData(symbol=symbol, bars=df)
			except Exception as e:
				print(f"Warning: Alpaca data failed for {symbol}: {e}. Falling back to yfinance.")

		df = fetch_yf(symbol, self.config.timeframe, self.config.lookback_bars)
		return MarketData(symbol=symbol, bars=df)