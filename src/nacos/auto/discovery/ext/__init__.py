# -*- coding: utf-8 -*-
"""
Service Discovery Extensions
Provides drop-in replacements for common HTTP libraries with Nacos service discovery
"""

from .manager import (
    configure, get_discovery_client, DEFAULT_STRATEGY, 
    get_blacklist, clear_blacklist, set_blacklist_ttl,
    set_blacklist_probe_interval, set_blacklist_connection_timeout
)
from ..core import LoadBalanceStrategy

__all__ = [
    'configure',
    'get_discovery_client',
    'LoadBalanceStrategy',
    'get_blacklist',
    'clear_blacklist',
    'set_blacklist_ttl',
    'set_blacklist_probe_interval',
    'set_blacklist_connection_timeout'
]
