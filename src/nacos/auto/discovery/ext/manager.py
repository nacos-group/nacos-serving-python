# -*- coding: utf-8 -*-
"""
Global Client Manager
Manages Nacos service discovery clients and configurations
"""

import os
import logging
import asyncio
import threading
from typing import Dict, Any, Optional

from v2.nacos import NacosNamingService, ClientConfigBuilder
from ..core import LoadBalanceStrategy
from ..nacos_discovery import NacosServiceDiscovery
from ....utils.tools import run_async_safely
from ...constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)

# Global state
_discovery_client = None
_discovery_lock = threading.Lock()
_config = None


def configure():
    """
    Configure Nacos service discovery client
    
    Args:
        server_address: Nacos server address
        namespace_id: Namespace ID
        username: Username for authentication
        password: Password for authentication
        cache_ttl: Cache time-to-live in seconds
        log_level: Log level
    """
    global _config
        
    from ...config.loader import ConfigLoader
    _config = ConfigLoader().load_config()
    _config = _config.get('nacos', {})
    
    # Reset client to force re-initialization with new config
    _reset_client()


def _reset_client():
    """Reset the global client"""
    global _discovery_client
    
    _discovery_client = None


async def _init_discovery_client_async() -> NacosServiceDiscovery:
    """Initialize the discovery client asynchronously"""
    global _discovery_client, _config

    # Use default config if not configured
    if _config is None:
        configure()

    discovery_config = _config.get('discovery', {})
    log_config = _config.get('logging', {})
    
    # Create client config
    client_config = (ClientConfigBuilder()
                         .server_address(_config.get('server', 'localhost:8848'))
                         .namespace_id(_config.get('namespace', 'public'))
                         .username(_config.get('username', ''))
                         .password(_config.get('password', ''))
                         .endpoint_query_header({'Request-Module': 'Naming'})
                         .access_key(_config.get('access_key', ''))
                         .secret_key(_config.get('secret_key', ''))
                         .endpoint(_config.get('endpoint', ''))
                         .log_dir(log_config.get('file', ''))
                         # .log_format(log_config.get('format', None))
                         .log_level(log_config.get('level', 'INFO'))
                         .build())
    
    
    # Create naming service client
    nacos_client = await NacosNamingService.create_naming_service(client_config)
    
    # Get blacklist configuration
    blacklist_config = discovery_config.get('blacklist', {})
    blacklist_ttl = blacklist_config.get('ttl', 60)  # Default 60 seconds
    blacklist_probe_interval = blacklist_config.get('probe_interval', 3)  # Default 3 seconds
    blacklist_connection_timeout = blacklist_config.get('connection_timeout', 0.5)  # Default 0.5 seconds
    
    discovery_config.update({
        'namespace_id': _config.get('namespace', 'public'),
        'group_name': _config.get('group', 'DEFAULT_GROUP'),
        'blacklist_ttl': blacklist_ttl,
        'blacklist_probe_interval': blacklist_probe_interval,
        'blacklist_connection_timeout': blacklist_connection_timeout,
    })

    # Create discovery client
    return NacosServiceDiscovery(nacos_client, **discovery_config)


def _init_discovery_client_sync() -> NacosServiceDiscovery:
    """Initialize the discovery client synchronously"""
    return run_async_safely(_init_discovery_client_async)
    


def get_discovery_client() -> NacosServiceDiscovery:
    """
    Get the global discovery client, initializing it if needed
    
    Returns:
        NacosServiceDiscovery client
    """
    global _discovery_client
    
    if _discovery_client is None:
        with _discovery_lock:
            if _discovery_client is not None:
                return _discovery_client
            
            logger.debug("Initializing Nacos service discovery client")
            _discovery_client = _init_discovery_client_sync()
    
    return _discovery_client


def get_blacklist() -> Dict[str, Any]:
    """Get current blacklist"""
    client = get_discovery_client()
    return client.get_blacklist()

def clear_blacklist() -> None:
    """Clear the blacklist"""
    client = get_discovery_client()
    client.clear_blacklist()
    
def set_blacklist_ttl(ttl_seconds: int) -> None:
    """Set blacklist TTL"""
    client = get_discovery_client()
    client.set_blacklist_ttl(ttl_seconds)

def set_blacklist_probe_interval(interval: int) -> None:
    """
    Set blacklist probe interval
    
    Args:
        interval: Probe interval in seconds
    """
    client = get_discovery_client()
    client.set_blacklist_probe_interval(interval)

def set_blacklist_connection_timeout(timeout: float) -> None:
    """
    Set blacklist probe connection timeout
    
    Args:
        timeout: Connection timeout in seconds
    """
    client = get_discovery_client()
    client.set_blacklist_connection_timeout(timeout)


# Default load balancing strategy for all clients
DEFAULT_STRATEGY = LoadBalanceStrategy.ROUND_ROBIN
