# 🚀 Advanced Algorithmic Trading System

Ein hochmodernes, multi-strategisches Trading-System mit Live-Order-Ausführung über Alpaca API, umfassendem Risk Management und Echtzeit-Marktanalyse.

## ✨ Features

### 🎯 Multi-Strategy Trading
- **Momentum Strategy**: Identifiziert starke Preisbewegungen
- **RSI Strategy**: Erkennt überkaufte/überverkaufte Zustände
- **Moving Average Crossover**: Klassische Trendfolge-Strategie
- **Bollinger Bands**: Volatilitäts-basierte Signale
- **Kombiniertes Signal-Management**: Mehrheitsentscheidung aus allen Strategien

### 📊 Live Market Data
- **Echtzeit-Preise**: 5-Minuten-Intervalle für aktuelle Kurse
- **Marktstatus-Monitor**: Automatische Erkennung von Handelszeiten
- **Live Signal Monitor**: Echtzeit-Signale für mehrere Symbole
- **Performance Dashboard**: Live-Tracking aller Indikatoren

### 🛡️ Risk Management
- **Position Sizing**: Automatische Positionsgrößen-Berechnung
- **Stop-Loss Orders**: Automatische Verlustbegrenzung
- **Take-Profit Orders**: Automatische Gewinnmitnahme
- **Bracket Orders**: Kombination aus Entry, SL und TP
- **Risk per Trade**: Begrenzung des Kapitaleinsatzes pro Trade

### 💼 Portfolio Management
- **Live Account Sync**: Echtzeit-Synchronisation mit Alpaca Account
- **Order Management**: Aktive Order-Überwachung und -Verwaltung
- **Performance Tracking**: Detaillierte Handelsstatistiken
- **Win Rate Analysis**: Erfolgsquoten und Profit/Loss Tracking
- **Trade History**: Vollständige Aufzeichnung aller Transaktionen

### 🔗 Alpaca Integration
- **Paper Trading**: Sicheres Testen ohne echtes Geld
- **Live Trading**: Echte Order-Ausführung (mit API-Schlüsseln)
- **Account Management**: Echtzeit-Account-Informationen
- **Order Status**: Live-Order-Tracking und -Updates

## 🚀 Installation & Setup

### Voraussetzungen
```bash
pip install streamlit pandas numpy plotly yfinance
pip install alpaca-trade-api  # Für Live-Trading
```

### Alpaca API Setup
1. **Konto erstellen**: [alpaca.markets](https://alpaca.markets/)
2. **API-Schlüssel generieren**: Dashboard → API Keys
3. **Paper Trading aktivieren**: Für sicheres Testen

### Starten der Anwendung
```bash
streamlit run Algorithmic-Trading-Python.py
```

## ⚙️ Konfiguration

### API-Konfiguration (Sidebar)
- **Alpaca API Key**: Ihr API-Schlüssel
- **Alpaca API Secret**: Ihr API-Geheimnis
- **Paper Trading**: Test-Modus aktivieren

### Trading-Einstellungen
- **Initial Balance**: Startkapital ($)
- **Max Position Size**: Maximale Positionsgröße (%)
- **Risk per Trade**: Risiko pro Trade (%)

### Risk Management
- **Stop Loss**: Verlustbegrenzung (%)
- **Take Profit**: Gewinnmitnahme (%)
- **Bracket Orders**: Automatische SL/TP Orders

### Strategie-Parameter
- **RSI Period**: RSI-Berechnungszeitraum
- **RSI Overbought/Oversold**: Schwellenwerte
- **Moving Average Periods**: Kurz-/Langfrist-MA

## 📈 Verwendung

### 1. Live Market Dashboard
- **Marktstatus**: Aktuelle Handelszeiten
- **Live-Preise**: Echtzeit-Kurse für Top-Symbole
- **Signal-Monitor**: Live-Trading-Signale

### 2. Stock-Analyse
- **Symbol eingeben**: z.B. AAPL, TSLA, MSFT
- **Zeitraum wählen**: 1M, 3M, 6M, 1Y
- **Analyse anzeigen**: Umfassende Chart-Analyse

### 3. Live Trading (mit API-Schlüsseln)
- **Signal befolgen**: BUY/SELL Buttons
- **Order-Management**: Aktive Orders verwalten
- **Portfolio-Tracking**: Live-Account-Status

## 🎯 Trading-Strategien

### Momentum Strategy
- Erkennt starke Preisbewegungen
- Kauft bei >5% Momentum
- Verkauft bei <-5% Momentum

### RSI Strategy
- Relative Strength Index (RSI)
- Kauft bei RSI < 30 (überverkauft)
- Verkauft bei RSI > 70 (überkauft)

### Moving Average Crossover
- Vergleicht kurz- und langfristige gleitende Durchschnitte
- Kauft bei goldenem Kreuz (kurz > lang)
- Verkauft bei totem Kreuz (kurz < lang)

### Bollinger Bands
- Volatilitäts-basierte Bänder
- Kauft bei Berührung unteres Band
- Verkauft bei Berührung oberes Band

## 🛡️ Sicherheit & Risk Management

- **Paper Trading**: Testen ohne echtes Geld
- **Position Limits**: Automatische Positionsgrößen-Kontrolle
- **Risk Limits**: Maximale Verluste pro Trade
- **Stop Losses**: Automatische Verlustbegrenzung
- **Order Management**: Vollständige Order-Kontrolle

## 📊 Performance-Metriken

- **Total P&L**: Gesamtgewinn/-verlust
- **Win Rate**: Erfolgsquote der Trades
- **Total Trades**: Anzahl ausgeführter Trades
- **Performance Chart**: Visuelle Darstellung der Entwicklung

## 🔧 Erweiterte Features

- **Auto-Refresh**: Automatische Datenaktualisierung
- **Custom Symbols**: Beliebige Aktien analysieren
- **Strategy Breakdown**: Detaillierte Strategie-Analyse
- **Signal Strength**: Stärke der Handelssignale
- **Quick Analysis**: Schnelle Marktbeurteilung

## 🚨 Wichtige Hinweise

⚠️ **Dies ist ein Algorithmic Trading System für Bildungszwecke**

- **Risiko**: Trading birgt hohe Verlustrisiken
- **Testen**: Verwenden Sie immer Paper Trading zuerst
- **Überwachung**: Überwachen Sie das System regelmäßig
- **Limits**: Setzen Sie klare Verlustgrenzen
- **Wissen**: Verstehen Sie die Strategien vor der Nutzung

## 📞 Support

Bei Fragen oder Problemen:
1. Überprüfen Sie die Alpaca API-Dokumentation
2. Testen Sie im Paper Trading Modus
3. Überwachen Sie die Streamlit-Konsole auf Fehler
4. Stellen Sie sicher, dass alle Dependencies installiert sind

## 🔄 Updates & Entwicklung

Das System wird kontinuierlich weiterentwickelt mit:
- Zusätzlichen Trading-Strategien
- Erweiterten Risk Management Tools
- Verbesserten Performance-Metriken
- Machine Learning Integration
- Mobile App Unterstützung

---

**Erstellt mit ❤️ für die Trading-Community**