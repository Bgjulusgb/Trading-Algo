"""
Advanced Risk Management Module
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
from advanced_trading_algo import TradingSignal, SignalType, TradingConfig

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskMetrics:
    portfolio_var: float  # Value at Risk
    expected_shortfall: float  # Conditional VaR
    max_drawdown: float
    sharpe_ratio: float
    beta: float
    correlation_risk: float
    concentration_risk: float
    volatility: float
    risk_level: RiskLevel

@dataclass
class PositionRisk:
    symbol: str
    position_size: float
    portfolio_weight: float
    var_contribution: float
    beta: float
    volatility: float
    correlation_with_portfolio: float
    risk_score: float

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self, config: TradingConfig, lookback_days: int = 252):
        self.config = config
        self.lookback_days = lookback_days
        self.market_data = {}
        self.portfolio_history = []
        self.risk_limits = {
            'max_portfolio_var': 0.05,  # 5% daily VaR limit
            'max_position_weight': 0.15,  # 15% max position size
            'max_sector_concentration': 0.30,  # 30% max sector exposure
            'max_correlation': 0.8,  # Max correlation between positions
            'min_sharpe_ratio': 0.5,  # Minimum acceptable Sharpe ratio
            'max_drawdown_limit': 0.20  # 20% max drawdown limit
        }
    
    def calculate_var(self, returns: pd.Series, confidence_level: float = 0.05) -> float:
        """Calculate Value at Risk using historical simulation"""
        if len(returns) == 0:
            return 0.0
        
        return np.percentile(returns, confidence_level * 100)
    
    def calculate_expected_shortfall(self, returns: pd.Series, confidence_level: float = 0.05) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if len(returns) == 0:
            return 0.0
        
        var = self.calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()
    
    def calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        if len(returns) == 0:
            return 0.0
        
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - peak) / peak
        return drawdown.min()
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_returns = returns.mean() - risk_free_rate / 252  # Daily risk-free rate
        return (excess_returns / returns.std()) * np.sqrt(252)
    
    def calculate_beta(self, asset_returns: pd.Series, market_returns: pd.Series) -> float:
        """Calculate beta relative to market"""
        if len(asset_returns) == 0 or len(market_returns) == 0:
            return 1.0
        
        # Align the series
        aligned_data = pd.concat([asset_returns, market_returns], axis=1).dropna()
        if len(aligned_data) < 30:  # Need sufficient data
            return 1.0
        
        covariance = aligned_data.iloc[:, 0].cov(aligned_data.iloc[:, 1])
        market_variance = aligned_data.iloc[:, 1].var()
        
        return covariance / market_variance if market_variance != 0 else 1.0
    
    def calculate_correlation_matrix(self, returns_dict: Dict[str, pd.Series]) -> pd.DataFrame:
        """Calculate correlation matrix for portfolio positions"""
        if not returns_dict:
            return pd.DataFrame()
        
        # Create DataFrame from returns
        returns_df = pd.DataFrame(returns_dict).dropna()
        
        if returns_df.empty:
            return pd.DataFrame()
        
        return returns_df.corr()
    
    def assess_concentration_risk(self, positions: Dict[str, float]) -> float:
        """Assess portfolio concentration risk using Herfindahl-Hirschman Index"""
        if not positions:
            return 0.0
        
        total_value = sum(abs(pos) for pos in positions.values())
        if total_value == 0:
            return 0.0
        
        weights = [abs(pos) / total_value for pos in positions.values()]
        hhi = sum(w**2 for w in weights)
        
        # Normalize HHI to 0-1 scale (1 = maximum concentration)
        n = len(positions)
        normalized_hhi = (hhi - 1/n) / (1 - 1/n) if n > 1 else 1.0
        
        return normalized_hhi
    
    def calculate_portfolio_var(self, positions: Dict[str, float], 
                              returns_dict: Dict[str, pd.Series],
                              confidence_level: float = 0.05) -> float:
        """Calculate portfolio VaR using Monte Carlo simulation"""
        if not positions or not returns_dict:
            return 0.0
        
        # Align returns data
        returns_df = pd.DataFrame(returns_dict).dropna()
        if returns_df.empty or len(returns_df) < 30:
            return 0.0
        
        # Calculate portfolio weights
        total_value = sum(abs(pos) for pos in positions.values())
        if total_value == 0:
            return 0.0
        
        weights = np.array([positions.get(symbol, 0) / total_value 
                           for symbol in returns_df.columns])
        
        # Calculate portfolio returns
        portfolio_returns = (returns_df * weights).sum(axis=1)
        
        return self.calculate_var(portfolio_returns, confidence_level)
    
    def evaluate_position_risk(self, symbol: str, position_size: float,
                             current_positions: Dict[str, float],
                             returns_dict: Dict[str, pd.Series]) -> PositionRisk:
        """Evaluate risk metrics for a specific position"""
        
        # Calculate portfolio weight
        total_portfolio_value = sum(abs(pos) for pos in current_positions.values()) + abs(position_size)
        portfolio_weight = abs(position_size) / total_portfolio_value if total_portfolio_value > 0 else 0
        
        # Get asset returns
        asset_returns = returns_dict.get(symbol, pd.Series())
        
        # Calculate volatility
        volatility = asset_returns.std() * np.sqrt(252) if len(asset_returns) > 0 else 0.0
        
        # Calculate beta (using SPY as market proxy if available)
        market_returns = returns_dict.get('SPY', pd.Series())
        beta = self.calculate_beta(asset_returns, market_returns) if len(market_returns) > 0 else 1.0
        
        # Calculate correlation with existing portfolio
        if len(current_positions) > 1:
            portfolio_returns = pd.Series()
            for pos_symbol, pos_size in current_positions.items():
                if pos_symbol != symbol and pos_symbol in returns_dict:
                    pos_weight = abs(pos_size) / sum(abs(p) for p in current_positions.values())
                    pos_returns = returns_dict[pos_symbol] * pos_weight
                    if portfolio_returns.empty:
                        portfolio_returns = pos_returns
                    else:
                        portfolio_returns += pos_returns
            
            correlation = asset_returns.corr(portfolio_returns) if len(portfolio_returns) > 0 else 0.0
        else:
            correlation = 0.0
        
        # Calculate VaR contribution
        var_contribution = portfolio_weight * volatility * 0.05  # Simplified VaR contribution
        
        # Calculate risk score (0-100)
        risk_score = min(100, (
            portfolio_weight * 30 +  # Position size risk
            volatility * 25 +        # Volatility risk
            abs(beta - 1) * 20 +     # Beta risk
            abs(correlation) * 25    # Correlation risk
        ))
        
        return PositionRisk(
            symbol=symbol,
            position_size=position_size,
            portfolio_weight=portfolio_weight,
            var_contribution=var_contribution,
            beta=beta,
            volatility=volatility,
            correlation_with_portfolio=correlation,
            risk_score=risk_score
        )
    
    def assess_signal_risk(self, signal: TradingSignal, 
                          current_positions: Dict[str, float],
                          returns_dict: Dict[str, pd.Series]) -> Tuple[bool, str, float]:
        """Assess risk of executing a trading signal"""
        
        # Calculate proposed position size
        portfolio_value = sum(abs(pos) for pos in current_positions.values())
        max_position_value = portfolio_value * self.config.get('trading.max_position_size', 0.1)
        proposed_position = max_position_value / signal.price if signal.price > 0 else 0
        
        if signal.signal_type == SignalType.SELL:
            proposed_position = -proposed_position
        
        # Evaluate position risk
        position_risk = self.evaluate_position_risk(
            signal.symbol, proposed_position, current_positions, returns_dict
        )
        
        # Check risk limits
        risk_violations = []
        
        # Position weight limit
        if position_risk.portfolio_weight > self.risk_limits['max_position_weight']:
            risk_violations.append(f"Position weight ({position_risk.portfolio_weight:.1%}) exceeds limit ({self.risk_limits['max_position_weight']:.1%})")
        
        # Volatility limit
        if position_risk.volatility > 0.5:  # 50% annual volatility limit
            risk_violations.append(f"Asset volatility ({position_risk.volatility:.1%}) too high")
        
        # Correlation limit
        if abs(position_risk.correlation_with_portfolio) > self.risk_limits['max_correlation']:
            risk_violations.append(f"Correlation ({position_risk.correlation_with_portfolio:.2f}) too high")
        
        # Calculate new portfolio VaR
        new_positions = current_positions.copy()
        new_positions[signal.symbol] = new_positions.get(signal.symbol, 0) + proposed_position
        
        new_portfolio_var = self.calculate_portfolio_var(new_positions, returns_dict)
        if abs(new_portfolio_var) > self.risk_limits['max_portfolio_var']:
            risk_violations.append(f"Portfolio VaR ({abs(new_portfolio_var):.1%}) exceeds limit ({self.risk_limits['max_portfolio_var']:.1%})")
        
        # Concentration risk
        concentration_risk = self.assess_concentration_risk(new_positions)
        if concentration_risk > 0.8:  # 80% concentration limit
            risk_violations.append(f"Portfolio concentration ({concentration_risk:.1%}) too high")
        
        # Decision
        if risk_violations:
            return False, "; ".join(risk_violations), position_risk.risk_score
        else:
            return True, "Risk acceptable", position_risk.risk_score
    
    def calculate_portfolio_metrics(self, positions: Dict[str, float],
                                  returns_dict: Dict[str, pd.Series],
                                  portfolio_returns: pd.Series) -> RiskMetrics:
        """Calculate comprehensive portfolio risk metrics"""
        
        # Portfolio VaR and Expected Shortfall
        portfolio_var = self.calculate_var(portfolio_returns)
        expected_shortfall = self.calculate_expected_shortfall(portfolio_returns)
        
        # Max Drawdown
        max_drawdown = self.calculate_max_drawdown(portfolio_returns)
        
        # Sharpe Ratio
        sharpe_ratio = self.calculate_sharpe_ratio(portfolio_returns)
        
        # Portfolio Beta
        market_returns = returns_dict.get('SPY', pd.Series())
        beta = self.calculate_beta(portfolio_returns, market_returns) if len(market_returns) > 0 else 1.0
        
        # Correlation Risk (average pairwise correlation)
        correlation_matrix = self.calculate_correlation_matrix(returns_dict)
        if not correlation_matrix.empty:
            # Get upper triangle of correlation matrix (excluding diagonal)
            mask = np.triu(np.ones_like(correlation_matrix), k=1).astype(bool)
            correlations = correlation_matrix.where(mask).stack()
            correlation_risk = correlations.mean() if len(correlations) > 0 else 0.0
        else:
            correlation_risk = 0.0
        
        # Concentration Risk
        concentration_risk = self.assess_concentration_risk(positions)
        
        # Volatility
        volatility = portfolio_returns.std() * np.sqrt(252) if len(portfolio_returns) > 0 else 0.0
        
        # Determine overall risk level
        risk_score = (
            abs(portfolio_var) * 20 +
            abs(max_drawdown) * 15 +
            (1 / max(sharpe_ratio, 0.1)) * 10 +
            volatility * 15 +
            concentration_risk * 20 +
            abs(correlation_risk) * 20
        )
        
        if risk_score < 20:
            risk_level = RiskLevel.LOW
        elif risk_score < 40:
            risk_level = RiskLevel.MEDIUM
        elif risk_score < 60:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL
        
        return RiskMetrics(
            portfolio_var=portfolio_var,
            expected_shortfall=expected_shortfall,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            beta=beta,
            correlation_risk=correlation_risk,
            concentration_risk=concentration_risk,
            volatility=volatility,
            risk_level=risk_level
        )
    
    def generate_risk_report(self, positions: Dict[str, float],
                           returns_dict: Dict[str, pd.Series],
                           portfolio_returns: pd.Series) -> Dict:
        """Generate comprehensive risk report"""
        
        # Calculate portfolio metrics
        portfolio_metrics = self.calculate_portfolio_metrics(positions, returns_dict, portfolio_returns)
        
        # Calculate individual position risks
        position_risks = []
        for symbol, position_size in positions.items():
            if symbol in returns_dict:
                pos_risk = self.evaluate_position_risk(symbol, position_size, positions, returns_dict)
                position_risks.append(pos_risk)
        
        # Risk warnings
        warnings = []
        if abs(portfolio_metrics.portfolio_var) > self.risk_limits['max_portfolio_var']:
            warnings.append(f"Portfolio VaR ({abs(portfolio_metrics.portfolio_var):.1%}) exceeds limit")
        
        if portfolio_metrics.max_drawdown < -self.risk_limits['max_drawdown_limit']:
            warnings.append(f"Max drawdown ({portfolio_metrics.max_drawdown:.1%}) exceeds limit")
        
        if portfolio_metrics.sharpe_ratio < self.risk_limits['min_sharpe_ratio']:
            warnings.append(f"Sharpe ratio ({portfolio_metrics.sharpe_ratio:.2f}) below minimum")
        
        if portfolio_metrics.concentration_risk > 0.8:
            warnings.append(f"High concentration risk ({portfolio_metrics.concentration_risk:.1%})")
        
        # Recommendations
        recommendations = []
        if portfolio_metrics.risk_level == RiskLevel.CRITICAL:
            recommendations.append("Consider reducing position sizes immediately")
            recommendations.append("Diversify portfolio across more uncorrelated assets")
        elif portfolio_metrics.risk_level == RiskLevel.HIGH:
            recommendations.append("Monitor positions closely")
            recommendations.append("Consider adding hedging positions")
        
        if portfolio_metrics.concentration_risk > 0.6:
            recommendations.append("Reduce concentration in top positions")
        
        if abs(portfolio_metrics.correlation_risk) > 0.7:
            recommendations.append("Add negatively correlated assets")
        
        return {
            'timestamp': datetime.now(),
            'portfolio_metrics': portfolio_metrics,
            'position_risks': position_risks,
            'warnings': warnings,
            'recommendations': recommendations,
            'risk_limits': self.risk_limits
        }

class DynamicPositionSizer:
    """Dynamic position sizing based on risk metrics"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
    
    def calculate_optimal_position_size(self, signal: TradingSignal,
                                      current_positions: Dict[str, float],
                                      returns_dict: Dict[str, pd.Series],
                                      target_risk: float = 0.01) -> float:
        """Calculate optimal position size based on Kelly Criterion and risk parity"""
        
        # Get asset returns
        asset_returns = returns_dict.get(signal.symbol, pd.Series())
        if len(asset_returns) < 30:  # Need sufficient data
            return 0.0
        
        # Calculate expected return and volatility
        expected_return = asset_returns.mean() * 252  # Annualized
        volatility = asset_returns.std() * np.sqrt(252)  # Annualized
        
        if volatility == 0:
            return 0.0
        
        # Kelly Criterion position size
        win_rate = len(asset_returns[asset_returns > 0]) / len(asset_returns)
        avg_win = asset_returns[asset_returns > 0].mean() if len(asset_returns[asset_returns > 0]) > 0 else 0
        avg_loss = abs(asset_returns[asset_returns < 0].mean()) if len(asset_returns[asset_returns < 0]) > 0 else 0
        
        if avg_loss > 0:
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        else:
            kelly_fraction = 0.1
        
        # Risk parity position size
        portfolio_volatility = 0.15  # Assume 15% target portfolio volatility
        risk_parity_fraction = (target_risk * portfolio_volatility) / volatility
        
        # Combine Kelly and Risk Parity
        optimal_fraction = min(kelly_fraction * 0.5 + risk_parity_fraction * 0.5, 0.2)  # Cap at 20%
        
        # Calculate portfolio value
        portfolio_value = sum(abs(pos) for pos in current_positions.values())
        if portfolio_value == 0:
            portfolio_value = 100000  # Assume $100k starting capital
        
        optimal_position_value = portfolio_value * optimal_fraction
        optimal_shares = optimal_position_value / signal.price if signal.price > 0 else 0
        
        return optimal_shares

