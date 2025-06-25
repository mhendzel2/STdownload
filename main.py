import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
import pandas as pd
import queue

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import BarData, TickAttrib
from ibapi.ticktype import TickTypeEnum

from config import IBKRConfig
from data_handler import DataHandler
from news_handler import NewsDataManager
from utils import create_contract, format_datetime
from logger import setup_logger


class IBKRApp(EWrapper, EClient):
    """
    Main application class that inherits from both EWrapper and EClient
    to handle IBKR API communication and data processing.
    """
    
    def __init__(self, config: IBKRConfig):
        EClient.__init__(self, self)
        self.config = config
        self.data_handler = DataHandler()
        self.news_manager = NewsDataManager()
        self.logger = setup_logger('IBKRApp')
        
        # Connection and state management
        self.connected = False
        self.next_order_id = None
        self.connection_event = threading.Event()
        self.request_events = {}
        
        # Data storage
        self.historical_data = {}
        self.request_errors = {}
        
        # Real-time data streaming
        self.streaming_data = {}
        self.streaming_callbacks = {}
        self.tick_data_queue = queue.Queue()
        self.streaming_active = {}
        
        # Threading
        self.api_thread = None
        
    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson: str = ""):
        """Handle API errors"""
        error_msg = f"Error {errorCode}: {errorString} (reqId: {reqId})"
        self.logger.error(error_msg)
        
        # Store error for the specific request
        if reqId > 0:
            self.request_errors[reqId] = f"Error {errorCode}: {errorString}"
            if reqId in self.request_events:
                self.request_events[reqId].set()  # Signal completion on error

        if errorCode in [502, 504, 2104, 2106, 2158]:  # Connection or market data farm errors
            self.connected = False
            self.connection_event.clear()
            
    def connectAck(self):
        """Acknowledge successful connection"""
        self.logger.info("Connected to IBKR API")
        self.connected = True
        
    def nextValidId(self, orderId: int):
        """Receive next valid order ID and signal connection is fully ready"""
        self.next_order_id = orderId
        self.logger.info(f"Next valid order ID: {orderId}")
        # Signal that the connection is fully established and we have a valid ID
        self.connection_event.set()
        
    def historicalData(self, reqId: int, bar: BarData):
        """Receive historical data bars"""
        if reqId not in self.historical_data:
            self.historical_data[reqId] = []
            
        bar_data = {
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume,
            'wap': bar.wap,
            'count': bar.count
        }
        
        self.historical_data[reqId].append(bar_data)
        
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Mark end of historical data transmission"""
        self.logger.info(f"Historical data complete for request {reqId}")
        self.logger.info(f"Data period: {start} to {end}")
        if reqId in self.request_events:
            self.request_events[reqId].set()  # Signal completion
        
    def connect_to_ibkr(self) -> bool:
        """
        Connect to IBKR TWS/Gateway
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to IBKR on {self.config.host}:{self.config.port}")
            self.connect(self.config.host, self.config.port, self.config.client_id)
            
            # Start API thread
            self.api_thread = threading.Thread(target=self.run, daemon=True)
            self.api_thread.start()
            
            # Wait for connection and nextValidId to be received
            self.logger.info("Waiting for connection to be acknowledged...")
            connected = self.connection_event.wait(timeout=self.config.connection_timeout)
                
            if connected:
                self.logger.info("Successfully connected and initialized.")
                return True
            else:
                self.logger.error("Failed to connect to IBKR within the timeout period.")
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
            
    def disconnect_from_ibkr(self):
        """Disconnect from IBKR"""
        if self.isConnected():
            self.logger.info("Disconnecting from IBKR...")
            self.disconnect()
            if self.api_thread and self.api_thread.is_alive():
                self.api_thread.join(timeout=5)
            self.connected = False
            self.logger.info("Disconnected from IBKR")
            
    def request_historical_data(self, 
                              symbol: str,
                              sec_type: str = "STK",
                              exchange: str = "SMART",
                              currency: str = "USD",
                              duration: str = "1 Y",
                              bar_size: str = "1 day",
                              what_to_show: str = "TRADES",
                              use_rth: bool = True,
                              end_date: str = "") -> Optional[pd.DataFrame]:
        """
        Request historical data for a specific instrument
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            sec_type: Security type (STK, FUT, OPT, etc.)
            exchange: Exchange (SMART, NYSE, NASDAQ, etc.)
            currency: Currency (USD, EUR, etc.)
            duration: Duration string (1 Y, 6 M, 30 D, etc.)
            bar_size: Bar size (1 day, 1 hour, 5 mins, etc.)
            what_to_show: Data type (TRADES, MIDPOINT, BID, ASK, etc.)
            use_rth: Use regular trading hours only
            end_date: End date (empty for current time)
            
        Returns:
            pd.DataFrame: Historical data or None if failed
        """
        if not self.connected:
            self.logger.error("Not connected to IBKR. Please connect first.")
            return None
            
        # Handle forex pair symbols like "EURUSD"
        req_symbol = symbol
        req_currency = currency
        if sec_type == "CASH" and len(symbol) == 6:
            req_symbol = symbol[:3]
            req_currency = symbol[3:]
            self.logger.info(f"Interpreting CASH symbol '{symbol}' as {req_symbol}/{req_currency}")

        # Create contract
        contract = create_contract(req_symbol, sec_type, exchange, req_currency)
        
        # Generate unique request ID
        req_id = self.next_order_id
        self.next_order_id += 1
        
        # Initialize data storage and event for this request
        self.historical_data[req_id] = []
        self.request_errors.pop(req_id, None)
        self.request_events[req_id] = threading.Event()
        
        self.logger.info(f"Requesting historical data for {symbol} (reqId: {req_id})...")
        self.logger.info(f"Duration: {duration}, Bar size: {bar_size}, Data type: {what_to_show}")
        
        # Request historical data
        self.reqHistoricalData(
            reqId=req_id,
            contract=contract,
            endDateTime=end_date,
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=1 if use_rth else 0,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )
        
        # Wait for data to be received or an error to occur
        finished = self.request_events[req_id].wait(timeout=self.config.data_timeout)
        
        # Clean up the event
        del self.request_events[req_id]

        if not finished:
            self.logger.warning(f"Timeout waiting for data for {symbol} (reqId: {req_id})")
            self.cancelHistoricalData(req_id)
            return None

        if req_id in self.request_errors:
            self.logger.error(f"Error for {symbol}: {self.request_errors[req_id]}")
            return None
            
        if self.historical_data.get(req_id):
            df = pd.DataFrame(self.historical_data[req_id])
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                self.logger.info(f"Received {len(df)} data points for {symbol}")
                return df
        
        self.logger.warning(f"No data received for {symbol}")
        return None
            
    def download_multiple_symbols(self, symbols: List[str], **kwargs) -> Dict[str, pd.DataFrame]:
        """
        Download historical data for multiple symbols
        
        Args:
            symbols: List of stock symbols
            **kwargs: Additional parameters for request_historical_data
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping symbols to their data
        """
        results = {}
        
        for i, symbol in enumerate(symbols):
            self.logger.info(f"Downloading data for {symbol} ({i+1}/{len(symbols)})...")
            data = self.request_historical_data(symbol, **kwargs)
            if data is not None and not data.empty:
                results[symbol] = data
                # Save individual file (no timestamp by default for predictability)
                filename = f"{symbol}_historical_data.csv"
                filepath = self.data_handler.save_to_csv(data, filename, include_timestamp=False)
                self.logger.info(f"Saved {symbol} data to {filepath}")
            else:
                self.logger.error(f"Failed to download data for {symbol}")
                
            # Small delay between requests to respect API limits
            time.sleep(self.config.request_delay)
            
        return results

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib: TickAttrib):
        """Receive real-time price data"""
        tick_data = {
            'reqId': reqId,
            'tickType': tickType,
            'tickTypeName': TickTypeEnum.to_str(tickType),
            'price': price,
            'timestamp': datetime.now(),
            'canAutoExecute': attrib.canAutoExecute,
            'pastLimit': attrib.pastLimit,
            'preOpen': attrib.preOpen
        }
        
        if reqId in self.streaming_data:
            self.streaming_data[reqId].append(tick_data)
            
        # Add to queue for real-time processing
        self.tick_data_queue.put(tick_data)
        
        # Call registered callbacks
        if reqId in self.streaming_callbacks:
            for callback in self.streaming_callbacks[reqId]:
                try:
                    callback(tick_data)
                except Exception as e:
                    self.logger.error(f"Error in streaming callback: {e}")

    def tickSize(self, reqId: int, tickType: int, size: int):
        """Receive real-time size data"""
        tick_data = {
            'reqId': reqId,
            'tickType': tickType,
            'tickTypeName': TickTypeEnum.to_str(tickType),
            'size': size,
            'timestamp': datetime.now()
        }
        
        if reqId in self.streaming_data:
            self.streaming_data[reqId].append(tick_data)
            
        self.tick_data_queue.put(tick_data)
        
        if reqId in self.streaming_callbacks:
            for callback in self.streaming_callbacks[reqId]:
                try:
                    callback(tick_data)
                except Exception as e:
                    self.logger.error(f"Error in streaming callback: {e}")

    def start_real_time_data(self, symbol: str, sec_type: str = "STK", 
                           exchange: str = "SMART", currency: str = "USD",
                           callback: Optional[Callable] = None) -> int:
        """
        Start real-time data streaming for a symbol
        
        Args:
            symbol: Trading symbol
            sec_type: Security type
            exchange: Exchange
            currency: Currency
            callback: Optional callback function for real-time data
            
        Returns:
            int: Request ID for this stream
        """
        if not self.connected:
            self.logger.error("Not connected to IBKR")
            return -1
            
        contract = create_contract(symbol, sec_type, exchange, currency)
        req_id = self.next_order_id
        self.next_order_id += 1
        
        # Initialize storage for this stream
        self.streaming_data[req_id] = []
        self.streaming_active[req_id] = True
        
        if callback:
            if req_id not in self.streaming_callbacks:
                self.streaming_callbacks[req_id] = []
            self.streaming_callbacks[req_id].append(callback)
        
        # Request market data
        self.reqMktData(req_id, contract, "", False, False, [])
        
        self.logger.info(f"Started real-time data stream for {symbol} (reqId: {req_id})")
        return req_id

    def stop_real_time_data(self, req_id: int):
        """Stop real-time data streaming for a request ID"""
        if req_id in self.streaming_active:
            self.cancelMktData(req_id)
            self.streaming_active[req_id] = False
            self.logger.info(f"Stopped real-time data stream (reqId: {req_id})")

    def get_streaming_data(self, req_id: int, limit: int = 100) -> List[Dict]:
        """Get recent streaming data for a request ID"""
        if req_id in self.streaming_data:
            return self.streaming_data[req_id][-limit:]
        return []

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            'connected': self.connected,
            'next_order_id': self.next_order_id,
            'api_thread_alive': self.api_thread.is_alive() if self.api_thread else False,
            'active_streams': len([k for k, v in self.streaming_active.items() if v]),
            'news_providers_loaded': self.news_manager.providers_loaded
        }

    def historicalNews(self, reqId: int, time: str, providerCode: str, articleId: str, headline: str):
        """Receive historical news headlines"""
        self.news_manager.add_news_item(reqId, time, providerCode, articleId, headline)
        self.logger.debug(f"Received news for reqId {reqId}: {headline[:50]}...")

    def historicalNewsEnd(self, reqId: int, hasMore: bool):
        """Mark end of historical news transmission"""
        self.news_manager.mark_request_complete(reqId, hasMore)
        self.logger.info(f"Historical news complete for request {reqId}, hasMore: {hasMore}")

    def newsProviders(self, newsProviders):
        """Receive available news providers"""
        self.news_manager.set_news_providers(newsProviders)
        self.logger.info(f"Received {len(newsProviders)} news providers")

    def request_historical_news(self, symbol: str, con_id: int = None, 
                              provider_codes: str = "", start_date: str = "", 
                              end_date: str = "", total_results: int = 10) -> Optional[List[Dict]]:
        """
        Request historical news for a symbol
        
        Args:
            symbol: Trading symbol
            con_id: Contract ID (if known, otherwise will resolve from symbol)
            provider_codes: News provider codes (empty for all)
            start_date: Start date (YYYY-MM-DD HH:MM:SS format)
            end_date: End date (YYYY-MM-DD HH:MM:SS format)
            total_results: Maximum number of headlines
            
        Returns:
            List of news items or None if failed
        """
        if not self.connected:
            self.logger.error("Not connected to IBKR")
            return None

        # Use provided con_id or resolve from symbol
        if con_id is None:
            # Common contract IDs for major symbols (for demo purposes)
            contract_ids = {
                'AAPL': 265598,
                'GOOGL': 208813720,
                'MSFT': 272093,
                'TSLA': 76792991,
                'AMZN': 3691937
            }
            con_id = contract_ids.get(symbol.upper())
            if con_id is None:
                self.logger.error(f"No contract ID found for {symbol}. Please provide con_id parameter.")
                return None

        req_id = self.next_order_id
        self.next_order_id += 1

        # Register the request
        self.news_manager.register_news_request(
            req_id, symbol, con_id, provider_codes, start_date, end_date, total_results
        )

        self.logger.info(f"Requesting historical news for {symbol} (conId: {con_id}, reqId: {req_id})")
        
        # Make the request
        self.reqHistoricalNews(req_id, con_id, provider_codes, start_date, end_date, total_results)

        # Wait for completion
        success = self.news_manager.wait_for_completion(req_id, self.config.data_timeout)
        
        if success:
            news_data = self.news_manager.get_news_data(req_id)
            self.logger.info(f"Received {len(news_data)} news items for {symbol}")
            return news_data
        else:
            self.logger.warning(f"Timeout waiting for news data for {symbol}")
            return None

    def request_news_providers(self) -> bool:
        """Request available news providers"""
        if not self.connected:
            self.logger.error("Not connected to IBKR")
            return False
            
        self.reqNewsProviders()
        self.logger.info("Requested news providers")
        return True

    def get_news_data(self, req_id: int) -> List[Dict]:
        """Get news data for a request ID"""
        return self.news_manager.get_news_data(req_id)

    def export_news_data(self, req_id: int, format_type: str = 'csv') -> Optional[str]:
        """Export news data to file"""
        return self.news_manager.export_news_data(req_id, format_type)
