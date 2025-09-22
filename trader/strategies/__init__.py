from dataclasses import dataclass
from typing import Literal, Protocol

Signal = Literal["buy", "sell", "hold"]


class Strategy(Protocol):
	name: str

	def generate(self, close, high, low, volume) -> Signal:  # expects pandas Series
		...


@dataclass
class StrategyResult:
	name: str
	signal: Signal