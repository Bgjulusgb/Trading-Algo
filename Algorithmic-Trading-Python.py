import pandas as pd
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.express as px
import yfinance as yf
import streamlit as st
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Alpaca API Integration
try:
    import alpaca_trade_api as tradeapi
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    st.warning("Alpaca API not available. Install with: pip install alpaca-trade-api")

# Order Types
class OrderType:
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide:
    BUY = "buy"
    SELL = "sell"

# Strategy Classes
class TradingStrategy:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def generate_signal(self, data):
        """Generate trading signal based on strategy logic"""
        raise NotImplementedError

class MomentumStrategy(TradingStrategy):
    def __init__(self, period=14):
        super().__init__("Momentum Strategy", f"Momentum based on {period}-day price change")
        self.period = period

    def generate_signal(self, data):
        if len(data) < self.period:
            return "HOLD"

        # Calculate momentum
        momentum = (data['Close'].iloc[-1] - data['Close'].iloc[-self.period]) / data['Close'].iloc[-self.period]

        # Simple momentum signal
        if momentum > 0.05:  # 5% positive momentum
            return "BUY"
        elif momentum < -0.05:  # 5% negative momentum
            return "SELL"
        else:
            return "HOLD"

class RSIStrategy(TradingStrategy):
    def __init__(self, period=14, overbought=70, oversold=30):
        super().__init__("RSI Strategy", f"RSI({period}) with overbought={overbought}, oversold={oversold}")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def calculate_rsi(self, data):
        """Calculate RSI indicator"""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signal(self, data):
        if len(data) < self.period:
            return "HOLD"

        rsi = self.calculate_rsi(data)
        current_rsi = rsi.iloc[-1]

        if current_rsi < self.oversold:
            return "BUY"
        elif current_rsi > self.overbought:
            return "SELL"
        else:
            return "HOLD"

class MovingAverageStrategy(TradingStrategy):
    def __init__(self, short_period=20, long_period=50):
        super().__init__("Moving Average Crossover",
                        f"MA({short_period}) vs MA({long_period}) crossover strategy")
        self.short_period = short_period
        self.long_period = long_period

    def generate_signal(self, data):
        if len(data) < self.long_period:
            return "HOLD"

        short_ma = data['Close'].rolling(window=self.short_period).mean()
        long_ma = data['Close'].rolling(window=self.long_period).mean()

        # Check for crossover
        if short_ma.iloc[-2] <= long_ma.iloc[-2] and short_ma.iloc[-1] > long_ma.iloc[-1]:
            return "BUY"
        elif short_ma.iloc[-2] >= long_ma.iloc[-2] and short_ma.iloc[-1] < long_ma.iloc[-1]:
            return "SELL"
        else:
            return "HOLD"

class BollingerBandsStrategy(TradingStrategy):
    def __init__(self, period=20, std_dev=2):
        super().__init__("Bollinger Bands",
                        f"Bollinger Bands ({period} periods, {std_dev} std dev)")
        self.period = period
        self.std_dev = std_dev

    def generate_signal(self, data):
        if len(data) < self.period:
            return "HOLD"

        ma = data['Close'].rolling(window=self.period).mean()
        std = data['Close'].rolling(window=self.period).std()
        upper_band = ma + (std * self.std_dev)
        lower_band = ma - (std * self.std_dev)

        current_price = data['Close'].iloc[-1]

        if current_price <= lower_band.iloc[-1]:
            return "BUY"
        elif current_price >= upper_band.iloc[-1]:
            return "SELL"
        else:
            return "HOLD"

