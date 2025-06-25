# IBKR Historical Data Downloader

A comprehensive Python application for downloading historical and real-time financial data from Interactive Brokers (IBKR) with advanced analytics and visualization capabilities.

## Features

### 🔄 Real-Time Data Streaming
- Live market data streaming for stocks, forex, futures, and options
- Real-time analytics with moving averages, volatility calculations
- WebSocket-based updates for instant data visualization
- Customizable alerts and monitoring

### 📊 Advanced Analytics & Visualization
- Interactive charts with Chart.js integration
- Technical indicators (Moving Averages, Volatility, Support/Resistance)
- Real-time dashboard with multiple data streams
- Export capabilities for charts and data

### 📰 News Data Integration
- Historical news headlines retrieval for any symbol
- News provider filtering and selection
- Keyword search and headline filtering
- Sentiment analysis with positive/negative/neutral classification
- News data visualization with time and provider distribution charts
- Export news data in CSV/JSON formats

### 📈 Historical Data Downloads
- Single and bulk symbol downloads
- Multiple timeframes (1 sec to 1 month bars)
- Various data types (TRADES, MIDPOINT, BID, ASK, etc.)
- Support for multiple asset classes (STK, FOREX, FUTURES, OPTIONS)

### 🌐 Modern Web Interface
- Responsive Bootstrap 5 design
- Real-time connection status monitoring
- Progress tracking for downloads
- File management and export features

### 🛠️ Multiple Access Methods
- Web interface for easy operation
- Command-line interface for automation
- RESTful API for programmatic access
- Comprehensive error handling and logging

## Prerequisites

