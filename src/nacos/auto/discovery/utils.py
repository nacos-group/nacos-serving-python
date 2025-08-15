# -*- coding: utf-8 -*-
"""
Utility functions for service discovery
Provides utilities for blacklist handling and exception identification
"""

import logging
import re
import socket
from typing import Optional, Dict, Any, Callable, Union, Tuple
from urllib.parse import urlparse

from .core import ConnectionError

logger = logging.getLogger(__name__)

# Connection error keywords to match
CONNECTION_ERROR_KEYWORDS = [
    'connection refused',
    'connection reset',
    'connection aborted',
    'connect timeout',
    'failed to establish a new connection',
    'no route to host',
    'host unreachable',
    'network is unreachable',
]

# Timeout errors to ignore
IGNORED_TIMEOUT_KEYWORDS = [
    'read timeout',
    'read timed out',
]

def is_connection_error(error: Exception) -> bool:
    """
    Determine if an exception is a connection error
    
    Args:
        error: Exception object
        
    Returns:
        Whether it's a connection error
    """
    # Check exception type first
    if isinstance(error, (socket.error, ConnectionRefusedError, 
                          ConnectionResetError, ConnectionAbortedError)):
        return True
    
    # Convert error to lowercase string for case-insensitive matching
    error_str = str(error).lower()
    
    # Ignore read timeouts
    for keyword in IGNORED_TIMEOUT_KEYWORDS:
        if keyword in error_str:
            return False
    
    # Check for socket timeout separately (it's a common error type)
    if isinstance(error, socket.timeout) and 'socket.timeout' in error_str:
        return True
    
    # Check if error message contains any of the connection error keywords
    for keyword in CONNECTION_ERROR_KEYWORDS:
        if keyword in error_str:
            return True
    
    return False

def extract_host_port(url: str) -> Optional[Tuple[str, int]]:
    """
    Extract host and port from URL
    
    Args:
        url: URL string
        
    Returns:
        (host, port) tuple, or None if parsing fails
    """
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
            
        host = parsed.hostname
        if not host:
            return None
            
        port = parsed.port
        if not port:
            # Use default port
            port = 443 if parsed.scheme == 'https' else 80
            
        return host, port
    except Exception as e:
        logger.debug(f"Failed to parse host and port from URL: {url}, error: {e}")
        return None
