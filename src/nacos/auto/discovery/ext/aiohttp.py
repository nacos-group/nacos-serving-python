# -*- coding: utf-8 -*-
"""
aiohttp Extension
Provides drop-in replacement for aiohttp module with Nacos service discovery
"""

import logging

# Import all from aiohttp
try:
    import aiohttp
except ImportError:
    raise ImportError("aiohttp module is required for nacos.auto.discovery.ext.aiohttp")

from ..aiohttp_ext import ServiceDiscoveryClientSession
from ...constants import NAMING_MODULE
from .manager import get_discovery_client, DEFAULT_STRATEGY

logger = logging.getLogger(NAMING_MODULE)

# Original functions and classes we will override


class ClientSession(aiohttp.ClientSession):
    """Client session with service discovery support"""
    
    def __init__(self, **kwargs):
        try:
            # Get discovery client
            service_discovery = get_discovery_client()
            
            # Extract strategy
            strategy = kwargs.pop('strategy', DEFAULT_STRATEGY)
            
            # Create service discovery session
            super().__init__(**kwargs)
            
            # Store original _request method
            self._original_request = self._request
            
            # Access resolver through composition because we can't easily inherit
            # from ServiceDiscoveryClientSession (already inherits from aiohttp.ClientSession)
            self._sd_session = ServiceDiscoveryClientSession(
                service_discovery, 
                strategy=strategy
            )
            
            # Replace _request method with service discovery version
            self._request = self._sd_request
            
        except Exception as e:
            logger.debug(f"Error initializing service discovery session: {e}", exc_info=True)
            # Fall back to original ClientSession
            super().__init__(**kwargs)
    
    async def _sd_request(self, method, url, **kwargs):
        """Request method with service discovery"""
        try:
            # Use the resolver from ServiceDiscoveryClientSession
            str_url = str(url)
            resolved_url = await self._sd_session.resolver.resolve_url_async(
                str_url, 
                strategy=self._sd_session.strategy
            )
            
            # If URL is resolved (service discovery), update URL
            if resolved_url != str_url:
                logger.debug(f"Service discovery: {str_url} -> {resolved_url}")
                url = resolved_url
            
        except Exception as e:
            logger.debug(f"Error in service discovery resolution: {e}", exc_info=True)
        
        # Call original _request with possibly resolved URL
        return await self._original_request(method, url, **kwargs)


# Override the module's original classes with our versions
__all__ = ["ClientSession"]