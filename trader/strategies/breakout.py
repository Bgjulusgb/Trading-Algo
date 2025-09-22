from __future__ import annotations

import pandas as pd

from . import Signal


class DonchianBreakout:
	name = "donchian_breakout"

	def __init__(self, lookback: int = 20):
		self.lookback = lookback

	def generate(self, close: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series) -> Signal:
		if high is None or low is None or len(high) < self.lookback + 1 or len(low) < self.lookback + 1:
			return "hold"
		high_n = high.rolling(self.lookback).max()
		low_n = low.rolling(self.lookback).min()
		if close.iloc[-1] > high_n.iloc[-2]:
			return "buy"
		if close.iloc[-1] < low_n.iloc[-2]:
			return "sell"
		return "hold"