# Portfolio and Risk Management
class PortfolioManager:
    def __init__(self, initial_balance=10000):
        self.balance = initial_balance
        self.positions = {}
        self.trade_history = []
        self.performance_history = []

    def can_afford_position(self, price, quantity, max_position_pct=0.1):
        """Check if we can afford a position"""
        position_value = price * quantity
        max_position_value = self.balance * max_position_pct
        return position_value <= max_position_value

    def calculate_position_size(self, price, stop_loss_pct=0.02):
        """Calculate position size based on risk tolerance"""
        risk_per_share = price * stop_loss_pct
        max_risk_per_trade = self.balance * 0.01  # 1% risk per trade
        position_size = max_risk_per_trade / risk_per_share
        return int(position_size)

    def execute_trade(self, symbol, signal, price, quantity):
        """Execute a trade"""
        if signal == "BUY":
            cost = price * quantity
            if cost <= self.balance:
                self.balance -= cost
                self.positions[symbol] = {
                    'quantity': quantity,
                    'avg_price': price,
                    'entry_date': datetime.now()
                }
                self.trade_history.append({
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'type': 'BUY',
                    'price': price,
                    'quantity': quantity,
                    'value': cost
                })
                return True
        elif signal == "SELL" and symbol in self.positions:
            revenue = price * self.positions[symbol]['quantity']
            self.balance += revenue
            profit = revenue - (self.positions[symbol]['avg_price'] * self.positions[symbol]['quantity'])
            del self.positions[symbol]

            self.trade_history.append({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'type': 'SELL',
                'price': price,
                'quantity': quantity,
                'value': revenue,
                'profit': profit
            })
            return True

        return False

# Order Management System
class OrderManager:
    def __init__(self, api_key=None, api_secret=None, base_url="https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.api = None
        self.active_orders = {}
        self.order_history = []

        if ALPACA_AVAILABLE and api_key and api_secret:
            try:
                self.api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
                st.success("✅ Alpaca API Connected Successfully!")
            except Exception as e:
                st.error(f"❌ Failed to connect to Alpaca API: {str(e)}")
        elif ALPACA_AVAILABLE:
            st.info("ℹ️ Alpaca API available but credentials not configured. Using simulation mode.")

    def submit_order(self, symbol, qty, side, order_type=OrderType.MARKET, limit_price=None, stop_price=None, time_in_force='day'):
        """Submit an order to Alpaca"""
        if not self.api:
            # Simulation mode
            order_id = f"sim_{symbol}_{side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            order = {
                'id': order_id,
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': order_type,
                'status': 'filled',  # Simulate immediate fill
                'filled_qty': qty,
                'filled_avg_price': 150.0,  # Mock price
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            self.active_orders[order_id] = order
            self.order_history.append(order)
            return order

        try:
            order_params = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': order_type,
                'time_in_force': time_in_force
            }

            if limit_price:
                order_params['limit_price'] = limit_price
            if stop_price:
                order_params['stop_price'] = stop_price

            order = self.api.submit_order(**order_params)
            self.active_orders[order.id] = order
            return order

        except Exception as e:
            st.error(f"❌ Order submission failed: {str(e)}")
            return None

    def submit_bracket_order(self, symbol, qty, side, take_profit_price, stop_loss_price, limit_price=None):
        """Submit a bracket order (entry + take profit + stop loss)"""
        if not self.api:
            st.warning("⚠️ Bracket orders not available in simulation mode")
            return None

        try:
            # Submit main order
            main_order = self.submit_order(symbol, qty, side, OrderType.LIMIT if limit_price else OrderType.MARKET, limit_price)

            if main_order and main_order.status == 'filled':
                # Submit take profit order
                tp_order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY,
                    type=OrderType.LIMIT,
                    limit_price=take_profit_price,
                    time_in_force='gtc'
                )

                # Submit stop loss order
                sl_order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY,
                    type=OrderType.STOP,
                    stop_price=stop_loss_price,
                    time_in_force='gtc'
                )

                return {'main': main_order, 'take_profit': tp_order, 'stop_loss': sl_order}

        except Exception as e:
            st.error(f"❌ Bracket order submission failed: {str(e)}")
            return None

    def get_account_info(self):
        """Get account information"""
        if not self.api:
            return {
                'cash': '10000.00',
                'portfolio_value': '10000.00',
                'buying_power': '20000.00',
                'status': 'SIMULATION'
            }

        try:
            account = self.api.get_account()
            return {
                'cash': account.cash,
                'portfolio_value': account.portfolio_value,
                'buying_power': account.buying_power,
                'status': 'LIVE'
            }
        except Exception as e:
            st.error(f"❌ Failed to get account info: {str(e)}")
            return None

    def get_positions(self):
        """Get current positions"""
        if not self.api:
            return []

        try:
            positions = self.api.list_positions()
            return positions
        except Exception as e:
            st.error(f"❌ Failed to get positions: {str(e)}")
            return []

    def cancel_order(self, order_id):
        """Cancel an order"""
        if not self.api:
            if order_id in self.active_orders:
                self.active_orders[order_id]['status'] = 'cancelled'
                return True
            return False

        try:
            self.api.cancel_order(order_id)
            return True
        except Exception as e:
            st.error(f"❌ Failed to cancel order: {str(e)}")
            return False

