from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from ibapi.contract import Contract
from logger import setup_logger

logger = setup_logger('Utils')


def create_contract(symbol: str, sec_type: str = "STK", exchange: str = "SMART", currency: str = "USD") -> Contract:
    """
    Create an IBKR contract object
    
    Args:
        symbol: Trading symbol
        sec_type: Security type (STK, FUT, OPT, CASH, etc.)
        exchange: Exchange
        currency: Currency
        
    Returns:
        Contract: IBKR contract object
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.exchange = exchange
    contract.currency = currency
    
    logger.debug(f"Created contract: {symbol} {sec_type} {exchange} {currency}")
    return contract


def format_datetime(dt: datetime, format_str: str = "%Y%m%d %H:%M:%S") -> str:
    """
    Format datetime for IBKR API
    
    Args:
        dt: Datetime object
        format_str: Format string
        
    Returns:
        str: Formatted datetime string
    """
    return dt.strftime(format_str)


def parse_duration_string(duration_str: str) -> timedelta:
    """
    Parse IBKR duration string to timedelta
    
    Args:
        duration_str: Duration string like "1 Y", "6 M", "30 D"
        
    Returns:
        timedelta: Parsed duration
    """
    parts = duration_str.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Invalid duration string: {duration_str}")
    
    value, unit = parts
    value = int(value)
    
    unit = unit.upper()
    if unit in ['Y', 'YEAR', 'YEARS']:
        return timedelta(days=value * 365)
    elif unit in ['M', 'MONTH', 'MONTHS']:
        return timedelta(days=value * 30)
    elif unit in ['W', 'WEEK', 'WEEKS']:
        return timedelta(weeks=value)
    elif unit in ['D', 'DAY', 'DAYS']:
        return timedelta(days=value)
    elif unit in ['H', 'HOUR', 'HOURS']:
        return timedelta(hours=value)
    else:
        raise ValueError(f"Unknown duration unit: {unit}")


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format
    
    Args:
        symbol: Trading symbol
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Basic validation: alphanumeric characters, dots, hyphens
    import re
    pattern = r'^[A-Za-z0-9.-]+$'
    return bool(re.match(pattern, symbol.strip()))


def get_supported_bar_sizes() -> List[str]:
    """
    Get list of supported bar sizes for IBKR API
    
    Returns:
        List[str]: List of supported bar sizes
    """
    return [
        "1 sec", "5 secs", "10 secs", "15 secs", "30 secs",
        "1 min", "2 mins", "3 mins", "5 mins", "10 mins", "15 mins", "20 mins", "30 mins",
        "1 hour", "2 hours", "3 hours", "4 hours", "8 hours",
        "1 day", "1 week", "1 month"
    ]


def get_supported_what_to_show() -> List[str]:
    """
    Get list of supported 'what to show' options for IBKR API
    
    Returns:
        List[str]: List of supported options
    """
    return [
        "TRADES", "MIDPOINT", "BID", "ASK", "BID_ASK",
        "HISTORICAL_VOLATILITY", "OPTION_IMPLIED_VOLATILITY",
        "REBATE_RATE", "FEE_RATE", "YIELD_BID", "YIELD_ASK", "YIELD_BID_ASK", "YIELD_LAST"
    ]


def get_supported_security_types() -> List[str]:
    """
    Get list of supported security types
    
    Returns:
        List[str]: List of supported security types
    """
    return ["STK", "OPT", "FUT", "CASH", "BOND", "CFD", "FUND", "NEWS"]


def calculate_data_points(duration: str, bar_size: str) -> Optional[int]:
    """
    Estimate number of data points for given duration and bar size
    
    Args:
        duration: Duration string
        bar_size: Bar size string
        
    Returns:
        int: Estimated number of data points or None if can't calculate
    """
    try:
        duration_td = parse_duration_string(duration)
        duration_seconds = duration_td.total_seconds()
        
        # Parse bar size to seconds
        bar_parts = bar_size.strip().split()
        if len(bar_parts) != 2:
            return None
        
        value, unit = bar_parts
        value = int(value)
        unit = unit.lower()
        
        if unit in ['sec', 'secs', 'second', 'seconds']:
            bar_seconds = value
        elif unit in ['min', 'mins', 'minute', 'minutes']:
            bar_seconds = value * 60
        elif unit in ['hour', 'hours']:
            bar_seconds = value * 3600
        elif unit in ['day', 'days']:
            bar_seconds = value * 86400
        elif unit in ['week', 'weeks']:
            bar_seconds = value * 604800
        elif unit in ['month', 'months']:
            bar_seconds = value * 2628000  # Approximate
        else:
            return None
        
        return int(duration_seconds / bar_seconds)
    
    except Exception as e:
        logger.warning(f"Failed to calculate data points: {e}")
        return None


def format_data_summary(data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """
    Create a summary of downloaded data
    
    Args:
        data: DataFrame with historical data
        symbol: Trading symbol
        
    Returns:
        Dict[str, Any]: Data summary
    """
    if data.empty:
        return {
            'symbol': symbol,
            'records': 0,
            'start_date': None,
            'end_date': None,
            'columns': []
        }
    
    return {
        'symbol': symbol,
        'records': len(data),
        'start_date': data.index.min().isoformat() if hasattr(data.index, 'min') else None,
        'end_date': data.index.max().isoformat() if hasattr(data.index, 'max') else None,
        'columns': data.columns.tolist(),
        'sample_data': data.head(3).to_dict('records') if len(data) > 0 else []
    }


def validate_download_parameters(symbols: List[str], duration: str, bar_size: str, 
                               sec_type: str, what_to_show: str) -> List[str]:
    """
    Validate download parameters and return list of validation errors
    
    Args:
        symbols: List of symbols
        duration: Duration string
        bar_size: Bar size string
        sec_type: Security type
        what_to_show: What to show
        
    Returns:
        List[str]: List of validation errors (empty if all valid)
    """
    errors = []
    
    # Validate symbols
    if not symbols:
        errors.append("No symbols provided")
    else:
        for symbol in symbols:
            if not validate_symbol(symbol):
                errors.append(f"Invalid symbol format: {symbol}")
    
    # Validate bar size
    if bar_size not in get_supported_bar_sizes():
        errors.append(f"Unsupported bar size: {bar_size}")
    
    # Validate security type
    if sec_type not in get_supported_security_types():
        errors.append(f"Unsupported security type: {sec_type}")
    
    # Validate what to show
    if what_to_show not in get_supported_what_to_show():
        errors.append(f"Unsupported what to show: {what_to_show}")
    
    # Validate duration format
    try:
        parse_duration_string(duration)
    except ValueError as e:
        errors.append(f"Invalid duration: {e}")
    
    return errors
