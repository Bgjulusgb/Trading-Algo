import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


@dataclass
class TradingConfig:
	alpaca_api_key_id: str
	alpaca_api_secret_key: str
	alpaca_base_url: str
	symbols: List[str]
	timeframe: str
	lookback_bars: int
	poll_interval_seconds: int
	max_notional_per_trade: float
	long_only: bool
	order_time_in_force: str
	stop_loss_pct: float
	take_profit_pct: float
	aggregate_rule: str
	min_strategies_agree: int
	use_alpaca_data: bool


TRUE_SET = {"1", "true", "yes", "y", "on"}


def _get_bool(name: str, default: bool) -> bool:
	value = os.getenv(name)
	if value is None:
		return default
	return value.strip().lower() in TRUE_SET


def _get_float(name: str, default: float) -> float:
	value = os.getenv(name)
	return float(value) if value is not None else default


def _get_int(name: str, default: int) -> int:
	value = os.getenv(name)
	return int(value) if value is not None else default


def load_config(env_file: str = ".env") -> TradingConfig:
	# Load .env file if present
	load_dotenv(env_file, override=False)

	alpaca_api_key_id = os.getenv("ALPACA_API_KEY_ID", "")
	alpaca_api_secret_key = os.getenv("ALPACA_API_SECRET_KEY", "")
	alpaca_base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

	symbols_str = os.getenv("SYMBOLS", "AAPL,MSFT,SPY")
	symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
	timeframe = os.getenv("TIMEFRAME", "1Min")
	lookback_bars = _get_int("LOOKBACK_BARS", 300)
	poll_interval_seconds = _get_int("POLL_INTERVAL_SECONDS", 60)
	max_notional_per_trade = _get_float("MAX_NOTIONAL_PER_TRADE", 1000.0)
	long_only = _get_bool("LONG_ONLY", True)
	order_time_in_force = os.getenv("ORDER_TIME_IN_FORCE", "gtc")
	stop_loss_pct = _get_float("STOP_LOSS_PCT", 0.01)
	take_profit_pct = _get_float("TAKE_PROFIT_PCT", 0.02)
	aggregate_rule = os.getenv("AGGREGATE_RULE", "majority")
	min_strategies_agree = _get_int("MIN_STRATEGIES_AGREE", 3)
	use_alpaca_data = _get_bool("USE_ALPACA_DATA", True)

	if not alpaca_api_key_id or not alpaca_api_secret_key:
		# Allow no keys if user only wants charts/analysis, but warn via print
		print("Warning: ALPACA_API_KEY_ID/ALPACA_API_SECRET_KEY not set. Trading will be disabled.")

	return TradingConfig(
		alpaca_api_key_id=alpaca_api_key_id,
		alpaca_api_secret_key=alpaca_api_secret_key,
		alpaca_base_url=alpaca_base_url,
		symbols=symbols,
		timeframe=timeframe,
		lookback_bars=lookback_bars,
		poll_interval_seconds=poll_interval_seconds,
		max_notional_per_trade=max_notional_per_trade,
		long_only=long_only,
		order_time_in_force=order_time_in_force,
		stop_loss_pct=stop_loss_pct,
		take_profit_pct=take_profit_pct,
		aggregate_rule=aggregate_rule,
		min_strategies_agree=min_strategies_agree,
		use_alpaca_data=use_alpaca_data,
	)