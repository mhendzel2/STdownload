# IBKR Historical Data Downloader

## Overview

This application is a Python-based historical data downloader for Interactive Brokers (IBKR) that provides both a command-line interface and a web-based interface. It connects to IBKR's TWS (Trader Workstation) or Gateway API to retrieve historical market data for various financial instruments including stocks, forex, futures, and options.

## System Architecture

The application follows a modular architecture with clear separation of concerns:

### Backend Architecture
- **Flask Web Framework**: Provides the web interface and REST API endpoints
- **IBKR API Integration**: Uses the official Interactive Brokers Python API (`ibapi`) for market data retrieval
- **Threading Model**: Implements a multi-threaded approach to handle API communication asynchronously
- **Event-Driven Communication**: Uses threading events and callbacks for managing API responses

### Data Processing Pipeline
- **Contract Creation**: Dynamically creates IBKR contract objects for different security types
- **Historical Data Requests**: Manages batched requests with rate limiting and timeout handling
- **Data Storage**: Supports multiple output formats (CSV, Excel) with flexible naming conventions

## Key Components

### Core Application (`main.py`)
- **IBKRApp Class**: Main application class inheriting from both EWrapper and EClient
- **Connection Management**: Handles TWS/Gateway connections with configurable timeouts
- **Data Request Orchestration**: Manages multiple concurrent historical data requests
- **Error Handling**: Comprehensive error tracking and request-specific error storage

### Configuration System (`config.py`)
- **IBKRConfig Class**: Centralized configuration using dataclasses
- **Environment Variable Support**: Loads settings from environment variables
- **File-Based Configuration**: JSON configuration file support
- **Default Settings**: Sensible defaults for demo trading and common use cases

### Data Management (`data_handler.py`)
- **Multi-Format Export**: CSV and Excel output with multiple worksheets
- **Flexible File Naming**: Optional timestamp inclusion in filenames
- **Directory Management**: Automatic creation of output directories
- **Data Validation**: Built-in data integrity checks

### Utility Functions (`utils.py`)
- **Contract Factory**: Helper functions for creating IBKR contracts
- **Parameter Validation**: Input validation for symbols, durations, and bar sizes
- **Data Formatting**: Datetime formatting and data summary utilities
- **Supported Options**: Centralized lists of valid API parameters

### Web Interface
- **Flask Application** (`web_app.py`): RESTful API and template rendering
- **Bootstrap Frontend**: Responsive web interface with real-time status updates
- **AJAX Communication**: Asynchronous data downloads with progress tracking
- **Connection Management**: Web-based connection status and control

### Command Line Interface (`cli.py`)
- **Argument Parsing**: Comprehensive command-line argument handling
- **Batch Processing**: Support for multiple symbols in single commands
- **Flexible Parameters**: All API parameters configurable via CLI
- **Examples and Help**: Detailed usage examples and help text

## Data Flow

1. **Connection Establishment**: Application connects to IBKR TWS/Gateway using configured host/port
2. **Contract Resolution**: Symbols are converted to IBKR Contract objects with appropriate security types
3. **Historical Data Requests**: Requests are queued with rate limiting and sent to IBKR API
4. **Data Reception**: Historical bars are received asynchronously via callback methods
5. **Data Processing**: Raw data is converted to pandas DataFrames for analysis
6. **Export**: Processed data is exported to CSV or Excel files with configurable naming

## External Dependencies

### Primary Dependencies
- **ibapi**: Official Interactive Brokers Python API for market data
- **pandas**: Data manipulation and analysis library
- **flask**: Web framework for the web interface
- **openpyxl**: Excel file creation and manipulation

### Development Dependencies
- **Python 3.11+**: Modern Python runtime with enhanced type hints
- **Bootstrap 5**: Frontend CSS framework for responsive design
- **Font Awesome**: Icon library for enhanced UI

### IBKR Requirements
- **TWS or Gateway**: Must be running and configured to accept API connections
- **API Settings**: Socket port must be enabled in TWS/Gateway settings
- **Permissions**: Appropriate market data subscriptions required

## Deployment Strategy

### Local Development
- **Replit Environment**: Configured for Python 3.11 with automatic dependency installation
- **Hot Reload**: Flask development server with automatic restart on code changes
- **Port Configuration**: Web interface runs on port 5000 with automatic port forwarding

### Production Considerations
- **Environment Variables**: All sensitive configuration should use environment variables
- **Process Management**: Consider using gunicorn or similar WSGI server for production
- **Error Handling**: Comprehensive logging and error tracking implemented
- **Rate Limiting**: Built-in rate limiting respects IBKR API limits

### Configuration Management
- **Demo vs Live**: Separate port configurations for paper trading vs live accounts
- **Client ID Management**: Unique client IDs prevent connection conflicts
- **Timeout Settings**: Configurable timeouts for different network conditions

## Recent Changes

### June 25, 2025 - Major Feature Enhancement
- **Real-Time Data Streaming**: Added live market data streaming capabilities with WebSocket-based updates
- **Advanced Analytics Engine**: Implemented technical indicators, moving averages, volatility calculations
- **Enhanced Web Interface**: Created streaming dashboard, analytics page with interactive charts
- **Chart.js Integration**: Real-time price charts, volume analysis, and technical visualizations
- **Streaming Data Manager**: Background analytics processing with configurable buffer sizes
- **News Data Integration**: Complete news headlines system with sentiment analysis
- **News Provider Support**: Multi-provider news filtering and selection
- **Keyword Search**: Advanced search capabilities for news headlines
- **Sentiment Analysis**: Automated positive/negative/neutral classification
- **News Visualization**: Provider distribution and time-based news charts
- **API Expansion**: Added 14 new endpoints (8 streaming + 6 news) for comprehensive data management
- **Export Capabilities**: Real-time data and news export to CSV/JSON formats
- **Technical Signals**: Automated signal generation for trading indicators

### Architecture Updates
- **New Modules**: 
  - `streaming.py` - Manages real-time data streams and analytics calculations
  - `news_handler.py` - Complete news data management and sentiment analysis
- **Enhanced Main App**: Added tick data processing, news callbacks, real-time stream management
- **JavaScript Frontend**: New streaming.js, analytics.js, and news.js for comprehensive web functionality
- **Template System**: Added streaming.html, analytics.html, and news.html for complete interface coverage
- **API Endpoints**: Full-featured API with streaming, analytics, and news data management
- **Web Interface**: 4-page application covering all major functionalities

### Deployment Preparation
- **Complete Package**: Prepared downloadable package with all components
- **Documentation**: Created comprehensive README.md and INSTALLATION.md guides
- **Local Testing Ready**: Configured for local TWS/Gateway connection testing

## User Preferences

Preferred communication style: Simple, everyday language.