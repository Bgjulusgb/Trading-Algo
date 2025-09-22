"""
Example usage of the Advanced Trading Algorithm
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from advanced_trading_algo import TradingConfig, StrategyEngine, TradingBot, TradingSignal
from backtesting import Backtester
from risk_manager import RiskManager
import yfinance as yf
import pandas as pd

def example_signal_generation():
    """Example: Generate trading signals for a symbol"""
    print("🎯 Example: Signal Generation")
    print("=" * 40)
    
    # Initialize components
    config = TradingConfig()
    strategy_engine = StrategyEngine(config)
    
    # Get market data
    symbol = "AAPL"
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="6mo")
    
    if data.empty:
        print(f"❌ No data available for {symbol}")
        return
    
    # Generate signal
    signal = strategy_engine.generate_combined_signal(data, symbol)
    
    if signal:
        print(f"📊 Signal for {symbol}:")
        print(f"   Type: {signal.signal_type.value.upper()}")
        print(f"   Strategy: {signal.strategy}")
        print(f"   Confidence: {signal.confidence:.1%}")
        print(f"   Price: ${signal.price:.2f}")
        if signal.stop_loss:
            print(f"   Stop Loss: ${signal.stop_loss:.2f}")
        if signal.take_profit:
            print(f"   Take Profit: ${signal.take_profit:.2f}")
    else:
        print(f"📊 No strong signal for {symbol}")
    
    print()

def example_backtesting():
    """Example: Run backtesting"""
    print("📈 Example: Backtesting")
    print("=" * 40)
    
    # Initialize backtester
    config = TradingConfig()
    backtester = Backtester(config, initial_capital=100000)
    
    # Run backtest
    symbols = ["AAPL", "GOOGL", "MSFT"]
    start_date = "2023-01-01"
    end_date = "2024-01-01"
    
    print(f"Running backtest for {symbols} from {start_date} to {end_date}...")
    result = backtester.run_backtest(symbols, start_date, end_date)
    
    # Display results
    print(f"📊 Backtest Results:")
    print(f"   Initial Capital: ${result.initial_capital:,.2f}")
    print(f"   Final Capital: ${result.final_capital:,.2f}")
    print(f"   Total Return: {result.total_return:.2%}")
    print(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"   Max Drawdown: {result.max_drawdown:.2%}")
    print(f"   Win Rate: {result.win_rate:.2%}")
    print(f"   Total Trades: {result.total_trades}")
    
    print()

def example_risk_management():
    """Example: Risk management analysis"""
    print("🔒 Example: Risk Management")
    print("=" * 40)
    
    # Initialize risk manager
    config = TradingConfig()
    risk_manager = RiskManager(config)
    
    # Example portfolio
    positions = {
        'AAPL': 1000,
        'GOOGL': 500,
        'MSFT': 800,
        'TSLA': 300
    }
    
    # Get returns data
    symbols = list(positions.keys()) + ['SPY']
    returns_dict = {}
    
    print("Loading market data...")
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1y")
            if not data.empty:
                returns_dict[symbol] = data['Close'].pct_change().dropna()
        except Exception as e:
            print(f"Error loading {symbol}: {e}")
    
    if not returns_dict:
        print("❌ No market data available")
        return
    
    # Calculate portfolio returns
    total_value = sum(abs(pos) for pos in positions.values())
    portfolio_returns = pd.Series(0.0, index=list(returns_dict.values())[0].index)
    
    for symbol, position in positions.items():
        if symbol in returns_dict:
            weight = abs(position) / total_value
            portfolio_returns += returns_dict[symbol] * weight
    
    # Generate risk report
    risk_report = risk_manager.generate_risk_report(positions, returns_dict, portfolio_returns)
    
    print(f"📊 Portfolio Risk Analysis:")
    print(f"   Risk Level: {risk_report['portfolio_metrics'].risk_level.value.upper()}")
    print(f"   Portfolio VaR (5%): {risk_report['portfolio_metrics'].portfolio_var:.2%}")
    print(f"   Max Drawdown: {risk_report['portfolio_metrics'].max_drawdown:.2%}")
    print(f"   Sharpe Ratio: {risk_report['portfolio_metrics'].sharpe_ratio:.2f}")
    print(f"   Concentration Risk: {risk_report['portfolio_metrics'].concentration_risk:.2%}")
    
    if risk_report['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in risk_report['warnings']:
            print(f"   - {warning}")
    
    if risk_report['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in risk_report['recommendations']:
            print(f"   - {rec}")
    
    print()

def example_strategy_comparison():
    """Example: Compare different strategies"""
    print("📊 Example: Strategy Comparison")
    print("=" * 40)
    
    config = TradingConfig()
    
    # Test configurations
    strategies = [
        {"name": "RSI Only", "rsi": True, "macd": False, "bollinger": False, "ma_crossover": False},
        {"name": "MACD Only", "rsi": False, "macd": True, "bollinger": False, "ma_crossover": False},
        {"name": "All Strategies", "rsi": True, "macd": True, "bollinger": True, "ma_crossover": True},
    ]
    
    results = {}
    symbols = ["AAPL"]
    
    for strategy in strategies:
        print(f"Testing {strategy['name']}...")
        
        # Update config
        for strat_name, enabled in strategy.items():
            if strat_name != "name":
                config.config["strategies"][strat_name]["enabled"] = enabled
        
        # Run backtest
        backtester = Backtester(config, initial_capital=10000)
        result = backtester.run_backtest(symbols, "2023-01-01", "2024-01-01")
        results[strategy["name"]] = result
    
    # Display comparison
    print(f"\n📊 Strategy Comparison Results:")
    print(f"{'Strategy':<15} {'Return':<8} {'Sharpe':<8} {'Drawdown':<10} {'Trades':<8}")
    print("-" * 60)
    
    for name, result in results.items():
        print(f"{name:<15} {result.total_return:>7.1%} {result.sharpe_ratio:>7.2f} "
              f"{result.max_drawdown:>9.1%} {result.total_trades:>7}")
    
    print()

def example_configuration():
    """Example: Configuration management"""
    print("⚙️ Example: Configuration")
    print("=" * 40)
    
    config = TradingConfig()
    
    print("📋 Current Configuration:")
    print(f"   Trading Symbols: {config.get('trading.symbols')}")
    print(f"   Max Position Size: {config.get('trading.max_position_size'):.1%}")
    print(f"   Stop Loss: {config.get('trading.stop_loss_pct'):.1%}")
    print(f"   Take Profit: {config.get('trading.take_profit_pct'):.1%}")
    print(f"   Min Confidence: {config.get('trading.min_confidence'):.1%}")
    print(f"   Update Interval: {config.get('data.update_interval')} seconds")
    
    # Show enabled strategies
    print(f"\n📈 Enabled Strategies:")
    for strategy in ['rsi', 'macd', 'bollinger', 'ma_crossover']:
        enabled = config.get(f'strategies.{strategy}.enabled')
        weight = config.get(f'strategies.{strategy}.weight')
        status = "✅" if enabled else "❌"
        print(f"   {status} {strategy.upper()}: Weight {weight:.2f}")
    
    print()

def main():
    """Run all examples"""
    print("🚀 Advanced Trading Algorithm - Examples")
    print("=" * 50)
    print()
    
    try:
        # Run examples
        example_configuration()
        example_signal_generation()
        example_backtesting()
        example_risk_management()
        example_strategy_comparison()
        
        print("✅ All examples completed successfully!")
        print("\n🔗 Next Steps:")
        print("   1. Configure your Alpaca API credentials in trading_config.json")
        print("   2. Run the dashboard: python run_dashboard.py")
        print("   3. Start paper trading: python run_bot.py --mode paper")
        print("   4. Monitor performance and adjust strategies")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()