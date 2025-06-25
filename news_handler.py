"""
News data handling module for IBKR Historical Data Downloader
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import json

from logger import setup_logger


class NewsDataManager:
    """Manages news data retrieval and storage"""
    
    def __init__(self):
        self.logger = setup_logger('NewsDataManager')
        
        # News storage
        self.news_data = {}  # req_id -> list of news items
        self.news_requests = {}  # req_id -> request info
        self.request_events = {}  # req_id -> threading.Event
        
        # News providers cache
        self.news_providers = []
        self.providers_loaded = False
        
    def add_news_item(self, req_id: int, time_str: str, provider_code: str, 
                     article_id: str, headline: str):
        """Add a news item to storage"""
        if req_id not in self.news_data:
            self.news_data[req_id] = []
            
        news_item = {
            'timestamp': time_str,
            'provider_code': provider_code,
            'article_id': article_id,
            'headline': headline,
            'received_at': datetime.now().isoformat()
        }
        
        self.news_data[req_id].append(news_item)
        self.logger.debug(f"Added news item for reqId {req_id}: {headline[:50]}...")
    
    def mark_request_complete(self, req_id: int, has_more: bool = False):
        """Mark a news request as complete"""
        if req_id in self.request_events:
            self.request_events[req_id].set()
            
        if req_id in self.news_requests:
            self.news_requests[req_id]['completed'] = True
            self.news_requests[req_id]['has_more'] = has_more
            self.news_requests[req_id]['completed_at'] = datetime.now().isoformat()
            
        self.logger.info(f"News request {req_id} completed. Has more: {has_more}")
    
    def get_news_data(self, req_id: int) -> List[Dict]:
        """Get news data for a request ID"""
        return self.news_data.get(req_id, [])
    
    def get_request_info(self, req_id: int) -> Optional[Dict]:
        """Get request information"""
        return self.news_requests.get(req_id)
    
    def register_news_request(self, req_id: int, symbol: str, con_id: int, 
                            provider_codes: str, start_date: str, end_date: str, 
                            total_results: int):
        """Register a new news request"""
        self.news_requests[req_id] = {
            'symbol': symbol,
            'con_id': con_id,
            'provider_codes': provider_codes,
            'start_date': start_date,
            'end_date': end_date,
            'total_results': total_results,
            'started_at': datetime.now().isoformat(),
            'completed': False,
            'has_more': False
        }
        
        self.request_events[req_id] = threading.Event()
        self.news_data[req_id] = []
        
        self.logger.info(f"Registered news request {req_id} for {symbol}")
    
    def wait_for_completion(self, req_id: int, timeout: int = 30) -> bool:
        """Wait for a news request to complete"""
        if req_id in self.request_events:
            return self.request_events[req_id].wait(timeout)
        return False
    
    def cleanup_request(self, req_id: int):
        """Clean up request resources"""
        if req_id in self.request_events:
            del self.request_events[req_id]
    
    def set_news_providers(self, providers: List[Any]):
        """Set available news providers"""
        self.news_providers = []
        for provider in providers:
            self.news_providers.append({
                'code': provider.providerCode,
                'name': provider.providerName
            })
        self.providers_loaded = True
        self.logger.info(f"Loaded {len(self.news_providers)} news providers")
    
    def get_news_providers(self) -> List[Dict]:
        """Get available news providers"""
        return self.news_providers.copy()
    
    def export_news_data(self, req_id: int, format_type: str = 'csv') -> Optional[str]:
        """Export news data to file"""
        news_data = self.get_news_data(req_id)
        if not news_data:
            return None
            
        request_info = self.get_request_info(req_id)
        symbol = request_info.get('symbol', 'unknown') if request_info else 'unknown'
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            if format_type.lower() == 'csv':
                df = pd.DataFrame(news_data)
                filename = f"news_{symbol}_{timestamp}.csv"
                filepath = f"data/{filename}"
                df.to_csv(filepath, index=False)
                self.logger.info(f"Exported news data to {filepath}")
                return filepath
                
            elif format_type.lower() == 'json':
                filename = f"news_{symbol}_{timestamp}.json"
                filepath = f"data/{filename}"
                export_data = {
                    'request_info': request_info,
                    'news_items': news_data,
                    'exported_at': datetime.now().isoformat()
                }
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2)
                self.logger.info(f"Exported news data to {filepath}")
                return filepath
                
        except Exception as e:
            self.logger.error(f"Failed to export news data: {e}")
        
        return None
    
    def search_news(self, req_id: int, keyword: str) -> List[Dict]:
        """Search news headlines for a keyword"""
        news_data = self.get_news_data(req_id)
        if not news_data:
            return []
            
        keyword_lower = keyword.lower()
        filtered_news = []
        
        for item in news_data:
            if keyword_lower in item['headline'].lower():
                filtered_news.append(item)
                
        return filtered_news
    
    def get_news_summary(self, req_id: int) -> Dict[str, Any]:
        """Get summary statistics for news data"""
        news_data = self.get_news_data(req_id)
        request_info = self.get_request_info(req_id)
        
        if not news_data:
            return {
                'total_items': 0,
                'providers': [],
                'date_range': None,
                'request_info': request_info
            }
        
        # Extract providers
        providers = list(set(item['provider_code'] for item in news_data))
        
        # Date range
        timestamps = [item['timestamp'] for item in news_data]
        date_range = {
            'earliest': min(timestamps) if timestamps else None,
            'latest': max(timestamps) if timestamps else None
        }
        
        return {
            'total_items': len(news_data),
            'providers': providers,
            'date_range': date_range,
            'request_info': request_info,
            'sample_headlines': [item['headline'] for item in news_data[:3]]
        }


class NewsVisualization:
    """Handles news data visualization and analysis"""
    
    def __init__(self):
        self.logger = setup_logger('NewsVisualization')
    
    def generate_news_chart_data(self, news_data: List[Dict]) -> Dict[str, Any]:
        """Generate data for news visualization charts"""
        if not news_data:
            return {}
        
        # Count news by provider
        provider_counts = {}
        for item in news_data:
            provider = item['provider_code']
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        # Count news by time (hour)
        time_counts = {}
        for item in news_data:
            try:
                # Parse timestamp and group by hour
                dt = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                hour_key = dt.strftime('%Y-%m-%d %H:00')
                time_counts[hour_key] = time_counts.get(hour_key, 0) + 1
            except:
                continue
        
        # Prepare chart data
        chart_data = {
            'provider_distribution': {
                'labels': list(provider_counts.keys()),
                'data': list(provider_counts.values())
            },
            'time_distribution': {
                'labels': sorted(time_counts.keys()),
                'data': [time_counts[label] for label in sorted(time_counts.keys())]
            },
            'total_count': len(news_data),
            'last_update': datetime.now().isoformat()
        }
        
        return chart_data
    
    def generate_sentiment_analysis(self, news_data: List[Dict]) -> Dict[str, Any]:
        """Generate basic sentiment analysis of headlines"""
        if not news_data:
            return {}
        
        # Simple keyword-based sentiment analysis
        positive_keywords = ['up', 'gain', 'rise', 'increase', 'positive', 'growth', 'strong', 'beat', 'exceed']
        negative_keywords = ['down', 'fall', 'decline', 'decrease', 'negative', 'loss', 'weak', 'miss', 'below']
        
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        sentiment_items = {'positive': [], 'negative': [], 'neutral': []}
        
        for item in news_data:
            headline_lower = item['headline'].lower()
            
            positive_score = sum(1 for keyword in positive_keywords if keyword in headline_lower)
            negative_score = sum(1 for keyword in negative_keywords if keyword in headline_lower)
            
            if positive_score > negative_score:
                sentiment = 'positive'
            elif negative_score > positive_score:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            sentiment_counts[sentiment] += 1
            sentiment_items[sentiment].append(item)
        
        return {
            'sentiment_distribution': sentiment_counts,
            'sentiment_items': sentiment_items,
            'total_analyzed': len(news_data)
        }