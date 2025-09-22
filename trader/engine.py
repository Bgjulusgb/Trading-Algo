from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from .config import TradingConfig
from .data import DataProvider
from .alpaca_client import AlpacaClient
from .strategies import StrategyResult, Signal
from .strategies.sma import SMACrossover
from .strategies.rsi import RSI
from .strategies.macd import MACD
from .strategies.breakout import DonchianBreakout
from .strategies.vwap import VWAPReversion


@dataclass
class Decision:
	symbol: str
	signal: Signal
	reasons: List[str]


class SignalAggregator:
	def __init__(self, config: TradingConfig):
		self.config = config
		self.strategies = [
			SMACrossover(10, 30),
			RSI(14, 30, 70),
			MACD(12, 26, 9),
			DonchianBreakout(20),
			VWAPReversion(20, 0.005),
		]

	def evaluate(self, df: pd.DataFrame) -> List[StrategyResult]:
		close = df["Close"]
		high = df["High"]
		low = df["Low"]
		volume = df["Volume"]
		results: List[StrategyResult] = []
		for strat in self.strategies:
			try:
				sig = strat.generate(close, high, low, volume)
				results.append(StrategyResult(name=strat.name, signal=sig))
			except Exception as e:
				results.append(StrategyResult(name=strat.name, signal="hold"))
		return results

	def decide(self, symbol: str, df: pd.DataFrame) -> Decision:
		results = self.evaluate(df)
		buy_count = sum(1 for r in results if r.signal == "buy")
		sell_count = sum(1 for r in results if r.signal == "sell")
		reasons = [f"{r.name}:{r.signal}" for r in results]
		min_agree = self.config.min_strategies_agree
		if self.config.aggregate_rule == "majority":
			if buy_count >= max(sell_count + 1, min_agree):
				return Decision(symbol=symbol, signal="buy", reasons=reasons)
			if sell_count >= max(buy_count + 1, min_agree):
				return Decision(symbol=symbol, signal="sell", reasons=reasons)
			return Decision(symbol=symbol, signal="hold", reasons=reasons)
		elif self.config.aggregate_rule == "consensus":
			if buy_count >= min_agree and sell_count == 0:
				return Decision(symbol=symbol, signal="buy", reasons=reasons)
			if sell_count >= min_agree and buy_count == 0:
				return Decision(symbol=symbol, signal="sell", reasons=reasons)
			return Decision(symbol=symbol, signal="hold", reasons=reasons)
		else:
			return Decision(symbol=symbol, signal="hold", reasons=reasons)


class TradingEngine:
	def __init__(self, config: TradingConfig, data: DataProvider, broker: AlpacaClient):
		self.config = config
		self.data = data
		self.broker = broker
		self.aggregator = SignalAggregator(config)

	def compute_order_qty(self, symbol: str, last_price: float) -> int:
		if last_price <= 0:
			return 0
		num_shares = int(self.config.max_notional_per_trade / last_price)
		return max(0, num_shares)

	def route_decision(self, decision: Decision, df: pd.DataFrame) -> Optional[str]:
		if decision.signal == "hold":
			return None
		if not self.broker.is_enabled():
			print("Trading disabled. Would have routed:", decision)
			return None
		last_price = float(df["Close"].iloc[-1])
		qty = self.compute_order_qty(decision.symbol, last_price)
		if qty <= 0:
			return None
		pos_qty = self.broker.get_position_qty(decision.symbol)
		# Risk checks: long-only, avoid flipping directly
		if self.config.long_only and decision.signal == "sell":
			if pos_qty > 0:
				self.broker.close_position(decision.symbol)
				return f"Closed long {decision.symbol}"
			return None
		if decision.signal == "buy" and pos_qty > 0:
			# Already long; skip duplicate buys
			return None
		if decision.signal == "sell" and pos_qty < 0:
			# Already short; skip duplicate sells
			return None
		# Submit bracket using last price as anchor for SL/TP
		res = self.broker.submit_bracket(
			symbol=decision.symbol,
			side="buy" if decision.signal == "buy" else "sell",
			qty=qty,
			anchor_price=last_price,
			stop_loss_pct=self.config.stop_loss_pct,
			take_profit_pct=self.config.take_profit_pct,
		)
		return f"{res.status}:{res.message}"

	def step(self) -> Dict[str, Decision]:
		decisions: Dict[str, Decision] = {}
		for symbol in self.config.symbols:
			md = self.data.get_bars(symbol)
			df = md.bars
			if df is None or df.empty or df.shape[0] < 50:
				continue
			decision = self.aggregator.decide(symbol, df)
			decisions[symbol] = decision
			self.route_decision(decision, df)
		return decisions