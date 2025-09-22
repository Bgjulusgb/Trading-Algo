from __future__ import annotations

import argparse
import signal
import sys
import time

from .config import load_config
from .data import DataProvider
from .alpaca_client import AlpacaClient
from .engine import TradingEngine


def build_arg_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Multi-strategy trading bot")
	parser.add_argument("--env-file", type=str, default=".env", help="Path to .env file")
	parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols override")
	parser.add_argument("--timeframe", type=str, default=None, help="Timeframe override e.g. 1Min, 5Min, 1D")
	parser.add_argument("--poll", type=int, default=None, help="Polling seconds override")
	return parser


def main(argv=None) -> int:
	args = build_arg_parser().parse_args(argv)
	config = load_config(args.env_file)
	if args.symbols:
		config.symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
	if args.timeframe:
		config.timeframe = args.timeframe
	if args.poll:
		config.poll_interval_seconds = int(args.poll)

	data = DataProvider(config)
	broker = AlpacaClient(config)
	engine = TradingEngine(config, data, broker)

	stop = False

	def handle_sigint(signum, frame):
		nonlocal stop
		stop = True

	signal.signal(signal.SIGINT, handle_sigint)
	print(f"Starting loop. Symbols={config.symbols}, timeframe={config.timeframe}, poll={config.poll_interval_seconds}s")
	while not stop:
		try:
			decisions = engine.step()
			for sym, d in decisions.items():
				print(f"{sym}: {d.signal} | reasons={','.join(d.reasons)}")
			time.sleep(config.poll_interval_seconds)
		except Exception as e:
			print("Loop error:", e)
			time.sleep(config.poll_interval_seconds)

	print("Stopped.")
	return 0


if __name__ == "__main__":
	sys.exit(main())