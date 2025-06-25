# Installation Guide

## Download Package

You can download the complete IBKR Historical Data Downloader package using these files:

### Core Python Files
- `main.py` - Core IBKR application logic with real-time streaming and news
- `web_app.py` - Flask web application with comprehensive API endpoints
- `cli.py` - Command-line interface for automation
- `config.py` - Configuration management system
- `data_handler.py` - Data storage and export functionality
- `streaming.py` - Real-time data streaming and analytics manager
- `news_handler.py` - News data management and sentiment analysis
- `utils.py` - Utility functions and validation
- `logger.py` - Logging configuration

### Web Interface Files
- `templates/index.html` - Main homepage with navigation
- `templates/download.html` - Historical data download page
- `templates/streaming.html` - Real-time streaming interface
- `templates/analytics.html` - Advanced analytics and charts
- `templates/news.html` - News data and sentiment analysis
- `static/style.css` - Custom styling and themes
- `static/app.js` - Main JavaScript functionality and API docs
- `static/download.js` - Download page functionality
- `static/streaming.js` - Real-time streaming JavaScript
- `static/analytics.js` - Analytics and visualization JavaScript
- `static/news.js` - News data management and search functionality

### Documentation
- `README.md` - Complete documentation and usage guide

## Quick Setup Instructions

1. **Prerequisites**
   ```bash
   # Ensure Python 3.11+ is installed
   python --version
   
   # Install required packages
   pip install pandas flask ibapi openpyxl
   ```

2. **IBKR Setup**
   - Install TWS or IB Gateway from Interactive Brokers
   - Enable API access in settings
   - Note connection ports (7497 for demo, 7496 for live)

3. **Run Application**
   ```bash
   # Start the web application
   python web_app.py
   
   # Or use command line interface
   python cli.py --symbols AAPL --duration "1 Y"
   ```

4. **Access Web Interface**
   - Open browser to `http://localhost:5000`
   - Connect to IBKR using the connection form
   - Start downloading data or streaming real-time data

## Directory Structure After Setup

```
ibkr-data-downloader/
├── data/                 # Downloaded data files (auto-created)
├── logs/                 # Application logs (auto-created)
├── templates/           # HTML templates
├── static/             # CSS and JavaScript files
├── *.py               # Python application files
└── README.md         # Documentation
```

The application will automatically create `data/` and `logs/` directories when first run.