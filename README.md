# 🚀 Advanced Trading Algorithm

Ein fortschrittlicher algorithmischer Trading-Bot mit mehreren Strategien, Risikomanagement und Live-Trading über Alpaca Markets.

## ✨ Features

### 📊 Mehrfache Trading-Strategien
- **RSI (Relative Strength Index)**: Identifiziert überkaufte/überverkaufte Bedingungen
- **MACD (Moving Average Convergence Divergence)**: Momentum-basierte Signale
- **Bollinger Bands**: Volatilitäts-basierte Ein- und Ausstiegspunkte
- **Moving Average Crossover**: Trend-folgende Signale
- **Kombinierte Signale**: Gewichtete Entscheidungen aus allen Strategien

### 🎯 Intelligente Signal-Generierung
- Kontinuierliche Marktdaten-Aktualisierung
- Konfidenz-basierte Signalfilterung
- Multi-Timeframe-Analyse
- Adaptive Schwellenwerte

### 🔒 Erweiterte Risikomanagement
- **Value at Risk (VaR)** Berechnung
- **Maximum Drawdown** Überwachung
- **Position Sizing** nach Kelly-Kriterium
- **Korrelations-Risiko** Analyse
- **Konzentrations-Risiko** Bewertung
- Dynamische Stop-Loss und Take-Profit Orders

### 📈 Live Trading Integration
- **Alpaca Markets API** Integration
- Automatische Orderausführung
- Portfolio-Überwachung in Echtzeit
- Bracket Orders (Stop-Loss + Take-Profit)

### 🔍 Backtesting & Optimierung
- Historische Performance-Analyse
- Strategie-Vergleich
- Risiko-adjustierte Renditen
- Sharpe Ratio und weitere Metriken

### 🌐 Web Dashboard
- Live Portfolio-Monitoring
- Signal-Visualisierung
- Technische Analyse Charts
- Konfiguration über GUI

## 🛠️ Installation

### 1. Repository klonen
```bash
git clone <repository-url>
cd advanced-trading-algorithm
```

### 2. Python Environment einrichten
```bash
python -m venv trading_env
source trading_env/bin/activate  # Linux/Mac
# oder
trading_env\Scripts\activate  # Windows
```

### 3. Dependencies installieren
```bash
pip install -r requirements.txt
```