# Enhanced Trading System with Live Trading
class EnhancedTradingSystem(TradingSystem):
    def __init__(self, alpaca_api_key=None, alpaca_api_secret=None):
        super().__init__()
        self.order_manager = OrderManager(alpaca_api_key, alpaca_api_secret)
        self.live_mode = ALPACA_AVAILABLE and alpaca_api_key and alpaca_api_secret

    def execute_live_trade(self, symbol, signal, quantity, take_profit_pct=0.05, stop_loss_pct=0.02):
        """Execute a live trade with risk management"""
        if signal == "BUY":
            # Get current price for bracket order
            try:
                stock = yf.Ticker(symbol)
                current_price = stock.history(period='1d')['Close'].iloc[-1]

                # Calculate take profit and stop loss prices
                take_profit_price = current_price * (1 + take_profit_pct)
                stop_loss_price = current_price * (1 - stop_loss_pct)

                # Submit bracket order
                bracket_order = self.order_manager.submit_bracket_order(
                    symbol=symbol,
                    qty=quantity,
                    side=OrderSide.BUY,
                    take_profit_price=take_profit_price,
                    stop_loss_price=stop_loss_price
                )

                if bracket_order:
                    st.success(f"✅ Bracket order placed for {symbol}: TP @ ${take_profit_price".2f"}, SL @ ${stop_loss_price".2f"}")
                    return bracket_order
                else:
                    st.error("❌ Failed to place bracket order")
                    return None

            except Exception as e:
                st.error(f"❌ Error executing trade: {str(e)}")
                return None

        elif signal == "SELL":
            # For sell orders, just submit a market order
            order = self.order_manager.submit_order(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET
            )

            if order:
                st.success(f"✅ Sell order placed for {symbol}")
                return order
            else:
                st.error("❌ Failed to place sell order")
                return None

    def get_real_time_quote(self, symbol):
        """Get real-time quote using Yahoo Finance"""
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period='1d', interval='1m')  # 1-minute intervals for near real-time
            return data['Close'].iloc[-1] if not data.empty else None
        except Exception as e:
            st.error(f"❌ Error getting real-time quote: {str(e)}")
            return None

    def monitor_live_signals(self, symbols, interval_minutes=5):
        """Monitor multiple symbols for live trading signals"""
        signals_data = {}

        for symbol in symbols:
            try:
                # Get latest data
                data = self.get_stock_data(symbol, '3mo')

                if data is not None:
                    signal = self.signal_manager.generate_combined_signal(symbol, data)
                    current_price = data['Close'].iloc[-1]

                    signals_data[symbol] = {
                        'signal': signal,
                        'price': current_price,
                        'timestamp': datetime.now(),
                        'indicators': {
                            'RSI': self.calculate_rsi(data['Close']).iloc[-1],
                            'SMA_20': data['SMA_20'].iloc[-1],
                            'SMA_50': data['SMA_50'].iloc[-1]
                        }
                    }
            except Exception as e:
                st.error(f"❌ Error monitoring {symbol}: {str(e)}")

        return signals_data

