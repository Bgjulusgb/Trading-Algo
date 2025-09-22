from __future__ import annotations

import pandas as pd

from . import Signal


class VWAPReversion:
	name = "vwap_reversion"

	def __init__(self, window: int = 20, threshold_pct: float = 0.005):
		self.window = window
		self.threshold_pct = threshold_pct

	def generate(self, close: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series) -> Signal:
		if close is None or volume is None or len(close) < self.window + 1:
			return "hold"
		# Approx intraday VWAP rolling
		price = (high + low + close) / 3
		cum_vol = volume.rolling(self.window).sum()
		cum_pv = (price * volume).rolling(self.window).sum()
		vwap = (cum_pv / cum_vol).ffill()
		if vwap.isna().iloc[-1]:
			return "hold"
		dev = (close.iloc[-1] - vwap.iloc[-1]) / vwap.iloc[-1]
		if dev < -self.threshold_pct:
			return "buy"
		if dev > self.threshold_pct:
			return "sell"
		return "hold"