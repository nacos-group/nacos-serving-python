# -*- coding: utf-8 -*-
"""
Error Handling Utilities
Provides common error handling mechanisms for service discovery
"""

import logging
import functools
import sys
from typing import Callable, Any, Optional, TypeVar, Union, Awaitable

from .utils import is_connection_error, extract_host_port
from .nacos_discovery import NacosServiceDiscovery
from .ext.manager import get_discovery_client
from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)

F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Awaitable[Any]])

def handle_connection_errors(func: F) -> F:
    """
    Decorator to handle connection errors and add failed hosts to blacklist
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Process connection errors
            _process_error(e, sys.exc_info(), args[0])
            # Re-raise the exception
            raise
    return wrapper  # type: ignore


def handle_async_connection_errors(func: AsyncF) -> AsyncF:
    """
    Decorator to handle connection errors in async functions and add failed hosts to blacklist
    
    Args:
        func: Async function to decorate
        
    Returns:
        Decorated async function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Process connection errors
            
            _process_error(e, *args, **kwargs)
            # Re-raise the exception
            raise
    return wrapper  # type: ignore


def _process_error(error: Exception, *args, **kwargs) -> None:
    """
    Process error and add to blacklist if it's a connection error
    
    Args:
        error: Exception object
        exe_info: Exception info from sys.exc_info()
    """
    if not is_connection_error(error):
        return

    exe_info = sys.exc_info()
    # Try to get the request and service discovery client
    address = _deep_peek_address_from_exec(exe_info)
    if address:
        host, port = address
        # Try to get URL from various sources
        get_discovery_client().add_to_blacklist(host, port)   
        logger.warning(f"Connection error detected: {host}:{port}, adding to blacklist. Error: {error}") 
    else:
        logger.debug("No address found in exception info, cannot add to blacklist")
def _deep_peek_address_from_exec(exe_info):
    """
    Try to extract host and port from the exception info.
    
    Args:
        exe_info: Exception info from sys.exc_info()
    """

    def parse_locals(frame):
        locals = frame.f_locals

        if 'req' in locals:
            req = locals['req']
            if hasattr(req, 'full_url'):
                return extract_host_port(req.full_url) 
            if hasattr(req, 'url'):
                return extract_host_port(req.url)
            if hasattr(req, 'host'):
                return extract_host_port(req.host)

        if 'address' in locals:
            address = locals['address']
            return address if isinstance(address, tuple) else None
        
        return None
    
    _, _, tb = exe_info
    while tb:
        frame = tb.tb_frame
        host_port = parse_locals(frame)
        if host_port:
            return host_port
        
        tb = tb.tb_next

    return None