# Live Market Data Feed
class LiveDataFeed:
    def __init__(self, symbols=['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']):
        self.symbols = symbols
        self.market_hours = {
            'start': '09:30',
            'end': '16:00'
        }
        self.price_data = {}

    def is_market_open(self):
        """Check if US stock market is currently open"""
        now = datetime.now().time()
        market_start = datetime.strptime(self.market_hours['start'], '%H:%M').time()
        market_end = datetime.strptime(self.market_hours['end'], '%H:%M').time()

        # Check if it's a weekday
        if datetime.now().weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        return market_start <= now <= market_end

    def get_latest_prices(self):
        """Get latest prices for all symbols"""
        prices = {}

        for symbol in self.symbols:
            try:
                stock = yf.Ticker(symbol)
                data = stock.history(period='1d', interval='5m')  # 5-minute intervals
                if not data.empty:
                    prices[symbol] = {
                        'price': data['Close'].iloc[-1],
                        'change': (data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100,
                        'volume': data['Volume'].iloc[-1]
                    }
            except Exception as e:
                st.error(f"❌ Error fetching price for {symbol}: {str(e)}")

        return prices

    def get_market_status(self):
        """Get current market status"""
        if self.is_market_open():
            return "🟢 OPEN", "Market is currently open"
        else:
            return "🔴 CLOSED", "Market is currently closed"

# Signal Manager
class SignalManager:
    def __init__(self):
        self.strategies = []
        self.signals = {}

    def add_strategy(self, strategy):
        self.strategies.append(strategy)

    def generate_combined_signal(self, symbol, data):
        """Generate combined signal from all strategies"""
        signals = []
        for strategy in self.strategies:
            signal = strategy.generate_signal(data)
            signals.append(signal)

        # Simple majority voting
        buy_votes = signals.count("BUY")
        sell_votes = signals.count("SELL")
        hold_votes = signals.count("HOLD")

        if buy_votes > sell_votes and buy_votes > hold_votes:
            return "BUY"
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            return "SELL"
        else:
            return "HOLD"

# Main Trading System
class TradingSystem:
    def __init__(self):
        self.signal_manager = SignalManager()
        self.portfolio = PortfolioManager()

        # Initialize strategies
        self.signal_manager.add_strategy(MomentumStrategy())
        self.signal_manager.add_strategy(RSIStrategy())
        self.signal_manager.add_strategy(MovingAverageStrategy())
        self.signal_manager.add_strategy(BollingerBandsStrategy())

    def get_stock_data(self, symbol, period='1mo'):
        """Get stock data with indicators"""
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)

        if data.empty:
            return None

        # Add basic indicators
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
        data['RSI'] = self.calculate_rsi(data['Close'])

        return data

    def calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def analyze_stock(self, symbol, period='1mo'):
        """Analyze stock and generate trading signal"""
        data = self.get_stock_data(symbol, period)

        if data is None or len(data) < 50:
            return None, "Insufficient data"

        signal = self.signal_manager.generate_combined_signal(symbol, data)

        # Get current price
        current_price = data['Close'].iloc[-1]

        # Calculate position size
        quantity = self.portfolio.calculate_position_size(current_price)

        return {
            'symbol': symbol,
            'signal': signal,
            'current_price': current_price,
            'suggested_quantity': quantity,
            'indicators': {
                'SMA_20': data['SMA_20'].iloc[-1],
                'SMA_50': data['SMA_50'].iloc[-1],
                'RSI': data['RSI'].iloc[-1],
                'momentum': (data['Close'].iloc[-1] - data['Close'].iloc[-20]) / data['Close'].iloc[-20]
            },
            'data': data
        }, signal

    def plot_analysis(self, analysis_result):
        """Create comprehensive analysis plot"""
        data = analysis_result['data']

        # Create subplots
        fig = make_subplots(
            rows=4, cols=1,
            subplot_titles=('Price & Moving Averages', 'RSI', 'Volume', 'Momentum'),
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.4, 0.2, 0.2, 0.2]
        )

        # Price and MAs
        fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Close Price',
                                line=dict(color='blue')), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'], name='SMA 20',
                                line=dict(color='orange', dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA_50'], name='SMA 50',
                                line=dict(color='red', dash='dash')), row=1, col=1)

        # RSI
        rsi_data = self.calculate_rsi(data['Close'])
        fig.add_trace(go.Scatter(x=data.index, y=rsi_data, name='RSI',
                                line=dict(color='purple')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1, annotation_text="Overbought")
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1, annotation_text="Oversold")

        # Volume
        fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume',
                            marker_color='lightblue'), row=3, col=1)

        # Momentum
        momentum = data['Close'].pct_change(14)
        fig.add_trace(go.Scatter(x=data.index, y=momentum, name='Momentum',
                                line=dict(color='green')), row=4, col=1)

        # Add buy/sell signals
        buy_signals = data[analysis_result['signal'] == 'BUY']
        sell_signals = data[analysis_result['signal'] == 'SELL']

        if not buy_signals.empty:
            fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'],
                                   mode='markers', name='Buy Signal',
                                   marker=dict(color='green', symbol='triangle-up', size=10)),
                         row=1, col=1)

        if not sell_signals.empty:
            fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'],
                                   mode='markers', name='Sell Signal',
                                   marker=dict(color='red', symbol='triangle-down', size=10)),
                         row=1, col=1)

        fig.update_layout(
            title=f'Trading Analysis for {analysis_result["symbol"]}',
            xaxis_title='Date',
            height=1000
        )

        return fig

