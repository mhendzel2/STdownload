import os
import json
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class IBKRConfig:
    """Configuration class for IBKR connection and data requests"""
    
    # Connection settings
    host: str = "127.0.0.1"
    port: int = 7497  # TWS demo port (7496 for live)
    client_id: int = 1
    
    # Timeout settings (in seconds)
    connection_timeout: int = 30
    data_timeout: int = 60
    
    # Rate limiting
    request_delay: float = 1.0  # Delay between requests in seconds
    
    # Data settings
    default_duration: str = "1 Y"
    default_bar_size: str = "1 day"
    default_what_to_show: str = "TRADES"
    default_use_rth: bool = True
    
    @classmethod
    def from_env(cls) -> 'IBKRConfig':
        """Create configuration from environment variables"""
        return cls(
            host=os.getenv("IBKR_HOST", "127.0.0.1"),
            port=int(os.getenv("IBKR_PORT", "7497")),
            client_id=int(os.getenv("IBKR_CLIENT_ID", "1")),
            connection_timeout=int(os.getenv("IBKR_CONNECTION_TIMEOUT", "30")),
            data_timeout=int(os.getenv("IBKR_DATA_TIMEOUT", "60")),
            request_delay=float(os.getenv("IBKR_REQUEST_DELAY", "1.0")),
            default_duration=os.getenv("IBKR_DEFAULT_DURATION", "1 Y"),
            default_bar_size=os.getenv("IBKR_DEFAULT_BAR_SIZE", "1 day"),
            default_what_to_show=os.getenv("IBKR_DEFAULT_WHAT_TO_SHOW", "TRADES"),
            default_use_rth=os.getenv("IBKR_DEFAULT_USE_RTH", "true").lower() == "true"
        )
    
    @classmethod
    def from_file(cls, filepath: str) -> 'IBKRConfig':
        """Load configuration from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except FileNotFoundError:
            # Return default config if file doesn't exist
            return cls()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file {filepath}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'host': self.host,
            'port': self.port,
            'client_id': self.client_id,
            'connection_timeout': self.connection_timeout,
            'data_timeout': self.data_timeout,
            'request_delay': self.request_delay,
            'default_duration': self.default_duration,
            'default_bar_size': self.default_bar_size,
            'default_what_to_show': self.default_what_to_show,
            'default_use_rth': self.default_use_rth
        }
    
    def save_to_file(self, filepath: str):
        """Save configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# Predefined configurations for different environments
DEMO_CONFIG = IBKRConfig(
    host="127.0.0.1",
    port=7497,  # TWS demo port
    client_id=1
)

LIVE_CONFIG = IBKRConfig(
    host="127.0.0.1",
    port=7496,  # TWS live port
    client_id=1
)

GATEWAY_DEMO_CONFIG = IBKRConfig(
    host="127.0.0.1",
    port=4002,  # Gateway demo port
    client_id=1
)

GATEWAY_LIVE_CONFIG = IBKRConfig(
    host="127.0.0.1",
    port=4001,  # Gateway live port
    client_id=1
)


def get_config() -> IBKRConfig:
    """Get configuration with priority: env vars -> config file -> defaults"""
    # First try to load from environment variables
    config = IBKRConfig.from_env()
    
    # If config file exists, merge with it
    config_file = os.getenv("IBKR_CONFIG_FILE", "config.json")
    if os.path.exists(config_file):
        file_config = IBKRConfig.from_file(config_file)
        # Environment variables take precedence
        for key, value in file_config.to_dict().items():
            if not hasattr(config, key) or getattr(config, key) == getattr(IBKRConfig(), key):
                setattr(config, key, value)
    
    return config
