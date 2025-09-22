"""
Web Dashboard for Trading Algorithm Monitoring
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import json
import time
from advanced_trading_algo import TradingConfig, StrategyEngine, AlpacaTrader, TradingBot
from backtesting import Backtester, run_strategy_comparison

# Page configuration
st.set_page_config(
    page_title="Advanced Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .signal-card {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .buy-signal {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
    }
    .sell-signal {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
    }
    .hold-signal {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

class Dashboard:
    def __init__(self):
        self.config = TradingConfig()
        self.strategy_engine = StrategyEngine(self.config)
        self.trader = AlpacaTrader(self.config)
        
    def load_market_data(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Load market data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            return data
        except Exception as e:
            st.error(f"Error loading data for {symbol}: {e}")
            return pd.DataFrame()
    
    def display_portfolio_overview(self):
        """Display portfolio overview"""
        st.subheader("📊 Portfolio Overview")
        
        try:
            # Get portfolio data
            portfolio_value = self.trader.get_portfolio_value()
            buying_power = self.trader.get_buying_power()
            positions = self.trader.get_positions()
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Portfolio Value", f"${portfolio_value:,.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Buying Power", f"${buying_power:,.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Active Positions", len(positions))
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col4:
                utilization = (portfolio_value - buying_power) / portfolio_value if portfolio_value > 0 else 0
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Capital Utilization", f"{utilization:.1%}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Display positions
            if positions:
                st.subheader("Current Positions")
                positions_data = []
                for pos in positions:
                    positions_data.append({
                        'Symbol': pos.symbol,
                        'Shares': int(pos.qty),
                        'Market Value': f"${float(pos.market_value):,.2f}",
                        'Unrealized P&L': f"${float(pos.unrealized_pl):,.2f}",
                        'P&L %': f"{float(pos.unrealized_plpc):.2%}"
                    })
                
                df_positions = pd.DataFrame(positions_data)
                st.dataframe(df_positions, use_container_width=True)
        
        except Exception as e:
            st.error(f"Error loading portfolio data: {e}")
            st.info("Make sure your Alpaca API credentials are configured correctly.")
    
    def display_live_signals(self):
        """Display live trading signals"""
        st.subheader("🎯 Live Trading Signals")
        
        symbols = self.config.get('trading.symbols', ['AAPL', 'GOOGL', 'MSFT'])
        
        for symbol in symbols:
            with st.expander(f"{symbol} Analysis", expanded=False):
                data = self.load_market_data(symbol, "3mo")
                if data.empty:
                    st.error(f"No data available for {symbol}")
                    continue
                
                # Generate signal
                signal = self.strategy_engine.generate_combined_signal(data, symbol)
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if signal:
                        signal_class = f"{signal.signal_type.value}-signal"
                        st.markdown(f'''
                        <div class="signal-card {signal_class}">
                            <h4>{signal.signal_type.value.upper()} Signal</h4>
                            <p><strong>Strategy:</strong> {signal.strategy}</p>
                            <p><strong>Confidence:</strong> {signal.confidence:.1%}</p>
                            <p><strong>Price:</strong> ${signal.price:.2f}</p>
                            {f"<p><strong>Stop Loss:</strong> ${signal.stop_loss:.2f}</p>" if signal.stop_loss else ""}
                            {f"<p><strong>Take Profit:</strong> ${signal.take_profit:.2f}</p>" if signal.take_profit else ""}
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.markdown('''
                        <div class="signal-card hold-signal">
                            <h4>HOLD</h4>
                            <p>No strong signal detected</p>
                        </div>
                        ''', unsafe_allow_html=True)
                
                with col2:
                    # Create price chart with indicators
                    self.plot_technical_analysis(data, symbol)
    
    def plot_technical_analysis(self, data: pd.DataFrame, symbol: str):
        """Plot technical analysis chart"""
        # Calculate indicators
        rsi = self.strategy_engine.ta.calculate_rsi(data)
        macd_data = self.strategy_engine.ta.calculate_macd(data)
        bb_data = self.strategy_engine.ta.calculate_bollinger_bands(data)
        ma_data = self.strategy_engine.ta.calculate_moving_averages(data)
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=[f'{symbol} Price & Indicators', 'RSI', 'MACD'],
            vertical_spacing=0.1,
            row_heights=[0.6, 0.2, 0.2]
        )
        
        # Price and Bollinger Bands
        fig.add_trace(
            go.Scatter(x=data.index, y=data['Close'], name='Close Price', line=dict(color='blue')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=bb_data['upper'], name='BB Upper', 
                      line=dict(color='red', dash='dash')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=bb_data['lower'], name='BB Lower', 
                      line=dict(color='red', dash='dash')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=ma_data['fast_ma'], name='Fast MA', 
                      line=dict(color='orange')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=ma_data['slow_ma'], name='Slow MA', 
                      line=dict(color='purple')),
            row=1, col=1
        )
        
        # RSI
        fig.add_trace(
            go.Scatter(x=data.index, y=rsi, name='RSI', line=dict(color='green')),
            row=2, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="red", row=2, col=1)
        
        # MACD
        fig.add_trace(
            go.Scatter(x=data.index, y=macd_data['macd'], name='MACD', 
                      line=dict(color='blue')),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=macd_data['signal'], name='Signal', 
                      line=dict(color='red')),
            row=3, col=1
        )
        
        fig.update_layout(height=600, showlegend=True)
        fig.update_xaxes(title_text="Date", row=3, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="RSI", row=2, col=1)
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def display_backtesting_results(self):
        """Display backtesting interface and results"""
        st.subheader("📈 Strategy Backtesting")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbols = st.multiselect(
                "Select Symbols",
                options=['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'SPY', 'QQQ'],
                default=['AAPL', 'GOOGL', 'MSFT']
            )
        
        with col2:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=365)
            )
        
        with col3:
            end_date = st.date_input(
                "End Date",
                value=datetime.now()
            )
        
        if st.button("Run Backtest", type="primary"):
            if symbols:
                with st.spinner("Running backtest..."):
                    backtester = Backtester(self.config)
                    result = backtester.run_backtest(
                        symbols, 
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d')
                    )
                
                # Display results
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Return", f"{result.total_return:.2%}")
                with col2:
                    st.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")
                with col3:
                    st.metric("Max Drawdown", f"{result.max_drawdown:.2%}")
                with col4:
                    st.metric("Win Rate", f"{result.win_rate:.2%}")
                
                # Portfolio value chart
                if result.portfolio_values:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=result.dates,
                        y=result.portfolio_values,
                        mode='lines',
                        name='Portfolio Value',
                        line=dict(color='blue')
                    ))
                    fig.update_layout(
                        title="Portfolio Value Over Time",
                        xaxis_title="Date",
                        yaxis_title="Portfolio Value ($)",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Trade history
                if result.trades:
                    st.subheader("Trade History")
                    trades_df = pd.DataFrame(result.trades)
                    if not trades_df.empty:
                        st.dataframe(trades_df, use_container_width=True)
            else:
                st.warning("Please select at least one symbol for backtesting.")
    
    def display_configuration(self):
        """Display and edit configuration"""
        st.subheader("⚙️ Configuration")
        
        # Trading parameters
        st.write("### Trading Parameters")
        col1, col2 = st.columns(2)
        
        with col1:
            max_position_size = st.slider(
                "Max Position Size (%)",
                min_value=1,
                max_value=50,
                value=int(self.config.get('trading.max_position_size', 0.1) * 100),
                help="Maximum percentage of portfolio to allocate per position"
            )
            
            stop_loss_pct = st.slider(
                "Stop Loss (%)",
                min_value=1,
                max_value=10,
                value=int(self.config.get('trading.stop_loss_pct', 0.02) * 100),
                help="Stop loss percentage"
            )
        
        with col2:
            take_profit_pct = st.slider(
                "Take Profit (%)",
                min_value=1,
                max_value=20,
                value=int(self.config.get('trading.take_profit_pct', 0.04) * 100),
                help="Take profit percentage"
            )
            
            min_confidence = st.slider(
                "Minimum Signal Confidence",
                min_value=0.1,
                max_value=1.0,
                value=self.config.get('trading.min_confidence', 0.6),
                step=0.1,
                help="Minimum confidence required to execute trades"
            )
        
        # Strategy weights
        st.write("### Strategy Configuration")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            rsi_enabled = st.checkbox("RSI Strategy", value=self.config.get('strategies.rsi.enabled', True))
            if rsi_enabled:
                rsi_weight = st.slider("RSI Weight", 0.0, 1.0, self.config.get('strategies.rsi.weight', 0.25))
        
        with col2:
            macd_enabled = st.checkbox("MACD Strategy", value=self.config.get('strategies.macd.enabled', True))
            if macd_enabled:
                macd_weight = st.slider("MACD Weight", 0.0, 1.0, self.config.get('strategies.macd.weight', 0.25))
        
        with col3:
            bb_enabled = st.checkbox("Bollinger Bands", value=self.config.get('strategies.bollinger.enabled', True))
            if bb_enabled:
                bb_weight = st.slider("Bollinger Weight", 0.0, 1.0, self.config.get('strategies.bollinger.weight', 0.25))
        
        with col4:
            ma_enabled = st.checkbox("MA Crossover", value=self.config.get('strategies.ma_crossover.enabled', True))
            if ma_enabled:
                ma_weight = st.slider("MA Weight", 0.0, 1.0, self.config.get('strategies.ma_crossover.weight', 0.25))
        
        if st.button("Save Configuration"):
            # Update configuration
            self.config.config['trading']['max_position_size'] = max_position_size / 100
            self.config.config['trading']['stop_loss_pct'] = stop_loss_pct / 100
            self.config.config['trading']['take_profit_pct'] = take_profit_pct / 100
            self.config.config['trading']['min_confidence'] = min_confidence
            
            self.config.config['strategies']['rsi']['enabled'] = rsi_enabled
            self.config.config['strategies']['macd']['enabled'] = macd_enabled
            self.config.config['strategies']['bollinger']['enabled'] = bb_enabled
            self.config.config['strategies']['ma_crossover']['enabled'] = ma_enabled
            
            if rsi_enabled:
                self.config.config['strategies']['rsi']['weight'] = rsi_weight
            if macd_enabled:
                self.config.config['strategies']['macd']['weight'] = macd_weight
            if bb_enabled:
                self.config.config['strategies']['bollinger']['weight'] = bb_weight
            if ma_enabled:
                self.config.config['strategies']['ma_crossover']['weight'] = ma_weight
            
            self.config.save_config()
            st.success("Configuration saved successfully!")

def main():
    """Main dashboard function"""
    st.markdown('<h1 class="main-header">🚀 Advanced Trading Dashboard</h1>', unsafe_allow_html=True)
    
    dashboard = Dashboard()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Portfolio Overview", "Live Signals", "Backtesting", "Configuration"]
    )
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)")
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Display selected page
    if page == "Portfolio Overview":
        dashboard.display_portfolio_overview()
    elif page == "Live Signals":
        dashboard.display_live_signals()
    elif page == "Backtesting":
        dashboard.display_backtesting_results()
    elif page == "Configuration":
        dashboard.display_configuration()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "Advanced Trading Algorithm Dashboard\n\n"
        "Features:\n"
        "- Multiple trading strategies\n"
        "- Live signal generation\n"
        "- Portfolio monitoring\n"
        "- Strategy backtesting\n"
        "- Risk management"
    )

if __name__ == "__main__":
    main()