def main():
    st.set_page_config(page_title="Advanced Trading Algorithm", page_icon="📈", layout="wide")

    st.title('🚀 Advanced Algorithmic Trading System')
    st.markdown("**Multi-Strategy Trading with Live Signal Generation & Real Order Execution**")

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API Configuration
        st.subheader("🔑 API Configuration")
        alpaca_api_key = st.text_input("Alpaca API Key", type="password",
                                      help="Get your API keys from https://alpaca.markets/")
        alpaca_api_secret = st.text_input("Alpaca API Secret", type="password",
                                         help="Your Alpaca API secret key")
        use_paper_trading = st.checkbox("Use Paper Trading", value=True,
                                      help="Use Alpaca's paper trading environment for testing")

        # Trading Settings
        st.subheader("💰 Trading Settings")
        initial_balance = st.number_input("Initial Balance ($)", value=10000, min_value=1000, step=1000)
        max_position_pct = st.slider("Max Position Size (%)", 0.01, 0.25, 0.10, 0.01)
        risk_per_trade = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0, 0.5)

        # Risk Management
        st.subheader("🛡️ Risk Management")
        stop_loss_pct = st.slider("Stop Loss (%)", 1.0, 10.0, 2.0, 0.5)
        take_profit_pct = st.slider("Take Profit (%)", 1.0, 20.0, 5.0, 0.5)
        enable_bracket_orders = st.checkbox("Enable Bracket Orders", value=True,
                                          help="Automatically place Stop Loss and Take Profit orders")

        # Strategy Settings
        st.subheader("📊 Strategy Parameters")
        rsi_period = st.slider("RSI Period", 10, 20, 14, 1)
        rsi_overbought = st.slider("RSI Overbought Level", 60, 80, 70, 1)
        rsi_oversold = st.slider("RSI Oversold Level", 20, 40, 30, 1)

        ma_short = st.slider("Short MA Period", 10, 30, 20, 1)
        ma_long = st.slider("Long MA Period", 30, 100, 50, 5)

        # Analysis Settings
        st.subheader("🔍 Analysis Settings")
        analysis_period = st.selectbox("Analysis Period", ['1mo', '3mo', '6mo', '1y'], index=1)
        auto_refresh = st.checkbox("Auto-refresh (every 30s)", value=False)

        # Live Trading Controls
        st.subheader("🎯 Live Trading")
        live_trading_enabled = st.checkbox("Enable Live Trading", value=False,
                                         help="Execute real trades with Alpaca")
        if live_trading_enabled and not (alpaca_api_key and alpaca_api_secret):
            st.error("❌ Please configure Alpaca API credentials to enable live trading")
            live_trading_enabled = False

        # Live Market Data
        st.subheader("📊 Live Market Data")
        live_data_enabled = st.checkbox("Enable Live Market Feed", value=True)

        # Portfolio Status
        st.subheader("💼 Portfolio Status")
        portfolio_placeholder = st.empty()

    # Initialize trading system
    if 'trading_system' not in st.session_state:
        base_url = "https://paper-api.alpaca.markets" if use_paper_trading else "https://api.alpaca.markets"
        st.session_state.trading_system = EnhancedTradingSystem(alpaca_api_key, alpaca_api_secret)
        st.session_state.trading_system.portfolio.balance = initial_balance
        st.session_state.trading_system.order_manager.base_url = base_url

        # Initialize live data feed
        st.session_state.live_data_feed = LiveDataFeed()

        # Store configuration
        st.session_state.config = {
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'enable_bracket_orders': enable_bracket_orders,
            'live_trading_enabled': live_trading_enabled,
            'live_data_enabled': live_data_enabled
        }

    # Update strategy parameters
    st.session_state.trading_system.signal_manager.strategies[1] = RSIStrategy(rsi_period, rsi_overbought, rsi_oversold)
    st.session_state.trading_system.signal_manager.strategies[2] = MovingAverageStrategy(ma_short, ma_long)

    # Update configuration
    st.session_state.config.update({
        'stop_loss_pct': stop_loss_pct,
        'take_profit_pct': take_profit_pct,
        'enable_bracket_orders': enable_bracket_orders,
        'live_trading_enabled': live_trading_enabled,
        'live_data_enabled': live_data_enabled
    })

    # Live Market Dashboard (if enabled)
    if st.session_state.config['live_data_enabled']:
        st.header("📈 Live Market Dashboard")

        # Market Status
        status, status_msg = st.session_state.live_data_feed.get_market_status()
        st.write(f"**Market Status:** {status} - {status_msg}")

        # Live Prices
        with st.spinner("Fetching live market data..."):
            live_prices = st.session_state.live_data_feed.get_latest_prices()

        if live_prices:
            # Display live prices in a grid
            cols = st.columns(min(len(live_prices), 5))

            for i, (symbol, data) in enumerate(live_prices.items()):
                if i < len(cols):
                    with cols[i]:
                        st.metric(
                            label=symbol,
                            value=f"${data['price']".2f"}",
                            delta=f"{data['change']".2f"}%"
                        )
                        st.caption(f"Volume: {data['volume']","}")

            # Live Signal Monitor
            with st.expander("🔄 Live Signal Monitor"):
                st.subheader("Real-time Trading Signals")

                # Monitor signals for live symbols
                live_signals = st.session_state.trading_system.monitor_live_signals(list(live_prices.keys()))

                if live_signals:
                    for symbol, signal_data in live_signals.items():
                        cols = st.columns([2, 1, 1, 1])
                        cols[0].write(f"**{symbol}**")
                        cols[1].write(f"${signal_data['price']".2f"}")

                        if signal_data['signal'] == 'BUY':
                            cols[2].success("🟢 BUY")
                        elif signal_data['signal'] == 'SELL':
                            cols[3].error("🔴 SELL")
                        else:
                            cols[2].info("🟡 HOLD")

                        # Quick indicators
                        with cols[3]:
                            st.caption(f"RSI: {signal_data['indicators']['RSI']".1f"}")

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📊 Stock Analysis")

        # Stock selection
        stock_ticker = st.text_input('Enter a stock ticker (e.g., AAPL, TSLA, MSFT)', 'AAPL')

        if stock_ticker:
            try:
                with st.spinner(f'Analyzing {stock_ticker}...'):
                    analysis_result, signal = st.session_state.trading_system.analyze_stock(stock_ticker, analysis_period)

                if analysis_result:
                    # Display analysis results
                    st.success(f"**Signal: {signal}** for {stock_ticker}")

                    # Signal strength indicators
                    indicators = analysis_result['indicators']
                    cols = st.columns(4)
                    cols[0].metric("Current Price", f"${analysis_result['current_price']".2f"}")
                    cols[1].metric("RSI", f"{indicators['RSI']".1f"}")
                    cols[2].metric("20-day Momentum", f"{indicators['momentum']".2%"}")
                    cols[3].metric("Suggested Quantity", analysis_result['suggested_quantity'])

                    # Plot
                    fig = st.session_state.trading_system.plot_analysis(analysis_result)
                    st.plotly_chart(fig, use_container_width=True)

                    # Strategy breakdown
                    with st.expander("🔍 Strategy Breakdown"):
                        st.subheader("Individual Strategy Signals")
                        strategies = st.session_state.trading_system.signal_manager.strategies

                        for i, strategy in enumerate(strategies):
                            individual_signal = strategy.generate_signal(analysis_result['data'])
                            st.write(f"**{strategy.name}:** {individual_signal}")

                    # Live Trading Actions
                    if st.session_state.config['live_trading_enabled']:
                        st.subheader("🎯 Execute Trade")

                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            execute_buy = st.button(f"🚀 BUY {analysis_result['suggested_quantity']} shares",
                                                  type="primary", disabled=(signal != "BUY"))

                        with col_b:
                            execute_sell = st.button(f"💰 SELL {analysis_result['suggested_quantity']} shares",
                                                   type="secondary", disabled=(signal != "SELL"))

                        with col_c:
                            quantity_override = st.number_input("Override Quantity",
                                                              min_value=1,
                                                              value=analysis_result['suggested_quantity'],
                                                              step=1)

                        if execute_buy:
                            with st.spinner("Executing BUY order..."):
                                order = st.session_state.trading_system.execute_live_trade(
                                    symbol=stock_ticker,
                                    signal="BUY",
                                    quantity=quantity_override,
                                    take_profit_pct=st.session_state.config['take_profit_pct'] / 100,
                                    stop_loss_pct=st.session_state.config['stop_loss_pct'] / 100
                                )

                                if order:
                                    st.success(f"✅ BUY order executed successfully!")
                                    st.rerun()

                        elif execute_sell:
                            with st.spinner("Executing SELL order..."):
                                order = st.session_state.trading_system.execute_live_trade(
                                    symbol=stock_ticker,
                                    signal="SELL",
                                    quantity=quantity_override
                                )

                                if order:
                                    st.success(f"✅ SELL order executed successfully!")
                                    st.rerun()

                    # Quick Analysis Summary
                    with st.expander("📈 Quick Analysis"):
                        st.write("**Signal Strength:**")
                        indicators = analysis_result['indicators']

                        # RSI Signal
                        if indicators['RSI'] < 30:
                            st.success("🟢 RSI: Oversold (Strong Buy)")
                        elif indicators['RSI'] > 70:
                            st.error("🔴 RSI: Overbought (Strong Sell)")
                        else:
                            st.info("🟡 RSI: Neutral")

                        # Momentum Signal
                        if indicators['momentum'] > 0.05:
                            st.success(f"🟢 Momentum: Strong (+{indicators['momentum']".2%"})")
                        elif indicators['momentum'] < -0.05:
                            st.error(f"🔴 Momentum: Weak ({indicators['momentum']".2%"})")
                        else:
                            st.info(f"🟡 Momentum: Neutral ({indicators['momentum']".2%"})")

                        # MA Signal
                        if indicators['SMA_20'] > indicators['SMA_50']:
                            st.success("🟢 Moving Averages: Bullish (20 > 50)")
                        else:
                            st.error("🔴 Moving Averages: Bearish (20 < 50)")

                else:
                    st.error("Unable to analyze stock. Please check the ticker symbol.")

            except Exception as e:
                st.error(f'Error analyzing {stock_ticker}: {str(e)}')

    with col2:
        st.header("📈 Portfolio & Performance")

        # Account Information
        if st.session_state.config['live_trading_enabled']:
            st.subheader("🏦 Account Status")
            account_info = st.session_state.trading_system.order_manager.get_account_info()

            if account_info:
                cols = st.columns(2)
                cols[0].metric("Account Status", account_info['status'])
                cols[1].metric("Cash Balance", f"${float(account_info['cash'])",.2f"}")

                st.metric("Portfolio Value", f"${float(account_info['portfolio_value'])",.2f"}")
                st.metric("Buying Power", f"${float(account_info['buying_power'])",.2f"}")

            # Active Orders
            st.subheader("📋 Active Orders")
            active_orders = st.session_state.trading_system.order_manager.active_orders

            if active_orders:
                for order_id, order in active_orders.items():
                    with st.expander(f"Order {order_id[:8]}... - {order['symbol']}"):
                        cols = st.columns(4)
                        cols[0].write(f"**Type:** {order['side']} {order['type']}")
                        cols[1].write(f"**Quantity:** {order['qty']}")
                        cols[2].write(f"**Status:** {order['status']}")
                        cols[3].write(f"**Price:** ${order.get('filled_avg_price', 'N/A')}")

                        if st.button(f"❌ Cancel Order", key=f"cancel_{order_id}"):
                            if st.session_state.trading_system.order_manager.cancel_order(order_id):
                                st.success("✅ Order cancelled successfully!")
                                st.rerun()
            else:
                st.info("ℹ️ No active orders")

            # Current Positions (from Alpaca)
            st.subheader("📊 Current Positions")
            positions = st.session_state.trading_system.order_manager.get_positions()

            if positions:
                for position in positions:
                    cols = st.columns(4)
                    cols[0].write(f"**{position.symbol}**")
                    cols[1].write(f"{position.qty} shares")
                    cols[2].write(f"${float(position.avg_entry_price)",".2f"}")
                    cols[3].write(f"${float(position.unrealized_pl)",".2f"}")
            else:
                st.info("ℹ️ No current positions")

        # Simulation Portfolio (fallback)
        portfolio = st.session_state.trading_system.portfolio

        if not st.session_state.config['live_trading_enabled'] or not st.session_state.trading_system.live_mode:
            st.subheader("💼 Simulated Portfolio")

            # Current positions
            if portfolio.positions:
                st.subheader("Current Positions")
                for symbol, position in portfolio.positions.items():
                    cols = st.columns([2, 1, 1])
                    cols[0].write(f"**{symbol}**")
                    cols[1].write(f"{position['quantity']} shares")
                    cols[2].write(f"${position['avg_price']".2f"}")

            # Trade history
            if portfolio.trade_history:
                st.subheader("Recent Trades")
                recent_trades = portfolio.trade_history[-5:]  # Last 5 trades
                for trade in reversed(recent_trades):
                    if trade['type'] == 'BUY':
                        st.success(f"BUY {trade['symbol']} @ ${trade['price']".2f"}")
                    else:
                        profit_color = "🟢" if trade['profit'] > 0 else "🔴"
                        st.error(f"SELL {trade['symbol']} @ ${trade['price']".2f"} {profit_color} ${trade['profit']".2f"}")

            # Portfolio metrics
            st.subheader("Portfolio Metrics")
            cols = st.columns(3)
            cols[0].metric("Current Balance", f"${portfolio.balance",.2f"}")
            cols[1].metric("Total Trades", len(portfolio.trade_history))

            if portfolio.trade_history:
                profits = [trade['profit'] for trade in portfolio.trade_history if 'profit' in trade]
                if profits:
                    total_profit = sum(profits)
                    win_rate = len([p for p in profits if p > 0]) / len(profits) * 100
                    cols[2].metric("Total P&L", f"${total_profit",.2f"}", delta=f"${total_profit",.2f"}")
                    st.metric("Win Rate", f"{win_rate".1f"}%")

        # Performance Chart
        if portfolio.trade_history:
            with st.expander("📈 Performance Chart"):
                st.subheader("Trade Performance Over Time")

                # Create performance chart
                trade_df = pd.DataFrame(portfolio.trade_history)
                if not trade_df.empty and 'timestamp' in trade_df.columns:
                    trade_df['cumulative_pnl'] = trade_df['profit'].cumsum()

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=trade_df['timestamp'],
                        y=trade_df['cumulative_pnl'],
                        mode='lines+markers',
                        name='Cumulative P&L',
                        line=dict(color='blue')
                    ))

                    fig.update_layout(
                        title='Trading Performance',
                        xaxis_title='Date',
                        yaxis_title='Cumulative Profit/Loss ($)',
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # Auto-refresh functionality
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == '__main__':
    main()

