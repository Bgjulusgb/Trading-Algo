from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential

try:
	from alpaca_trade_api.rest import REST as AlpacaREST
	except_import_error = None
except Exception as e:
	except_import_error = e
	AlpacaREST = None  # type: ignore

from .config import TradingConfig


@dataclass
class OrderResult:
	client_order_id: Optional[str]
	status: str
	message: str


class AlpacaClient:
	def __init__(self, config: TradingConfig):
		self.config = config
		self.enabled = False
		self.rest: Optional[AlpacaREST] = None
		if AlpacaREST is not None and not isinstance(except_import_error, Exception):
			try:
				self.rest = AlpacaREST(
					key_id=config.alpaca_api_key_id,
					secret_key=config.alpaca_api_secret_key,
					base_url=config.alpaca_base_url,
				)
				# Validate credentials by a lightweight call
				self.rest.get_clock()
				self.enabled = True
			except Exception as e:
				print(f"Warning: Alpaca client disabled: {e}")
				self.enabled = False

	def is_enabled(self) -> bool:
		return self.enabled

	def get_position_qty(self, symbol: str) -> float:
		if not self.enabled or self.rest is None:
			return 0.0
		try:
			pos = self.rest.get_position(symbol)
			return float(pos.qty)
		except Exception:
			return 0.0

	def cancel_open_orders(self) -> None:
		if not self.enabled or self.rest is None:
			return
		try:
			self.rest.cancel_all_orders()
		except Exception as e:
			print(f"Warning: cancel orders failed: {e}")

	@retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
	def submit_bracket(self, symbol: str, side: str, qty: int, anchor_price: float, stop_loss_pct: float, take_profit_pct: float) -> OrderResult:
		if not self.enabled or self.rest is None:
			return OrderResult(client_order_id=None, status="disabled", message="Alpaca disabled")
		if qty <= 0:
			return OrderResult(client_order_id=None, status="invalid", message="qty <= 0")
		try:
			if side == "buy":
				stop_price = round(anchor_price * (1 - stop_loss_pct), 2) if stop_loss_pct > 0 else None
				take_profit_price = round(anchor_price * (1 + take_profit_pct), 2) if take_profit_pct > 0 else None
			else:
				# For shorts, stop is above, take-profit is below
				stop_price = round(anchor_price * (1 + stop_loss_pct), 2) if stop_loss_pct > 0 else None
				take_profit_price = round(anchor_price * (1 - take_profit_pct), 2) if take_profit_pct > 0 else None
			order = self.rest.submit_order(
				symbol=symbol,
				side=side,
				type="market",
				qty=qty,
				time_in_force=self.config.order_time_in_force,
				order_class="bracket",
				stop_loss={"stop_price": stop_price} if stop_price else None,
				take_profit={"limit_price": take_profit_price} if take_profit_price else None,
			)
			return OrderResult(client_order_id=order.client_order_id, status="submitted", message="ok")
		except Exception as e:
			return OrderResult(client_order_id=None, status="error", message=str(e))

	def close_position(self, symbol: str) -> None:
		if not self.enabled or self.rest is None:
			return
		try:
			self.rest.close_position(symbol)
		except Exception as e:
			print(f"Warning: close position failed: {e}")