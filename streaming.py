"""
Real-time data streaming module for IBKR Historical Data Downloader
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import pandas as pd
import json
from collections import deque

from logger import setup_logger


class StreamingDataManager:
    """Manages real-time data streams and analytics"""
    
    def __init__(self, max_buffer_size: int = 1000):
        self.logger = setup_logger('StreamingDataManager')
        self.max_buffer_size = max_buffer_size
        
        # Data storage
        self.streams = {}  # req_id -> stream info
        self.data_buffers = {}  # req_id -> deque of tick data
        self.analytics = {}  # req_id -> calculated metrics
        
        # Threading
        self.analytics_thread = None
        self.running = False
        
    def start_analytics_engine(self):
        """Start the analytics calculation thread"""
        if not self.running:
            self.running = True
            self.analytics_thread = threading.Thread(target=self._analytics_worker, daemon=True)
            self.analytics_thread.start()
            self.logger.info("Analytics engine started")
    
    def stop_analytics_engine(self):
        """Stop the analytics calculation thread"""
        self.running = False
        if self.analytics_thread:
            self.analytics_thread.join(timeout=5)
        self.logger.info("Analytics engine stopped")
    
    def register_stream(self, req_id: int, symbol: str, sec_type: str = "STK"):
        """Register a new data stream"""
        self.streams[req_id] = {
            'symbol': symbol,
            'sec_type': sec_type,
            'start_time': datetime.now(),
            'active': True
        }
        self.data_buffers[req_id] = deque(maxlen=self.max_buffer_size)
        self.analytics[req_id] = {}
        self.logger.info(f"Registered stream for {symbol} (reqId: {req_id})")
    
    def add_tick_data(self, req_id: int, tick_data: Dict[str, Any]):
        """Add new tick data to the buffer"""
        if req_id in self.data_buffers:
            # Add timestamp if not present
            if 'timestamp' not in tick_data:
                tick_data['timestamp'] = datetime.now()
            
            self.data_buffers[req_id].append(tick_data)
    
    def unregister_stream(self, req_id: int):
        """Unregister a data stream"""
        if req_id in self.streams:
            self.streams[req_id]['active'] = False
            symbol = self.streams[req_id]['symbol']
            self.logger.info(f"Unregistered stream for {symbol} (reqId: {req_id})")
    
    def get_stream_data(self, req_id: int, limit: int = 100) -> List[Dict]:
        """Get recent data for a stream"""
        if req_id in self.data_buffers:
            data = list(self.data_buffers[req_id])
            return data[-limit:] if limit > 0 else data
        return []
    
    def get_stream_analytics(self, req_id: int) -> Dict[str, Any]:
        """Get calculated analytics for a stream"""
        return self.analytics.get(req_id, {})
    
    def get_all_streams(self) -> Dict[int, Dict]:
        """Get information about all streams"""
        return self.streams.copy()
    
    def _analytics_worker(self):
        """Worker thread for calculating real-time analytics"""
        while self.running:
            try:
                for req_id in list(self.data_buffers.keys()):
                    if req_id in self.streams and self.streams[req_id]['active']:
                        self._calculate_analytics(req_id)
                time.sleep(1)  # Update analytics every second
            except Exception as e:
                self.logger.error(f"Error in analytics worker: {e}")
    
    def _calculate_analytics(self, req_id: int):
        """Calculate analytics for a specific stream"""
        if req_id not in self.data_buffers:
            return
        
        data = list(self.data_buffers[req_id])
        if not data:
            return
        
        # Extract price data
        prices = []
        volumes = []
        timestamps = []
        
        for tick in data:
            if 'price' in tick and tick['price'] > 0:
                prices.append(tick['price'])
                timestamps.append(tick['timestamp'])
            elif 'size' in tick and tick['size'] > 0:
                volumes.append(tick['size'])
        
        analytics = {}
        
        if prices:
            analytics.update(self._calculate_price_analytics(prices, timestamps))
        
        if volumes:
            analytics['total_volume'] = sum(volumes)
            analytics['avg_volume'] = sum(volumes) / len(volumes)
        
        analytics['last_update'] = datetime.now()
        analytics['data_points'] = len(data)
        
        self.analytics[req_id] = analytics
    
    def _calculate_price_analytics(self, prices: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Calculate price-based analytics"""
        if not prices:
            return {}
        
        current_price = prices[-1]
        high_price = max(prices)
        low_price = min(prices)
        
        # Calculate moving averages
        ma_periods = [5, 10, 20]
        moving_averages = {}
        
        for period in ma_periods:
            if len(prices) >= period:
                ma = sum(prices[-period:]) / period
                moving_averages[f'ma_{period}'] = ma
        
        # Calculate price change
        price_change = 0
        price_change_pct = 0
        
        if len(prices) > 1:
            initial_price = prices[0]
            price_change = current_price - initial_price
            price_change_pct = (price_change / initial_price) * 100 if initial_price > 0 else 0
        
        # Calculate volatility (standard deviation of price changes)
        volatility = 0
        if len(prices) > 2:
            price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            mean_change = sum(price_changes) / len(price_changes)
            variance = sum((change - mean_change) ** 2 for change in price_changes) / len(price_changes)
            volatility = variance ** 0.5
        
        return {
            'current_price': current_price,
            'high_price': high_price,
            'low_price': low_price,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'volatility': volatility,
            'moving_averages': moving_averages,
            'price_range': high_price - low_price
        }
    
    def export_stream_data(self, req_id: int, format: str = 'csv') -> Optional[str]:
        """Export stream data to file"""
        if req_id not in self.data_buffers or req_id not in self.streams:
            return None
        
        data = list(self.data_buffers[req_id])
        if not data:
            return None
        
        symbol = self.streams[req_id]['symbol']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            if format.lower() == 'csv':
                df = pd.DataFrame(data)
                filename = f"streaming_{symbol}_{timestamp}.csv"
                filepath = f"data/{filename}"
                df.to_csv(filepath, index=False)
                self.logger.info(f"Exported streaming data to {filepath}")
                return filepath
            
            elif format.lower() == 'json':
                filename = f"streaming_{symbol}_{timestamp}.json"
                filepath = f"data/{filename}"
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                self.logger.info(f"Exported streaming data to {filepath}")
                return filepath
                
        except Exception as e:
            self.logger.error(f"Failed to export streaming data: {e}")
        
        return None