### 4. Alpaca API Konfiguration
1. Registrieren Sie sich bei [Alpaca Markets](https://alpaca.markets/)
2. Erstellen Sie API Keys (Paper Trading empfohlen für Tests)
3. Konfigurieren Sie `trading_config.json`:

```json
{
    "alpaca": {
        "api_key": "IHR_ALPACA_API_KEY",
        "secret_key": "IHR_ALPACA_SECRET_KEY",
        "base_url": "https://paper-api.alpaca.markets",
        "data_url": "https://data.alpaca.markets"
    }
}
```

## 🚀 Verwendung

### Live Trading Bot starten
```bash
python advanced_trading_algo.py
```

### Web Dashboard starten
```bash
streamlit run dashboard.py
```
Öffnen Sie dann http://localhost:8501 in Ihrem Browser.

### Backtesting durchführen
```bash
python backtesting.py
```

### Risikomanagement testen
```bash
python risk_manager.py
```

## ⚙️ Konfiguration

### Trading Parameter
```json
{
    "trading": {
        "symbols": ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"],
        "max_position_size": 0.1,        // 10% max pro Position
        "stop_loss_pct": 0.02,           // 2% Stop Loss
        "take_profit_pct": 0.04,         // 4% Take Profit
        "min_confidence": 0.6,           // 60% min. Signalstärke
        "risk_per_trade": 0.01           // 1% Risiko pro Trade
    }
}
```

### Strategie-Gewichtung
```json
{
    "strategies": {
        "rsi": {"enabled": true, "weight": 0.25},
        "macd": {"enabled": true, "weight": 0.25},
        "bollinger": {"enabled": true, "weight": 0.25},
        "ma_crossover": {"enabled": true, "weight": 0.25}
    }
}
```

## 📊 Dashboard Features

### Portfolio Overview
- Aktuelle Portfoliowert
- Verfügbare Kaufkraft
- Aktive Positionen
- Unrealisierte Gewinne/Verluste

### Live Signals
- Echtzeit-Signalgenerierung
- Technische Analyse Charts
- Konfidenz-Bewertungen
- Entry/Exit Punkte

### Backtesting
- Historische Performance
- Strategie-Vergleich
- Risiko-Metriken
- Drawdown-Analyse

### Konfiguration
- Parameter-Anpassung über GUI
- Strategie-Aktivierung/Deaktivierung
- Risikomanagement-Einstellungen

## 🔧 Erweiterte Features

### Risikomanagement
```python
from risk_manager import RiskManager, DynamicPositionSizer

# Risikobewertung für Signal
risk_manager = RiskManager(config)
is_safe, reason, risk_score = risk_manager.assess_signal_risk(
    signal, current_positions, returns_data
)

# Optimale Positionsgröße berechnen
position_sizer = DynamicPositionSizer(risk_manager)
optimal_size = position_sizer.calculate_optimal_position_size(
    signal, current_positions, returns_data
)
```

### Custom Strategien hinzufügen
```python
def custom_strategy(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
    # Ihre benutzerdefinierte Logik hier
    if custom_condition:
        return TradingSignal(
            symbol=symbol,
            signal_type=SignalType.BUY,
            confidence=0.8,
            strategy="Custom",
            price=current_price,
            timestamp=datetime.now()
        )
    return None
```

## 📈 Performance Metriken

Der Algorithmus trackt folgende Metriken:
- **Total Return**: Gesamtrendite
- **Sharpe Ratio**: Risiko-adjustierte Rendite
- **Maximum Drawdown**: Größter Verlust vom Höchststand
- **Win Rate**: Prozentsatz gewinnbringender Trades
- **Profit Factor**: Verhältnis Gewinne zu Verlusten
- **Value at Risk (VaR)**: Potenzielle Verluste bei gegebenem Konfidenzniveau

## ⚠️ Wichtige Hinweise

### Risiken
- **Marktrisiko**: Alle Investments bergen Verlustrisiken
- **Technisches Risiko**: Algorithmusfehler können zu Verlusten führen
- **Liquiditätsrisiko**: Nicht alle Positionen können sofort geschlossen werden

### Empfehlungen
1. **Starten Sie mit Paper Trading** (Alpaca Sandbox)
2. **Testen Sie ausgiebig** mit historischen Daten
3. **Beginnen Sie mit kleinen Positionsgrößen**
4. **Überwachen Sie die Performance** kontinuierlich
5. **Diversifizieren Sie** Ihre Strategien und Assets

### Rechtliche Hinweise
- Dieser Code dient nur zu Bildungszwecken
- Keine Anlageberatung oder Garantien
- Verwenden Sie auf eigenes Risiko
- Konsultieren Sie einen Finanzberater

## 🔄 Updates und Wartung

### Logs überwachen
```bash
tail -f trading_algo.log
```

### Performance überwachen
Das Dashboard zeigt Echtzeit-Metriken. Zusätzlich werden alle Trades und Signale geloggt.

### Konfiguration anpassen
Passen Sie `trading_config.json` an Ihre Bedürfnisse an und starten Sie den Bot neu.

## 🤝 Beitragen

Verbesserungsvorschläge und Pull Requests sind willkommen!

### Entwicklung
```bash
# Tests ausführen
python -m pytest tests/

# Code-Qualität prüfen
flake8 *.py
black *.py
```

## 📞 Support

Bei Fragen oder Problemen:
1. Prüfen Sie die Logs (`trading_algo.log`)
2. Überprüfen Sie Ihre API-Konfiguration
3. Stellen Sie sicher, dass alle Dependencies installiert sind

## 📜 Lizenz

MIT License - siehe LICENSE Datei für Details.

---

**⚡ Viel Erfolg beim Trading! ⚡**

*Denken Sie daran: Vergangene Performance ist kein Indikator für zukünftige Ergebnisse. Investieren Sie nur, was Sie sich leisten können zu verlieren.*