def main():
    """Example usage of risk management system"""
    from advanced_trading_algo import TradingConfig
    import yfinance as yf
    
    # Initialize risk manager
    config = TradingConfig()
    risk_manager = RiskManager(config)
    
    # Example portfolio positions
    positions = {
        'AAPL': 1000,
        'GOOGL': 500,
        'MSFT': 800,
        'TSLA': 300
    }
    
    # Get historical returns data
    symbols = list(positions.keys()) + ['SPY']  # Add market benchmark
    returns_dict = {}
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1y")
            if not data.empty:
                returns_dict[symbol] = data['Close'].pct_change().dropna()
        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")
    
    # Calculate portfolio returns
    if returns_dict:
        total_value = sum(abs(pos) for pos in positions.values())
        portfolio_returns = pd.Series(0.0, index=list(returns_dict.values())[0].index)
        
        for symbol, position in positions.items():
            if symbol in returns_dict:
                weight = abs(position) / total_value
                portfolio_returns += returns_dict[symbol] * weight
        
        # Generate risk report
        risk_report = risk_manager.generate_risk_report(positions, returns_dict, portfolio_returns)
        
        print("=== PORTFOLIO RISK REPORT ===")
        print(f"Timestamp: {risk_report['timestamp']}")
        print(f"Risk Level: {risk_report['portfolio_metrics'].risk_level.value.upper()}")
        print(f"Portfolio VaR (5%): {risk_report['portfolio_metrics'].portfolio_var:.2%}")
        print(f"Expected Shortfall: {risk_report['portfolio_metrics'].expected_shortfall:.2%}")
        print(f"Max Drawdown: {risk_report['portfolio_metrics'].max_drawdown:.2%}")
        print(f"Sharpe Ratio: {risk_report['portfolio_metrics'].sharpe_ratio:.2f}")
        print(f"Portfolio Beta: {risk_report['portfolio_metrics'].beta:.2f}")
        print(f"Concentration Risk: {risk_report['portfolio_metrics'].concentration_risk:.2%}")
        
        if risk_report['warnings']:
            print("\n=== WARNINGS ===")
            for warning in risk_report['warnings']:
                print(f"⚠️  {warning}")
        
        if risk_report['recommendations']:
            print("\n=== RECOMMENDATIONS ===")
            for rec in risk_report['recommendations']:
                print(f"💡 {rec}")
        
        print("\n=== POSITION RISKS ===")
        for pos_risk in risk_report['position_risks']:
            print(f"{pos_risk.symbol}: Risk Score {pos_risk.risk_score:.1f}, "
                  f"Weight {pos_risk.portfolio_weight:.1%}, "
                  f"Volatility {pos_risk.volatility:.1%}")

if __name__ == "__main__":
    main()