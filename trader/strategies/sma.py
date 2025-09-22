from __future__ import annotations

import pandas as pd

from . import Signal, Strategy


class SMACrossover:
	name = "sma_crossover"

	def __init__(self, fast: int = 10, slow: int = 30):
		self.fast = fast
		self.slow = slow

	def generate(self, close: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series) -> Signal:
		if close is None or close.empty:
			return "hold"
		fast_ma = close.rolling(self.fast).mean()
		slow_ma = close.rolling(self.slow).mean()
		if len(close) < max(self.fast, self.slow) + 1:
			return "hold"
		prev_fast, prev_slow = fast_ma.iloc[-2], slow_ma.iloc[-2]
		last_fast, last_slow = fast_ma.iloc[-1], slow_ma.iloc[-1]
		if pd.notna(prev_fast) and pd.notna(prev_slow) and pd.notna(last_fast) and pd.notna(last_slow):
			if prev_fast <= prev_slow and last_fast > last_slow:
				return "buy"
			if prev_fast >= prev_slow and last_fast < last_slow:
				return "sell"
		return "hold"