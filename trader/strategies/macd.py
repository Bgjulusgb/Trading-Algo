from __future__ import annotations

import pandas as pd

from . import Signal


class MACD:
	name = "macd"

	def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
		self.fast = fast
		self.slow = slow
		self.signal_period = signal

	def generate(self, close: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series) -> Signal:
		if close is None or len(close) < self.slow + self.signal_period + 2:
			return "hold"
		ema_fast = close.ewm(span=self.fast, adjust=False).mean()
		ema_slow = close.ewm(span=self.slow, adjust=False).mean()
		macd_line = ema_fast - ema_slow
		signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
		prev_hist = macd_line.iloc[-2] - signal_line.iloc[-2]
		last_hist = macd_line.iloc[-1] - signal_line.iloc[-1]
		if prev_hist <= 0 and last_hist > 0:
			return "buy"
		if prev_hist >= 0 and last_hist < 0:
			return "sell"
		return "hold"