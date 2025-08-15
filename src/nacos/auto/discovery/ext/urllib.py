# -*- coding: utf-8 -*-
"""
urllib Extension
Provides drop-in replacement for urllib.request with Nacos service discovery
"""

import sys
import logging
from urllib.request import *
from urllib.error import *
from urllib.parse import *
from urllib.response import *
from urllib.robotparser import *

from ..core import NoAvailableInstanceError
from ..urllib_ext import ServiceDiscoveryHandler
from .manager import get_discovery_client, DEFAULT_STRATEGY
from ...constants import NAMING_MODULE
from ..error_handlers import handle_connection_errors

logger = logging.getLogger(NAMING_MODULE)

# Original functions we will override
_original_urlopen = urlopen
_original_build_opener = build_opener


def build_opener(*handlers):
    """
    Create an opener object with service discovery capabilities
    
    Args:
        handlers: Handler instances
        
    Returns:
        OpenerDirector object
    """
    try:
        # Get discovery client
        service_discovery = get_discovery_client()
        
        # Add service discovery handler
        sd_handler = ServiceDiscoveryHandler(service_discovery, DEFAULT_STRATEGY)
        all_handlers = [sd_handler]
        if handlers:
            # If additional handlers are provided, extend the list
            all_handlers.extend(handlers)
        
        # Build opener with service discovery
        return _original_build_opener(*all_handlers)
    except Exception as e:
        logger.debug(f"Error in service discovery build_opener: {e}", exc_info=True)
        # Fall back to original build_opener
        return _original_build_opener(*handlers)


default_discovery_opener = build_opener()


@handle_connection_errors
def urlopen(url, *args, **kwargs):
    """
    Open a URL, which can be either a string or a Request object.
    This is a drop-in replacement that supports Nacos service discovery.
    
    Args:
        url: URL to open
        data: Data to send
        timeout: Timeout in seconds
        cafile: CA file
        capath: CA path
        cadefault: Use default CA
        context: SSL context
    
    Returns:
        Response object
    """
    try:
        # Open URL with service discovery
        return default_discovery_opener.open(url, *args, **kwargs)
        
    except NoAvailableInstanceError as e:
        # Convert to URLError for compatibility
        raise URLError(f"No available service instance: {str(e)}")



# Override Request to use our urlopen when opened directly
_original_Request_get_method = Request.get_method
Request.get_method = _original_Request_get_method
