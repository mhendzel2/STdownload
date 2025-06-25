#!/usr/bin/env python3
"""
Command-line interface for IBKR Historical Data Downloader
"""

import argparse
import sys
import json
from typing import List, Optional
import pandas as pd

from main import IBKRApp
from config import get_config, IBKRConfig
from utils import (
    validate_download_parameters,
    get_supported_bar_sizes,
    get_supported_what_to_show,
    get_supported_security_types,
    format_data_summary
)
from logger import setup_logger


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Download historical data from Interactive Brokers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download AAPL data for 1 year
  python cli.py --symbols AAPL --duration "1 Y"
  
  # Download multiple stocks with custom parameters
  python cli.py --symbols "AAPL,GOOGL,MSFT" --duration "6 M" --bar-size "1 hour"
  
  # Download forex data
  python cli.py --symbols EURUSD --sec-type CASH --duration "30 D" --bar-size "1 hour"
  
  # Custom connection settings
  python cli.py --symbols AAPL --host 127.0.0.1 --port 7497 --client-id 2
        """
    )
    
    # Connection settings
    conn_group = parser.add_argument_group('Connection Settings')
    conn_group.add_argument('--host', default='127.0.0.1',
                           help='IBKR TWS/Gateway host (default: 127.0.0.1)')
    conn_group.add_argument('--port', type=int, default=7497,
                           help='IBKR TWS/Gateway port (default: 7497 for demo)')
    conn_group.add_argument('--client-id', type=int, default=1,
                           help='Client ID (default: 1)')
    
    # Data request settings
    data_group = parser.add_argument_group('Data Request Settings')
    data_group.add_argument('--symbols', required=True,
                           help='Comma-separated list of symbols (e.g., AAPL,GOOGL)')
    data_group.add_argument('--sec-type', default='STK',
                           choices=get_supported_security_types(),
                           help='Security type (default: STK)')
    data_group.add_argument('--exchange', default='SMART',
                           help='Exchange (default: SMART)')
    data_group.add_argument('--currency', default='USD',
                           help='Currency (default: USD)')
    data_group.add_argument('--duration', default='1 Y',
                           help='Duration (e.g., "1 Y", "6 M", "30 D") (default: 1 Y)')
    data_group.add_argument('--bar-size', default='1 day',
                           choices=get_supported_bar_sizes(),
                           help='Bar size (default: 1 day)')
    data_group.add_argument('--what-to-show', default='TRADES',
                           choices=get_supported_what_to_show(),
                           help='What to show (default: TRADES)')
    data_group.add_argument('--use-rth', action='store_true', default=True,
                           help='Use regular trading hours only (default: True)')
    
    # Output settings
    output_group = parser.add_argument_group('Output Settings')
    output_group.add_argument('--output-dir', default='./data',
                             help='Output directory (default: ./data)')
    output_group.add_argument('--excel', action='store_true',
                             help='Save combined data to Excel file')
    output_group.add_argument('--include-timestamp', action='store_true',
                             help='Include timestamp in filenames')
    output_group.add_argument('--summary', action='store_true',
                             help='Show data summary after download')
    
    # Other settings
    parser.add_argument('--timeout', type=int, default=60,
                       help='Data request timeout in seconds (default: 60)')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Log level (default: INFO)')
    parser.add_argument('--config-file',
                       help='Load configuration from JSON file')
    
    return parser.parse_args()


def main():
    """Main CLI function"""
    args = parse_arguments()
    
    # Setup logging
    logger = setup_logger('CLI', level=args.log_level)
    
    try:
        # Parse symbols
        symbols = [s.strip().upper() for s in args.symbols.split(',') if s.strip()]
        if not symbols:
            logger.error("No valid symbols provided")
            return 1
        
        # Validate parameters
        errors = validate_download_parameters(
            symbols, args.duration, args.bar_size, args.sec_type, args.what_to_show
        )
        
        if errors:
            logger.error("Parameter validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return 1
        
        # Create configuration
        if args.config_file:
            config = IBKRConfig.from_file(args.config_file)
        else:
            config = get_config()
        
        # Override with command line arguments
        config.host = args.host
        config.port = args.port
        config.client_id = args.client_id
        config.data_timeout = args.timeout
        config.request_delay = args.delay
        
        logger.info(f"Connecting to IBKR at {config.host}:{config.port}")
        logger.info(f"Downloading data for {len(symbols)} symbols: {', '.join(symbols)}")
        
        # Create and connect IBKR app
        app = IBKRApp(config)
        app.data_handler.output_dir = args.output_dir
        
        if not app.connect_to_ibkr():
            logger.error("Failed to connect to IBKR")
            return 1
        
        try:
            results = {}
            failed_symbols = []
            
            # Download data for each symbol
            for i, symbol in enumerate(symbols):
                logger.info(f"Downloading {symbol} ({i+1}/{len(symbols)})...")
                
                data = app.request_historical_data(
                    symbol=symbol,
                    sec_type=args.sec_type,
                    exchange=args.exchange,
                    currency=args.currency,
                    duration=args.duration,
                    bar_size=args.bar_size,
                    what_to_show=args.what_to_show,
                    use_rth=args.use_rth
                )
                
                if data is not None and not data.empty:
                    results[symbol] = data
                    
                    # Save individual CSV file
                    filename = f"{symbol}_historical_data.csv"
                    filepath = app.data_handler.save_to_csv(
                        data, filename, include_timestamp=args.include_timestamp
                    )
                    logger.info(f"Saved {symbol} data to {filepath}")
                    
                    if args.summary:
                        summary = format_data_summary(data, symbol)
                        logger.info(f"Summary for {symbol}: {summary['records']} records, "
                                  f"{summary['start_date']} to {summary['end_date']}")
                else:
                    failed_symbols.append(symbol)
                    logger.error(f"Failed to download data for {symbol}")
            
            # Save combined Excel file if requested
            if args.excel and results:
                excel_file = app.data_handler.save_multiple_to_excel(
                    results, 'historical_data_combined'
                )
                logger.info(f"Saved combined Excel file: {excel_file}")
            
            # Final summary
            logger.info(f"Download complete: {len(results)}/{len(symbols)} successful")
            if failed_symbols:
                logger.warning(f"Failed symbols: {', '.join(failed_symbols)}")
            
            return 0 if results else 1
            
        finally:
            app.disconnect_from_ibkr()
    
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
