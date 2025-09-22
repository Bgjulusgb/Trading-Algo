"""
Advanced Trading Algorithm with Multiple Strategies and Alpaca Integration
Supports RSI, MACD, Bollinger Bands, and Moving Average Crossover strategies
"""

import pandas as pd
import numpy as np
import yfinance as yf
import alpaca_trade_api as tradeapi
import ta
from datetime import datetime, timedelta
import time
import logging
import json
import os
from typing import Dict, List, Tuple, Optional
import threading
from dataclasses import dataclass
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_algo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class TradingSignal:
    symbol: str
    signal_type: SignalType
    confidence: float
    strategy: str
    price: float
    timestamp: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class TradingConfig:
    """Trading configuration and parameters"""
    
    def __init__(self, config_file: str = 'trading_config.json'):
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            "alpaca": {
                "api_key": "",
                "secret_key": "",
                "base_url": "https://paper-api.alpaca.markets",  # Paper trading
                "data_url": "https://data.alpaca.markets"
            },
            "trading": {
                "symbols": ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"],
                "max_position_size": 0.1,  # 10% of portfolio per position
                "stop_loss_pct": 0.02,     # 2% stop loss
                "take_profit_pct": 0.04,   # 4% take profit
                "min_confidence": 0.6,     # Minimum signal confidence
                "risk_per_trade": 0.01     # 1% risk per trade
            },
            "strategies": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70,
                    "weight": 0.25
                },
                "macd": {
                    "enabled": True,
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "weight": 0.25
                },
                "bollinger": {
                    "enabled": True,
                    "period": 20,
                    "std_dev": 2,
                    "weight": 0.25
                },
                "ma_crossover": {
                    "enabled": True,
                    "fast_ma": 10,
                    "slow_ma": 30,
                    "weight": 0.25
                }
            },
            "data": {
                "update_interval": 60,  # seconds
                "lookback_days": 100
            }
        }
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                # Merge with defaults
                self.config = {**default_config, **loaded_config}
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Save configuration to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