class StreamingVisualization:
    """Handles real-time data visualization"""
    
    def __init__(self):
        self.logger = setup_logger('StreamingVisualization')
    
    def generate_chart_data(self, stream_data: List[Dict], analytics: Dict) -> Dict[str, Any]:
        """Generate data for real-time charts"""
        if not stream_data:
            return {}
        
        # Extract price data for charts
        price_data = []
        volume_data = []
        timestamps = []
        
        for tick in stream_data:
            if 'price' in tick and tick['price'] > 0:
                price_data.append({
                    'time': tick['timestamp'].isoformat(),
                    'price': tick['price'],
                    'type': tick.get('tickTypeName', 'Unknown')
                })
                timestamps.append(tick['timestamp'].isoformat())
            
            if 'size' in tick and tick['size'] > 0:
                volume_data.append({
                    'time': tick['timestamp'].isoformat(),
                    'volume': tick['size'],
                    'type': tick.get('tickTypeName', 'Unknown')
                })
        
        # Prepare chart configuration
        chart_data = {
            'price_series': price_data[-100:],  # Last 100 points
            'volume_series': volume_data[-100:],
            'analytics': analytics,
            'last_update': datetime.now().isoformat()
        }
        
        return chart_data
    
    def generate_dashboard_data(self, all_streams: Dict[int, Dict], 
                              streaming_manager: StreamingDataManager) -> Dict[str, Any]:
        """Generate data for the streaming dashboard"""
        dashboard_data = {
            'streams': [],
            'summary': {
                'total_streams': 0,
                'active_streams': 0,
                'total_data_points': 0
            },
            'last_update': datetime.now().isoformat()
        }
        
        for req_id, stream_info in all_streams.items():
            if stream_info['active']:
                analytics = streaming_manager.get_stream_analytics(req_id)
                recent_data = streaming_manager.get_stream_data(req_id, 10)
                
                stream_data = {
                    'req_id': req_id,
                    'symbol': stream_info['symbol'],
                    'sec_type': stream_info['sec_type'],
                    'start_time': stream_info['start_time'].isoformat(),
                    'analytics': analytics,
                    'data_points': analytics.get('data_points', 0),
                    'current_price': analytics.get('current_price'),
                    'price_change': analytics.get('price_change'),
                    'price_change_pct': analytics.get('price_change_pct')
                }
                
                dashboard_data['streams'].append(stream_data)
                dashboard_data['summary']['active_streams'] += 1
                dashboard_data['summary']['total_data_points'] += analytics.get('data_points', 0)
        
        dashboard_data['summary']['total_streams'] = len(all_streams)
        
        return dashboard_data