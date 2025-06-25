from flask import Flask, render_template, request, jsonify, send_file
import json
import threading
import time
from typing import Dict, Any, List
import pandas as pd

from main import IBKRApp
from config import get_config
from data_handler import DataHandler
from streaming import StreamingDataManager, StreamingVisualization
from news_handler import NewsVisualization
from utils import (
    validate_download_parameters, 
    get_supported_bar_sizes, 
    get_supported_what_to_show,
    get_supported_security_types,
    format_data_summary
)
from logger import setup_logger

app = Flask(__name__)
logger = setup_logger('WebApp')

# Global app instance and status
ibkr_app = None
streaming_manager = StreamingDataManager()
streaming_viz = StreamingVisualization()
news_viz = NewsVisualization()
download_status = {
    'active': False,
    'progress': 0,
    'total': 0,
    'current_symbol': '',
    'results': {},
    'errors': []
}


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/download')
def download_page():
    """Download page"""
    return render_template('download.html', 
                         bar_sizes=get_supported_bar_sizes(),
                         what_to_show_options=get_supported_what_to_show(),
                         security_types=get_supported_security_types())

@app.route('/streaming')
def streaming_page():
    """Real-time streaming page"""
    return render_template('streaming.html',
                         security_types=get_supported_security_types())

@app.route('/analytics')
def analytics_page():
    """Analytics and visualization page"""
    return render_template('analytics.html')

@app.route('/news')
def news_page():
    """News data page"""
    return render_template('news.html')


@app.route('/api/connection/status')
def connection_status():
    """Get connection status"""
    global ibkr_app
    
    if ibkr_app is None:
        return jsonify({'connected': False, 'message': 'Not initialized'})
    
    status = ibkr_app.get_connection_status()
    return jsonify(status)


