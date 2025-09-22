"""
Backtesting module for trading strategies
"""

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
from advanced_trading_algo import TradingConfig, StrategyEngine, TradingSignal, SignalType

logger = logging.getLogger(__name__)

class BacktestResult:
    """Container for backtesting results"""
    
    def __init__(self):
        self.trades = []
        self.portfolio_values = []
        self.dates = []
        self.initial_capital = 0
        self.final_capital = 0
        self.total_return = 0
        self.sharpe_ratio = 0
        self.max_drawdown = 0
        self.win_rate = 0
        self.profit_factor = 0
        self.total_trades = 0

class Backtester:
    """Backtesting engine for trading strategies"""
    
    def __init__(self, config: TradingConfig, initial_capital: float = 100000):
        self.config = config
        self.strategy_engine = StrategyEngine(config)
        self.initial_capital = initial_capital
        self.reset()
    
    def reset(self):
        """Reset backtester state"""
        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.portfolio_values = []
        self.dates = []
    
    def run_backtest(self, symbols: List[str], start_date: str, end_date: str) -> BacktestResult:
        """Run backtest for given symbols and date range"""
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        self.reset()
        
        # Get data for all symbols
        data_dict = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(start=start_date, end=end_date)
                if not data.empty:
                    data_dict[symbol] = data
                    logger.info(f"Loaded data for {symbol}: {len(data)} days")
            except Exception as e:
                logger.error(f"Error loading data for {symbol}: {e}")
        
        if not data_dict:
            logger.error("No data loaded for backtesting")
            return BacktestResult()
        
        # Get all unique dates
        all_dates = set()
        for data in data_dict.values():
            all_dates.update(data.index)
        all_dates = sorted(all_dates)
        
        # Run backtest day by day
        for date in all_dates:
            self.process_day(date, data_dict)
        
        # Calculate results
        return self.calculate_results()
    
    def process_day(self, date: pd.Timestamp, data_dict: Dict[str, pd.DataFrame]):
        """Process one trading day"""
        daily_portfolio_value = self.capital
        
        # Update positions value
        for symbol, position in self.positions.items():
            if symbol in data_dict and date in data_dict[symbol].index:
                current_price = data_dict[symbol].loc[date, 'Close']
                daily_portfolio_value += position['shares'] * current_price
        
        self.portfolio_values.append(daily_portfolio_value)
        self.dates.append(date)
        
        # Generate signals for each symbol
        for symbol, data in data_dict.items():
            if date not in data.index:
                continue
            
            # Get data up to current date for signal generation
            historical_data = data.loc[:date].copy()
            if len(historical_data) < 50:  # Need enough data for indicators
                continue
            
            # Generate signal
            signal = self.strategy_engine.generate_combined_signal(historical_data, symbol)
            
            if signal and signal.confidence >= self.config.get('trading.min_confidence', 0.6):
                self.execute_signal(signal, date, data.loc[date, 'Close'])
    
    def execute_signal(self, signal: TradingSignal, date: pd.Timestamp, price: float):
        """Execute trading signal in backtest"""
        symbol = signal.symbol
        
        # Calculate position size (simplified for backtesting)
        max_position_value = self.capital * self.config.get('trading.max_position_size', 0.1)
        shares = int(max_position_value / price)
        
        if signal.signal_type == SignalType.BUY:
            # Buy signal
            cost = shares * price
            if cost <= self.capital:
                self.capital -= cost
                self.positions[symbol] = {
                    'shares': shares,
                    'entry_price': price,
                    'entry_date': date,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit
                }
                
                trade = {
                    'symbol': symbol,
                    'type': 'BUY',
                    'shares': shares,
                    'price': price,
                    'date': date,
                    'strategy': signal.strategy,
                    'confidence': signal.confidence
                }
                self.trades.append(trade)
                logger.debug(f"BUY {shares} shares of {symbol} at ${price:.2f}")
        
        elif signal.signal_type == SignalType.SELL and symbol in self.positions:
            # Sell signal
            position = self.positions[symbol]
            revenue = position['shares'] * price
            self.capital += revenue
            
            # Calculate profit/loss
            profit_loss = (price - position['entry_price']) * position['shares']
            
            trade = {
                'symbol': symbol,
                'type': 'SELL',
                'shares': position['shares'],
                'price': price,
                'date': date,
                'strategy': signal.strategy,
                'confidence': signal.confidence,
                'entry_price': position['entry_price'],
                'profit_loss': profit_loss,
                'return_pct': (price - position['entry_price']) / position['entry_price']
            }
            self.trades.append(trade)
            logger.debug(f"SELL {position['shares']} shares of {symbol} at ${price:.2f}, P&L: ${profit_loss:.2f}")
            
            del self.positions[symbol]
    
    def calculate_results(self) -> BacktestResult:
        """Calculate backtesting results and metrics"""
        result = BacktestResult()
        result.trades = self.trades
        result.portfolio_values = self.portfolio_values
        result.dates = self.dates
        result.initial_capital = self.initial_capital
        result.final_capital = self.portfolio_values[-1] if self.portfolio_values else self.initial_capital
        
        # Total return
        result.total_return = (result.final_capital - result.initial_capital) / result.initial_capital
        
        # Calculate daily returns
        if len(self.portfolio_values) > 1:
            portfolio_series = pd.Series(self.portfolio_values, index=self.dates)
            daily_returns = portfolio_series.pct_change().dropna()
            
            # Sharpe ratio (assuming 0% risk-free rate)
            if daily_returns.std() != 0:
                result.sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
            
            # Maximum drawdown
            peak = portfolio_series.expanding().max()
            drawdown = (portfolio_series - peak) / peak
            result.max_drawdown = drawdown.min()
        
        # Trade statistics
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        result.total_trades = len(sell_trades)
        
        if sell_trades:
            profits = [t['profit_loss'] for t in sell_trades]
            winning_trades = [p for p in profits if p > 0]
            losing_trades = [p for p in profits if p < 0]
            
            result.win_rate = len(winning_trades) / len(sell_trades) if sell_trades else 0
            
            if losing_trades:
                gross_profit = sum(winning_trades) if winning_trades else 0
                gross_loss = abs(sum(losing_trades))
                result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return result
    
    def plot_results(self, result: BacktestResult, save_path: str = None):
        """Plot backtesting results"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Backtesting Results', fontsize=16)
        
        # Portfolio value over time
        axes[0, 0].plot(result.dates, result.portfolio_values)
        axes[0, 0].set_title('Portfolio Value Over Time')
        axes[0, 0].set_xlabel('Date')
        axes[0, 0].set_ylabel('Portfolio Value ($)')
        axes[0, 0].grid(True)
        
        # Drawdown
        if len(result.portfolio_values) > 1:
            portfolio_series = pd.Series(result.portfolio_values, index=result.dates)
            peak = portfolio_series.expanding().max()
            drawdown = (portfolio_series - peak) / peak * 100
            axes[0, 1].fill_between(result.dates, drawdown, 0, alpha=0.3, color='red')
            axes[0, 1].set_title('Drawdown (%)')
            axes[0, 1].set_xlabel('Date')
            axes[0, 1].set_ylabel('Drawdown (%)')
            axes[0, 1].grid(True)
        
        # Trade distribution
        sell_trades = [t for t in result.trades if t['type'] == 'SELL']
        if sell_trades:
            profits = [t['profit_loss'] for t in sell_trades]
            axes[1, 0].hist(profits, bins=20, alpha=0.7)
            axes[1, 0].set_title('Trade P&L Distribution')
            axes[1, 0].set_xlabel('Profit/Loss ($)')
            axes[1, 0].set_ylabel('Frequency')
            axes[1, 0].axvline(x=0, color='red', linestyle='--')
            axes[1, 0].grid(True)
        
        # Performance metrics
        metrics_text = f"""
        Total Return: {result.total_return:.2%}
        Sharpe Ratio: {result.sharpe_ratio:.2f}
        Max Drawdown: {result.max_drawdown:.2%}
        Win Rate: {result.win_rate:.2%}
        Profit Factor: {result.profit_factor:.2f}
        Total Trades: {result.total_trades}
        """
        axes[1, 1].text(0.1, 0.5, metrics_text, transform=axes[1, 1].transAxes, 
                        fontsize=12, verticalalignment='center')
        axes[1, 1].set_title('Performance Metrics')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()

def run_strategy_comparison():
    """Compare different strategy configurations"""
    config = TradingConfig()
    
    # Test different strategy combinations
    strategy_configs = [
        {"name": "RSI Only", "enabled": {"rsi": True, "macd": False, "bollinger": False, "ma_crossover": False}},
        {"name": "MACD Only", "enabled": {"rsi": False, "macd": True, "bollinger": False, "ma_crossover": False}},
        {"name": "Bollinger Only", "enabled": {"rsi": False, "macd": False, "bollinger": True, "ma_crossover": False}},
        {"name": "MA Crossover Only", "enabled": {"rsi": False, "macd": False, "bollinger": False, "ma_crossover": True}},
        {"name": "All Strategies", "enabled": {"rsi": True, "macd": True, "bollinger": True, "ma_crossover": True}},
    ]
    
    results = {}
    symbols = ["AAPL", "GOOGL", "MSFT"]
    start_date = "2023-01-01"
    end_date = "2024-01-01"
    
    for strategy_config in strategy_configs:
        # Update config
        for strategy, enabled in strategy_config["enabled"].items():
            config.config["strategies"][strategy]["enabled"] = enabled
        
        # Run backtest
        backtester = Backtester(config)
        result = backtester.run_backtest(symbols, start_date, end_date)
        results[strategy_config["name"]] = result
        
        print(f"\n{strategy_config['name']} Results:")
        print(f"Total Return: {result.total_return:.2%}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {result.max_drawdown:.2%}")
        print(f"Win Rate: {result.win_rate:.2%}")
        print(f"Total Trades: {result.total_trades}")
    
    return results

if __name__ == "__main__":
    # Example usage
    config = TradingConfig()
    backtester = Backtester(config)
    
    # Run backtest
    symbols = ["AAPL", "GOOGL", "MSFT"]
    start_date = "2023-01-01"
    end_date = "2024-01-01"
    
    result = backtester.run_backtest(symbols, start_date, end_date)
    
    print(f"Backtesting Results:")
    print(f"Initial Capital: ${result.initial_capital:,.2f}")
    print(f"Final Capital: ${result.final_capital:,.2f}")
    print(f"Total Return: {result.total_return:.2%}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {result.max_drawdown:.2%}")
    print(f"Win Rate: {result.win_rate:.2%}")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    print(f"Total Trades: {result.total_trades}")
    
    # Plot results
    backtester.plot_results(result, 'backtest_results.png')
    
    # Run strategy comparison
    print("\n" + "="*50)
    print("STRATEGY COMPARISON")
    print("="*50)
    run_strategy_comparison()