from __future__ import annotations

import pandas as pd

from . import Signal, Strategy


class RSI:
	name = "rsi"

	def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
		self.period = period
		self.oversold = oversold
		self.overbought = overbought

	def _rsi(self, close: pd.Series) -> pd.Series:
		delta = close.diff()
		up = delta.clip(lower=0)
		down = -delta.clip(upper=0)
		gain = up.rolling(self.period).mean()
		loss = down.rolling(self.period).mean()
		rs = gain / (loss.replace(0, pd.NA))
		rsi = 100 - (100 / (1 + rs))
		return rsi

	def generate(self, close: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series) -> Signal:
		if close is None or len(close) < self.period + 1:
			return "hold"
		rsi = self._rsi(close)
		if rsi.iloc[-2] <= self.oversold and rsi.iloc[-1] > self.oversold:
			return "buy"
		if rsi.iloc[-2] >= self.overbought and rsi.iloc[-1] < self.overbought:
			return "sell"
		return "hold"