@app.route('/api/connection/connect', methods=['POST'])
def connect():
    """Connect to IBKR"""
    global ibkr_app
    
    try:
        config = get_config()
        
        # Override config with request parameters if provided
        data = request.get_json() or {}
        if 'host' in data:
            config.host = data['host']
        if 'port' in data:
            config.port = int(data['port'])
        if 'client_id' in data:
            config.client_id = int(data['client_id'])
        
        ibkr_app = IBKRApp(config)
        success = ibkr_app.connect_to_ibkr()
        
        if success:
            # Start streaming analytics engine
            streaming_manager.start_analytics_engine()
            return jsonify({'success': True, 'message': 'Connected successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to connect'})
    
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/connection/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from IBKR"""
    global ibkr_app
    
    try:
        if ibkr_app:
            ibkr_app.disconnect_from_ibkr()
            # Stop streaming analytics
            streaming_manager.stop_analytics_engine()
        return jsonify({'success': True, 'message': 'Disconnected successfully'})
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/download/single', methods=['POST'])
def download_single():
    """Download data for a single symbol"""
    global ibkr_app
    
    if not ibkr_app or not ibkr_app.connected:
        return jsonify({'success': False, 'message': 'Not connected to IBKR'})
    
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()
        
        # Validate parameters
        errors = validate_download_parameters(
            [symbol],
            data.get('duration', '1 Y'),
            data.get('bar_size', '1 day'),
            data.get('sec_type', 'STK'),
            data.get('what_to_show', 'TRADES')
        )
        
        if errors:
            return jsonify({'success': False, 'message': '; '.join(errors)})
        
        # Download data
        df = ibkr_app.request_historical_data(
            symbol=symbol,
            sec_type=data.get('sec_type', 'STK'),
            exchange=data.get('exchange', 'SMART'),
            currency=data.get('currency', 'USD'),
            duration=data.get('duration', '1 Y'),
            bar_size=data.get('bar_size', '1 day'),
            what_to_show=data.get('what_to_show', 'TRADES'),
            use_rth=data.get('use_rth', True)
        )
        
        if df is not None and not df.empty:
            # Save to file
            filename = f"{symbol}_historical_data.csv"
            filepath = ibkr_app.data_handler.save_to_csv(df, filename)
            
            summary = format_data_summary(df, symbol)
            return jsonify({
                'success': True, 
                'message': f'Downloaded {len(df)} records for {symbol}',
                'summary': summary,
                'file': filename
            })
        else:
            return jsonify({'success': False, 'message': f'No data received for {symbol}'})
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/download/multiple', methods=['POST'])
def download_multiple():
    """Download data for multiple symbols"""
    global ibkr_app, download_status
    
    if not ibkr_app or not ibkr_app.connected:
        return jsonify({'success': False, 'message': 'Not connected to IBKR'})
    
    if download_status['active']:
        return jsonify({'success': False, 'message': 'Download already in progress'})
    
    try:
        data = request.get_json()
        symbols_text = data.get('symbols', '')
        symbols = [s.strip().upper() for s in symbols_text.split(',') if s.strip()]
        
        if not symbols:
            return jsonify({'success': False, 'message': 'No symbols provided'})
        
        # Validate parameters
        errors = validate_download_parameters(
            symbols,
            data.get('duration', '1 Y'),
            data.get('bar_size', '1 day'),
            data.get('sec_type', 'STK'),
            data.get('what_to_show', 'TRADES')
        )
        
        if errors:
            return jsonify({'success': False, 'message': '; '.join(errors)})
        
        # Start download in background thread
        def download_worker():
            global download_status
            download_status = {
                'active': True,
                'progress': 0,
                'total': len(symbols),
                'current_symbol': '',
                'results': {},
                'errors': []
            }
            
            try:
                results = {}
                for i, symbol in enumerate(symbols):
                    download_status['current_symbol'] = symbol
                    download_status['progress'] = i
                    
                    df = ibkr_app.request_historical_data(
                        symbol=symbol,
                        sec_type=data.get('sec_type', 'STK'),
                        exchange=data.get('exchange', 'SMART'),
                        currency=data.get('currency', 'USD'),
                        duration=data.get('duration', '1 Y'),
                        bar_size=data.get('bar_size', '1 day'),
                        what_to_show=data.get('what_to_show', 'TRADES'),
                        use_rth=data.get('use_rth', True)
                    )
                    
                    if df is not None and not df.empty:
                        results[symbol] = df
                        download_status['results'][symbol] = format_data_summary(df, symbol)
                    else:
                        download_status['errors'].append(f"No data for {symbol}")
                    
                    time.sleep(0.5)  # Small delay between requests
                
                # Save combined Excel file if requested
                if data.get('save_excel', False) and results:
                    excel_file = ibkr_app.data_handler.save_multiple_to_excel(
                        results, 'historical_data_combined'
                    )
                    download_status['excel_file'] = excel_file
                
                download_status['progress'] = len(symbols)
                download_status['current_symbol'] = 'Complete'
                
            except Exception as e:
                download_status['errors'].append(f"Download error: {e}")
            finally:
                download_status['active'] = False
        
        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Download started'})
    
    except Exception as e:
        logger.error(f"Download multiple error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/download/status')
def download_status_api():
    """Get download status"""
    global download_status
    return jsonify(download_status)


@app.route('/api/files')
def list_files():
    """List available data files"""
    try:
        data_handler = DataHandler()
        csv_files = data_handler.list_files('.csv')
        excel_files = data_handler.list_files('.xlsx')
        
        files = []
        for filename in csv_files + excel_files:
            file_info = data_handler.get_file_info(filename)
            if file_info:
                files.append(file_info)
        
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        logger.error(f"List files error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/files/<filename>')
def download_file(filename):
    """Download a specific file"""
    try:
        data_handler = DataHandler()
        filepath = data_handler.get_file_info(filename)
        
        if filepath and 'filepath' in filepath:
            return send_file(filepath['filepath'], as_attachment=True)
        else:
            return jsonify({'success': False, 'message': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Download file error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# Real-time streaming API endpoints
@app.route('/api/streaming/start', methods=['POST'])
def start_streaming():
    """Start real-time data streaming for a symbol"""
    global ibkr_app, streaming_manager
    
    if not ibkr_app or not ibkr_app.connected:
        return jsonify({'success': False, 'message': 'Not connected to IBKR'})
    
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()
        sec_type = data.get('sec_type', 'STK')
        exchange = data.get('exchange', 'SMART')
        currency = data.get('currency', 'USD')
        
        if not symbol:
            return jsonify({'success': False, 'message': 'Symbol is required'})
        
        # Create callback to add data to streaming manager
        def stream_callback(tick_data):
            streaming_manager.add_tick_data(tick_data['reqId'], tick_data)
        
        # Start streaming
        req_id = ibkr_app.start_real_time_data(symbol, sec_type, exchange, currency, stream_callback)
        
        if req_id > 0:
            # Register with streaming manager
            streaming_manager.register_stream(req_id, symbol, sec_type)
            return jsonify({
                'success': True, 
                'message': f'Started streaming for {symbol}',
                'req_id': req_id
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to start streaming'})
    
    except Exception as e:
        logger.error(f"Start streaming error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/streaming/stop', methods=['POST'])
def stop_streaming():
    """Stop real-time data streaming"""
    global ibkr_app, streaming_manager
    
    if not ibkr_app:
        return jsonify({'success': False, 'message': 'Not connected to IBKR'})
    
    try:
        data = request.get_json()
        req_id = data.get('req_id')
        
        if req_id is None:
            return jsonify({'success': False, 'message': 'Request ID is required'})
        
        ibkr_app.stop_real_time_data(req_id)
        streaming_manager.unregister_stream(req_id)
        
        return jsonify({'success': True, 'message': 'Stopped streaming'})
    
    except Exception as e:
        logger.error(f"Stop streaming error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/streaming/data/<int:req_id>')
def get_streaming_data(req_id):
    """Get recent streaming data for a request ID"""
    try:
        limit = request.args.get('limit', 100, type=int)
        data = streaming_manager.get_stream_data(req_id, limit)
        analytics = streaming_manager.get_stream_analytics(req_id)
        
        return jsonify({
            'success': True,
            'data': data,
            'analytics': analytics
        })
    
    except Exception as e:
        logger.error(f"Get streaming data error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/streaming/dashboard')
def streaming_dashboard():
    """Get dashboard data for all active streams"""
    try:
        all_streams = streaming_manager.get_all_streams()
        dashboard_data = streaming_viz.generate_dashboard_data(all_streams, streaming_manager)
        
        return jsonify({
            'success': True,
            'dashboard': dashboard_data
        })
    
    except Exception as e:
        logger.error(f"Streaming dashboard error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/streaming/chart/<int:req_id>')
def get_chart_data(req_id):
    """Get chart data for a specific stream"""
    try:
        stream_data = streaming_manager.get_stream_data(req_id, 200)
        analytics = streaming_manager.get_stream_analytics(req_id)
        chart_data = streaming_viz.generate_chart_data(stream_data, analytics)
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
    
    except Exception as e:
        logger.error(f"Get chart data error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/streaming/export/<int:req_id>')
def export_streaming_data(req_id):
    """Export streaming data to file"""
    try:
        format_type = request.args.get('format', 'csv')
        filepath = streaming_manager.export_stream_data(req_id, format_type)
        
        if filepath:
            return jsonify({
                'success': True,
                'message': f'Data exported to {filepath}',
                'filepath': filepath
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to export data'})
    
    except Exception as e:
        logger.error(f"Export streaming data error: {e}")
        return jsonify({'success': False, 'message': str(e)})


# News API endpoints
@app.route('/api/news/providers')
def get_news_providers():
    """Get available news providers"""
    global ibkr_app
    
    if not ibkr_app or not ibkr_app.connected:
        return jsonify({'success': False, 'message': 'Not connected to IBKR'})
    
    try:
        # Request providers if not already loaded
        if not ibkr_app.news_manager.providers_loaded:
            ibkr_app.request_news_providers()
            time.sleep(2)  # Wait for response
        
        providers = ibkr_app.news_manager.get_news_providers()
        return jsonify({
            'success': True,
            'providers': providers
        })
    
    except Exception as e:
        logger.error(f"Get news providers error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/request', methods=['POST'])
def request_historical_news():
    """Request historical news for a symbol"""
    global ibkr_app
    
    if not ibkr_app or not ibkr_app.connected:
        return jsonify({'success': False, 'message': 'Not connected to IBKR'})
    
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()
        con_id = data.get('con_id')
        provider_codes = data.get('provider_codes', '')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        total_results = data.get('total_results', 10)
        
        if not symbol:
            return jsonify({'success': False, 'message': 'Symbol is required'})
        
        news_data = ibkr_app.request_historical_news(
            symbol=symbol,
            con_id=con_id,
            provider_codes=provider_codes,
            start_date=start_date,
            end_date=end_date,
            total_results=total_results
        )
        
        if news_data is not None:
            # Get the request ID from the last news request
            req_ids = list(ibkr_app.news_manager.news_requests.keys())
            req_id = max(req_ids) if req_ids else None
            
            summary = ibkr_app.news_manager.get_news_summary(req_id) if req_id else {}
            
            return jsonify({
                'success': True,
                'message': f'Retrieved {len(news_data)} news items for {symbol}',
                'req_id': req_id,
                'news_data': news_data,
                'summary': summary
            })
        else:
            return jsonify({'success': False, 'message': f'No news data received for {symbol}'})
    
    except Exception as e:
        logger.error(f"Request news error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/data/<int:req_id>')
def get_news_data(req_id):
    """Get news data for a request ID"""
    global ibkr_app
    
    if not ibkr_app:
        return jsonify({'success': False, 'message': 'Application not initialized'})
    
    try:
        news_data = ibkr_app.news_manager.get_news_data(req_id)
        summary = ibkr_app.news_manager.get_news_summary(req_id)
        
        return jsonify({
            'success': True,
            'news_data': news_data,
            'summary': summary
        })
    
    except Exception as e:
        logger.error(f"Get news data error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/search/<int:req_id>')
def search_news(req_id):
    """Search news headlines for a keyword"""
    global ibkr_app
    
    if not ibkr_app:
        return jsonify({'success': False, 'message': 'Application not initialized'})
    
    try:
        keyword = request.args.get('keyword', '')
        if not keyword:
            return jsonify({'success': False, 'message': 'Keyword is required'})
        
        filtered_news = ibkr_app.news_manager.search_news(req_id, keyword)
        
        return jsonify({
            'success': True,
            'keyword': keyword,
            'results': filtered_news,
            'total_found': len(filtered_news)
        })
    
    except Exception as e:
        logger.error(f"Search news error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/chart/<int:req_id>')
def get_news_chart_data(req_id):
    """Get chart data for news visualization"""
    global ibkr_app, news_viz
    
    if not ibkr_app:
        return jsonify({'success': False, 'message': 'Application not initialized'})
    
    try:
        news_data = ibkr_app.news_manager.get_news_data(req_id)
        chart_data = news_viz.generate_news_chart_data(news_data)
        sentiment_data = news_viz.generate_sentiment_analysis(news_data)
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'sentiment_data': sentiment_data
        })
    
    except Exception as e:
        logger.error(f"Get news chart data error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/export/<int:req_id>')
def export_news_data(req_id):
    """Export news data to file"""
    global ibkr_app
    
    if not ibkr_app:
        return jsonify({'success': False, 'message': 'Application not initialized'})
    
    try:
        format_type = request.args.get('format', 'csv')
        filepath = ibkr_app.news_manager.export_news_data(req_id, format_type)
        
        if filepath:
            return jsonify({
                'success': True,
                'message': f'News data exported to {filepath}',
                'filepath': filepath
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to export news data'})
    
    except Exception as e:
        logger.error(f"Export news data error: {e}")
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