### Software Requirements
1. **Python 3.11+** (recommended)
2. **Interactive Brokers TWS or IB Gateway**
   - Download from [Interactive Brokers](https://www.interactivebrokers.com/en/trading/tws.php)
   - Choose TWS (full platform) or IB Gateway (API-only, lighter)

### IBKR Account Setup
1. Valid Interactive Brokers account (paper trading supported)
2. Market data subscriptions for desired instruments
3. API access enabled in account settings

## Installation

### 1. Download and Extract
Download the complete package and extract to your desired directory.

### 2. Install Dependencies
```bash
# Install required Python packages
pip install pandas flask ibapi openpyxl

# Or using requirements.txt (if provided)
pip install -r requirements.txt
```

### 3. Configure TWS/Gateway
1. Open TWS or IB Gateway
2. Navigate to: **Edit → Global Configuration → API → Settings**
3. Enable "Enable ActiveX and Socket EClients"
4. Note the Socket Port:
   - **Paper Trading**: TWS (7497), Gateway (4002)
   - **Live Trading**: TWS (7496), Gateway (4001)
5. Ensure "Read-Only API" is disabled if you want full functionality

## Quick Start

### 1. Start TWS/Gateway
Launch your TWS or IB Gateway application and ensure it's logged in.

### 2. Start the Web Application
```bash
python web_app.py
```
The application will start on `http://localhost:5000`

### 3. Connect to IBKR
1. Open your browser to `http://localhost:5000`
2. Use the connection form in the sidebar
3. Default settings for paper trading:
   - Host: `127.0.0.1`
   - Port: `7497` (TWS) or `4002` (Gateway)
   - Client ID: `1`

### 4. Download Historical Data
1. Navigate to the "Download" page
2. Enter symbol(s) and configure parameters
3. Click "Download Data"
4. Files are saved to the `data/` directory

### 5. Start Real-Time Streaming
1. Navigate to the "Streaming" page
2. Enter a symbol and click "Start Stream"
3. View live data in the dashboard
4. Access analytics on the "Analytics" page

### 6. Access News Data
1. Navigate to the "News" page
2. Enter a symbol (AAPL, GOOGL, MSFT, TSLA, AMZN supported)
3. Configure providers, date range, and result count
4. View headlines with sentiment analysis
5. Search and export news data

## Command Line Usage

### Basic Examples
```bash
# Download AAPL data for 1 year
python cli.py --symbols AAPL --duration "1 Y"

# Download multiple stocks with custom parameters
python cli.py --symbols "AAPL,GOOGL,MSFT" --duration "6 M" --bar-size "1 hour"

# Download forex data
python cli.py --symbols EURUSD --sec-type CASH --duration "30 D" --bar-size "1 hour"

# Save to Excel format
python cli.py --symbols "AAPL,GOOGL" --excel --include-timestamp
```

### Advanced Options
```bash
# Custom connection settings
python cli.py --symbols AAPL --host 127.0.0.1 --port 7497 --client-id 2

# Different data types
python cli.py --symbols AAPL --what-to-show MIDPOINT --use-rth

# Custom output directory
python cli.py --symbols AAPL --output-dir ./my_data

# Verbose logging
python cli.py --symbols AAPL --log-level DEBUG
```

## API Reference

### Connection Endpoints
- `GET /api/connection/status` - Get connection status
- `POST /api/connection/connect` - Connect to IBKR
- `POST /api/connection/disconnect` - Disconnect from IBKR

### Historical Data Endpoints
- `POST /api/download/single` - Download single symbol
- `POST /api/download/multiple` - Download multiple symbols
- `GET /api/download/status` - Get download progress

### Real-Time Streaming Endpoints
- `POST /api/streaming/start` - Start real-time stream
- `POST /api/streaming/stop` - Stop real-time stream
- `GET /api/streaming/data/{req_id}` - Get streaming data
- `GET /api/streaming/dashboard` - Get streaming dashboard
- `GET /api/streaming/chart/{req_id}` - Get chart data
- `GET /api/streaming/export/{req_id}` - Export streaming data

### File Management Endpoints
- `GET /api/files` - List data files
- `GET /api/files/{filename}` - Download specific file

## Configuration

### Environment Variables
Create a `.env` file or set environment variables:

```bash
# Connection settings
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1

# Timeout settings
IBKR_CONNECTION_TIMEOUT=30
IBKR_DATA_TIMEOUT=60

# Default parameters
IBKR_DEFAULT_DURATION=1 Y
IBKR_DEFAULT_BAR_SIZE=1 day
IBKR_DEFAULT_WHAT_TO_SHOW=TRADES

# Logging
LOG_LEVEL=INFO
```

### Configuration File
Create a `config.json` file:

```json
{
  "host": "127.0.0.1",
  "port": 7497,
  "client_id": 1,
  "connection_timeout": 30,
  "data_timeout": 60,
  "request_delay": 1.0,
  "default_duration": "1 Y",
  "default_bar_size": "1 day",
  "default_what_to_show": "TRADES",
  "default_use_rth": true
}
```

## File Structure

```
ibkr-data-downloader/
├── main.py                 # Core IBKR application logic
├── web_app.py             # Flask web application
├── cli.py                 # Command-line interface
├── config.py              # Configuration management
├── data_handler.py        # Data storage and export
├── streaming.py           # Real-time streaming manager
├── news_handler.py        # News data management
├── utils.py               # Utility functions
├── logger.py              # Logging configuration
├── templates/             # HTML templates
│   ├── index.html
│   ├── download.html
│   ├── streaming.html
│   ├── analytics.html
│   └── news.html
├── static/               # Static assets
│   ├── style.css
│   ├── app.js
│   ├── download.js
│   ├── streaming.js
│   ├── analytics.js
│   └── news.js
├── data/                 # Downloaded data files
└── logs/                 # Application logs
```

## Supported Instruments

### Security Types
- **STK**: Stocks
- **CASH**: Forex pairs
- **FUT**: Futures
- **OPT**: Options
- **BOND**: Bonds
- **CFD**: Contracts for Difference

### Bar Sizes
- Seconds: 1 sec, 5 secs, 10 secs, 15 secs, 30 secs
- Minutes: 1 min, 2 mins, 3 mins, 5 mins, 10 mins, 15 mins, 20 mins, 30 mins
- Hours: 1 hour, 2 hours, 3 hours, 4 hours, 8 hours
- Days: 1 day, 1 week, 1 month

### Data Types
- **TRADES**: Actual trades
- **MIDPOINT**: Midpoint between bid/ask
- **BID**: Bid prices
- **ASK**: Ask prices
- **BID_ASK**: Both bid and ask
- **HISTORICAL_VOLATILITY**: Historical volatility
- **OPTION_IMPLIED_VOLATILITY**: Implied volatility

## Troubleshooting

### Common Connection Issues

**Error 502: Couldn't connect to TWS**
- Ensure TWS/Gateway is running and logged in
- Check API settings are enabled
- Verify correct port number
- Ensure client ID is unique

**Connection Timeout**
- Increase connection timeout in configuration
- Check firewall settings
- Verify TWS/Gateway is accepting connections

**Market Data Issues**
- Verify market data subscriptions
- Check trading permissions
- Ensure data feed is active

### Performance Tips

**For Large Downloads**
- Use appropriate bar sizes (larger bars = fewer data points)
- Implement delays between requests
- Monitor memory usage for very large datasets

**For Real-Time Streaming**
- Limit number of concurrent streams
- Adjust update frequencies based on needs
- Monitor data buffer sizes

### Error Handling
- All errors are logged to the `logs/` directory
- Check console output for immediate feedback
- Use DEBUG log level for detailed troubleshooting

## License

This project is provided as-is for educational and personal use. Please ensure compliance with Interactive Brokers' API terms of service.

## Contributing

Feel free to submit issues, feature requests, or pull requests. When contributing:

1. Follow existing code style
2. Add appropriate error handling
3. Include documentation for new features
4. Test with both paper and live accounts (where appropriate)

## Disclaimer

This software is for educational and research purposes. Always verify data accuracy and test thoroughly before using in production trading environments. The authors are not responsible for any financial losses incurred through the use of this software.