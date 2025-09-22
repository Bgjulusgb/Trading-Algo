#!/usr/bin/env python3
"""
Startup script for the Advanced Trading Bot
"""

import sys
import os
import logging
import argparse
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from advanced_trading_algo import TradingBot, TradingConfig
from risk_manager import RiskManager

def setup_logging(log_level="INFO"):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(f'trading_bot_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_configuration():
    """Check if configuration is properly set up"""
    config = TradingConfig()
    
    # Check API credentials
    api_key = config.get('alpaca.api_key')
    secret_key = config.get('alpaca.secret_key')
    
    if not api_key or not secret_key or api_key == "YOUR_ALPACA_API_KEY_HERE":
        print("❌ Alpaca API credentials not configured!")
        print("Please edit trading_config.json and add your API credentials.")
        print("Get your credentials from: https://alpaca.markets/")
        return False
    
    # Check symbols
    symbols = config.get('trading.symbols', [])
    if not symbols:
        print("❌ No trading symbols configured!")
        return False
    
    print("✅ Configuration looks good!")
    print(f"📊 Trading symbols: {', '.join(symbols)}")
    print(f"🔑 Using API endpoint: {config.get('alpaca.base_url')}")
    
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Advanced Trading Bot')
    parser.add_argument('--mode', choices=['live', 'paper'], default='paper',
                       help='Trading mode (default: paper)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level (default: INFO)')
    parser.add_argument('--config', default='trading_config.json',
                       help='Configuration file path (default: trading_config.json)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run in dry-run mode (no actual trades)')
    parser.add_argument('--backtest', action='store_true',
                       help='Run backtest instead of live trading')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    print("🚀 Advanced Trading Bot")
    print("=" * 50)
    
    # Check configuration
    if not check_configuration():
        sys.exit(1)
    
    try:
        if args.backtest:
            # Run backtesting
            print("📈 Running backtesting mode...")
            from backtesting import Backtester, run_strategy_comparison
            
            config = TradingConfig(args.config)
            backtester = Backtester(config)
            
            symbols = config.get('trading.symbols', ['AAPL', 'GOOGL', 'MSFT'])
            result = backtester.run_backtest(symbols, "2023-01-01", "2024-01-01")
            
            print(f"\n📊 Backtest Results:")
            print(f"Total Return: {result.total_return:.2%}")
            print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
            print(f"Max Drawdown: {result.max_drawdown:.2%}")
            print(f"Win Rate: {result.win_rate:.2%}")
            print(f"Total Trades: {result.total_trades}")
            
            # Plot results
            backtester.plot_results(result)
            
        else:
            # Run live trading
            if args.mode == 'live':
                print("⚠️  LIVE TRADING MODE - Real money at risk!")
                response = input("Are you sure you want to continue? (yes/no): ")
                if response.lower() != 'yes':
                    print("Trading cancelled.")
                    sys.exit(0)
            else:
                print("📄 Paper trading mode - No real money at risk")
            
            if args.dry_run:
                print("🔍 Dry-run mode - No orders will be placed")
            
            # Initialize and start trading bot
            config = TradingConfig(args.config)
            
            # Update config for live/paper trading
            if args.mode == 'live':
                config.config['alpaca']['base_url'] = "https://api.alpaca.markets"
            else:
                config.config['alpaca']['base_url'] = "https://paper-api.alpaca.markets"
            
            bot = TradingBot(args.config)
            
            if args.dry_run:
                # Override trader methods for dry-run
                original_place_order = bot.trader.place_order
                def dry_run_place_order(signal):
                    logger.info(f"DRY-RUN: Would place {signal.signal_type.value} order for {signal.symbol}")
                    return True
                bot.trader.place_order = dry_run_place_order
            
            print(f"🤖 Starting trading bot...")
            print(f"📊 Monitoring {len(config.get('trading.symbols', []))} symbols")
            print(f"⏱️  Update interval: {config.get('data.update_interval', 60)} seconds")
            print("Press Ctrl+C to stop the bot")
            print("=" * 50)
            
            # Start the bot
            bot.start()
            
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        logger.info("Trading bot stopped by user interrupt")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Trading bot error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()