class TechnicalAnalysis:
    """Technical analysis strategies"""
    
    @staticmethod
    def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        return ta.momentum.RSIIndicator(data['Close'], window=period).rsi()
    
    @staticmethod
    def calculate_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD indicator"""
        macd = ta.trend.MACD(data['Close'], window_fast=fast, window_slow=slow, window_sign=signal)
        return {
            'macd': macd.macd(),
            'signal': macd.macd_signal(),
            'histogram': macd.macd_diff()
        }
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict:
        """Calculate Bollinger Bands"""
        bb = ta.volatility.BollingerBands(data['Close'], window=period, window_dev=std_dev)
        return {
            'upper': bb.bollinger_hband(),
            'middle': bb.bollinger_mavg(),
            'lower': bb.bollinger_lband()
        }
    
    @staticmethod
    def calculate_moving_averages(data: pd.DataFrame, fast: int = 10, slow: int = 30) -> Dict:
        """Calculate moving averages"""
        return {
            'fast_ma': ta.trend.SMAIndicator(data['Close'], window=fast).sma_indicator(),
            'slow_ma': ta.trend.SMAIndicator(data['Close'], window=slow).sma_indicator()
        }

class StrategyEngine:
    """Strategy engine for generating trading signals"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.ta = TechnicalAnalysis()
    
    def analyze_rsi_strategy(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """RSI-based trading strategy"""
        if not self.config.get('strategies.rsi.enabled', True):
            return None
        
        rsi_period = self.config.get('strategies.rsi.period', 14)
        oversold = self.config.get('strategies.rsi.oversold', 30)
        overbought = self.config.get('strategies.rsi.overbought', 70)
        
        rsi = self.ta.calculate_rsi(data, rsi_period)
        current_rsi = rsi.iloc[-1]
        current_price = data['Close'].iloc[-1]
        
        if current_rsi < oversold:
            confidence = (oversold - current_rsi) / oversold
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=min(confidence, 1.0),
                strategy="RSI",
                price=current_price,
                timestamp=datetime.now(),
                stop_loss=current_price * (1 - self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=current_price * (1 + self.config.get('trading.take_profit_pct', 0.04))
            )
        elif current_rsi > overbought:
            confidence = (current_rsi - overbought) / (100 - overbought)
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=min(confidence, 1.0),
                strategy="RSI",
                price=current_price,
                timestamp=datetime.now(),
                stop_loss=current_price * (1 + self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=current_price * (1 - self.config.get('trading.take_profit_pct', 0.04))
            )
        
        return None
    
    def analyze_macd_strategy(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """MACD-based trading strategy"""
        if not self.config.get('strategies.macd.enabled', True):
            return None
        
        fast = self.config.get('strategies.macd.fast_period', 12)
        slow = self.config.get('strategies.macd.slow_period', 26)
        signal_period = self.config.get('strategies.macd.signal_period', 9)
        
        macd_data = self.ta.calculate_macd(data, fast, slow, signal_period)
        current_macd = macd_data['macd'].iloc[-1]
        current_signal = macd_data['signal'].iloc[-1]
        prev_macd = macd_data['macd'].iloc[-2]
        prev_signal = macd_data['signal'].iloc[-2]
        current_price = data['Close'].iloc[-1]
        
        # MACD crossover signals
        if prev_macd <= prev_signal and current_macd > current_signal:
            confidence = abs(current_macd - current_signal) / current_price * 1000
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=min(confidence, 1.0),
                strategy="MACD",
                price=current_price,
                timestamp=datetime.now(),
                stop_loss=current_price * (1 - self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=current_price * (1 + self.config.get('trading.take_profit_pct', 0.04))
            )
        elif prev_macd >= prev_signal and current_macd < current_signal:
            confidence = abs(current_macd - current_signal) / current_price * 1000
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=min(confidence, 1.0),
                strategy="MACD",
                price=current_price,
                timestamp=datetime.now(),
                stop_loss=current_price * (1 + self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=current_price * (1 - self.config.get('trading.take_profit_pct', 0.04))
            )
        
        return None
    
    def analyze_bollinger_strategy(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """Bollinger Bands-based trading strategy"""
        if not self.config.get('strategies.bollinger.enabled', True):
            return None
        
        period = self.config.get('strategies.bollinger.period', 20)
        std_dev = self.config.get('strategies.bollinger.std_dev', 2)
        
        bb = self.ta.calculate_bollinger_bands(data, period, std_dev)
        current_price = data['Close'].iloc[-1]
        upper_band = bb['upper'].iloc[-1]
        lower_band = bb['lower'].iloc[-1]
        middle_band = bb['middle'].iloc[-1]
        
        # Price touching lower band - potential buy signal
        if current_price <= lower_band:
            confidence = (lower_band - current_price) / (middle_band - lower_band)
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=min(confidence, 1.0),
                strategy="Bollinger",
                price=current_price,
                timestamp=datetime.now(),
                stop_loss=current_price * (1 - self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=middle_band
            )
        # Price touching upper band - potential sell signal
        elif current_price >= upper_band:
            confidence = (current_price - upper_band) / (upper_band - middle_band)
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=min(confidence, 1.0),
                strategy="Bollinger",
                price=current_price,
                timestamp=datetime.now(),
                stop_loss=current_price * (1 + self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=middle_band
            )
        
        return None
    
    def analyze_ma_crossover_strategy(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """Moving Average Crossover strategy"""
        if not self.config.get('strategies.ma_crossover.enabled', True):
            return None
        
        fast_ma = self.config.get('strategies.ma_crossover.fast_ma', 10)
        slow_ma = self.config.get('strategies.ma_crossover.slow_ma', 30)
        
        ma_data = self.ta.calculate_moving_averages(data, fast_ma, slow_ma)
        current_fast = ma_data['fast_ma'].iloc[-1]
        current_slow = ma_data['slow_ma'].iloc[-1]
        prev_fast = ma_data['fast_ma'].iloc[-2]
        prev_slow = ma_data['slow_ma'].iloc[-2]
        current_price = data['Close'].iloc[-1]
        
        # Golden cross - fast MA crosses above slow MA
        if prev_fast <= prev_slow and current_fast > current_slow:
            confidence = (current_fast - current_slow) / current_slow
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=min(confidence, 1.0),
                strategy="MA_Crossover",
                price=current_price,
                timestamp=datetime.now(),
                stop_loss=current_price * (1 - self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=current_price * (1 + self.config.get('trading.take_profit_pct', 0.04))
            )
        # Death cross - fast MA crosses below slow MA
        elif prev_fast >= prev_slow and current_fast < current_slow:
            confidence = (current_slow - current_fast) / current_slow
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=min(confidence, 1.0),
                strategy="MA_Crossover",
                price=current_price,
                timestamp=datetime.now(),
                stop_loss=current_price * (1 + self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=current_price * (1 - self.config.get('trading.take_profit_pct', 0.04))
            )
        
        return None
    
    def generate_combined_signal(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """Generate combined signal from all strategies"""
        signals = []
        
        # Get signals from all strategies
        rsi_signal = self.analyze_rsi_strategy(data, symbol)
        macd_signal = self.analyze_macd_strategy(data, symbol)
        bb_signal = self.analyze_bollinger_strategy(data, symbol)
        ma_signal = self.analyze_ma_crossover_strategy(data, symbol)
        
        # Collect valid signals
        for signal in [rsi_signal, macd_signal, bb_signal, ma_signal]:
            if signal:
                signals.append(signal)
        
        if not signals:
            return None
        
        # Calculate weighted confidence
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        if len(buy_signals) > len(sell_signals):
            # More buy signals
            weighted_confidence = sum(s.confidence * self.config.get(f'strategies.{s.strategy.lower()}.weight', 0.25) 
                                    for s in buy_signals) / len(buy_signals)
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=weighted_confidence,
                strategy="Combined",
                price=data['Close'].iloc[-1],
                timestamp=datetime.now(),
                stop_loss=data['Close'].iloc[-1] * (1 - self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=data['Close'].iloc[-1] * (1 + self.config.get('trading.take_profit_pct', 0.04))
            )
        elif len(sell_signals) > len(buy_signals):
            # More sell signals
            weighted_confidence = sum(s.confidence * self.config.get(f'strategies.{s.strategy.lower()}.weight', 0.25) 
                                    for s in sell_signals) / len(sell_signals)
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=weighted_confidence,
                strategy="Combined",
                price=data['Close'].iloc[-1],
                timestamp=datetime.now(),
                stop_loss=data['Close'].iloc[-1] * (1 + self.config.get('trading.stop_loss_pct', 0.02)),
                take_profit=data['Close'].iloc[-1] * (1 - self.config.get('trading.take_profit_pct', 0.04))
            )
        
        return None

class AlpacaTrader:
    """Alpaca API integration for live trading"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.api = None
        self.initialize_api()
    
    def initialize_api(self):
        """Initialize Alpaca API connection"""
        try:
            api_key = self.config.get('alpaca.api_key')
            secret_key = self.config.get('alpaca.secret_key')
            base_url = self.config.get('alpaca.base_url')
            
            if not api_key or not secret_key:
                logger.error("Alpaca API credentials not found in config")
                return
            
            self.api = tradeapi.REST(
                api_key,
                secret_key,
                base_url,
                api_version='v2'
            )
            
            # Test connection
            account = self.api.get_account()
            logger.info(f"Connected to Alpaca API. Account status: {account.status}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca API: {e}")
            self.api = None
    
    def get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        if not self.api:
            return 0.0
        
        try:
            account = self.api.get_account()
            return float(account.portfolio_value)
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return 0.0
    
    def get_buying_power(self) -> float:
        """Get available buying power"""
        if not self.api:
            return 0.0
        
        try:
            account = self.api.get_account()
            return float(account.buying_power)
        except Exception as e:
            logger.error(f"Error getting buying power: {e}")
            return 0.0
    
    def calculate_position_size(self, signal: TradingSignal) -> int:
        """Calculate appropriate position size based on risk management"""
        portfolio_value = self.get_portfolio_value()
        if portfolio_value == 0:
            return 0
        
        # Calculate position size based on risk per trade
        risk_amount = portfolio_value * self.config.get('trading.risk_per_trade', 0.01)
        
        if signal.stop_loss:
            risk_per_share = abs(signal.price - signal.stop_loss)
            if risk_per_share > 0:
                shares = int(risk_amount / risk_per_share)
            else:
                shares = 0
        else:
            # Fallback to max position size
            max_position_value = portfolio_value * self.config.get('trading.max_position_size', 0.1)
            shares = int(max_position_value / signal.price)
        
        # Ensure we don't exceed buying power
        buying_power = self.get_buying_power()
        max_shares_by_power = int(buying_power / signal.price)
        
        return min(shares, max_shares_by_power, 100)  # Cap at 100 shares for safety
    
    def place_order(self, signal: TradingSignal) -> bool:
        """Place order based on trading signal"""
        if not self.api:
            logger.error("Alpaca API not initialized")
            return False
        
        try:
            # Calculate position size
            qty = self.calculate_position_size(signal)
            if qty <= 0:
                logger.warning(f"Invalid position size for {signal.symbol}: {qty}")
                return False
            
            # Determine order side
            side = 'buy' if signal.signal_type == SignalType.BUY else 'sell'
            
            # Place market order
            order = self.api.submit_order(
                symbol=signal.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='day'
            )
            
            logger.info(f"Order placed: {side.upper()} {qty} shares of {signal.symbol} at market price")
            logger.info(f"Order ID: {order.id}")
            
            # Place stop loss and take profit orders if specified
            if signal.signal_type == SignalType.BUY and signal.stop_loss:
                self.place_stop_loss_order(signal.symbol, qty, signal.stop_loss)
            
            if signal.signal_type == SignalType.BUY and signal.take_profit:
                self.place_take_profit_order(signal.symbol, qty, signal.take_profit)
            
            return True
            
        except Exception as e:
            logger.error(f"Error placing order for {signal.symbol}: {e}")
            return False
    
    def place_stop_loss_order(self, symbol: str, qty: int, stop_price: float):
        """Place stop loss order"""
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='stop',
                stop_price=stop_price,
                time_in_force='gtc'
            )
            logger.info(f"Stop loss order placed for {symbol} at ${stop_price:.2f}")
        except Exception as e:
            logger.error(f"Error placing stop loss order: {e}")
    
    def place_take_profit_order(self, symbol: str, qty: int, limit_price: float):
        """Place take profit order"""
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='limit',
                limit_price=limit_price,
                time_in_force='gtc'
            )
            logger.info(f"Take profit order placed for {symbol} at ${limit_price:.2f}")
        except Exception as e:
            logger.error(f"Error placing take profit order: {e}")
    
    def get_positions(self) -> List:
        """Get current positions"""
        if not self.api:
            return []
        
        try:
            return self.api.list_positions()
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

class TradingBot:
    """Main trading bot class"""
    
    def __init__(self, config_file: str = 'trading_config.json'):
        self.config = TradingConfig(config_file)
        self.strategy_engine = StrategyEngine(self.config)
        self.trader = AlpacaTrader(self.config)
        self.running = False
        self.data_cache = {}
    
    def get_market_data(self, symbol: str) -> pd.DataFrame:
        """Get market data for symbol"""
        try:
            lookback_days = self.config.get('data.lookback_days', 100)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                logger.warning(f"No data available for {symbol}")
                return pd.DataFrame()
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def update_data_cache(self):
        """Update data cache for all symbols"""
        symbols = self.config.get('trading.symbols', [])
        for symbol in symbols:
            self.data_cache[symbol] = self.get_market_data(symbol)
            logger.info(f"Updated data cache for {symbol}")
    
    def generate_signals(self) -> List[TradingSignal]:
        """Generate trading signals for all symbols"""
        signals = []
        
        for symbol, data in self.data_cache.items():
            if data.empty:
                continue
            
            signal = self.strategy_engine.generate_combined_signal(data, symbol)
            if signal and signal.confidence >= self.config.get('trading.min_confidence', 0.6):
                signals.append(signal)
                logger.info(f"Generated {signal.signal_type.value} signal for {symbol} "
                           f"(confidence: {signal.confidence:.2f}, strategy: {signal.strategy})")
        
        return signals
    
    def execute_signals(self, signals: List[TradingSignal]):
        """Execute trading signals"""
        for signal in signals:
            success = self.trader.place_order(signal)
            if success:
                logger.info(f"Successfully executed {signal.signal_type.value} order for {signal.symbol}")
            else:
                logger.error(f"Failed to execute order for {signal.symbol}")
    
    def run_trading_cycle(self):
        """Run one trading cycle"""
        logger.info("Starting trading cycle...")
        
        # Update market data
        self.update_data_cache()
        
        # Generate signals
        signals = self.generate_signals()
        
        if signals:
            logger.info(f"Generated {len(signals)} trading signals")
            # Execute signals
            self.execute_signals(signals)
        else:
            logger.info("No trading signals generated")
        
        # Log portfolio status
        portfolio_value = self.trader.get_portfolio_value()
        positions = self.trader.get_positions()
        logger.info(f"Portfolio value: ${portfolio_value:.2f}")
        logger.info(f"Active positions: {len(positions)}")
        
        logger.info("Trading cycle completed")
    
    def start(self):
        """Start the trading bot"""
        logger.info("Starting Advanced Trading Bot...")
        self.running = True
        
        update_interval = self.config.get('data.update_interval', 60)
        
        while self.running:
            try:
                self.run_trading_cycle()
                time.sleep(update_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping bot...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}")
                time.sleep(30)  # Wait 30 seconds before retrying
    
    def stop(self):
        """Stop the trading bot"""
        self.running = False
        logger.info("Trading bot stopped")

def main():
    """Main function to run the trading bot"""
    # Create default config if it doesn't exist
    config = TradingConfig()
    
    # Check if API credentials are configured
    if not config.get('alpaca.api_key') or not config.get('alpaca.secret_key'):
        logger.error("Please configure your Alpaca API credentials in trading_config.json")
        logger.info("Example configuration has been created in trading_config.json")
        return
    
    # Initialize and start trading bot
    bot = TradingBot()
    
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.stop()

if __name__ == "__main__":
    main()