# -*- coding: utf-8 -*-
"""
aiohttp Extension
Provides service discovery capability for aiohttp library
"""

import logging
import asyncio
from typing import Dict, Union, Optional, Any, Callable, List, Tuple

import aiohttp
from aiohttp.client import ClientSession
from aiohttp.typedefs import StrOrURL

from .nacos_discovery import NacosServiceDiscovery
from .url_resolver import ServiceUrlResolver
from .core import LoadBalanceStrategy
from .error_handlers import handle_async_connection_errors

logger = logging.getLogger(__name__)


class ServiceDiscoveryClientSession(aiohttp.ClientSession):
    """Service discovery client session"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery,
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 **kwargs):
        """
        Initialize service discovery client session
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
            kwargs: Other parameters passed to ClientSession
        """
        super().__init__(**kwargs)
        self.service_discovery = service_discovery
        self.resolver = ServiceUrlResolver(service_discovery)
        self.strategy = strategy
    
    @handle_async_connection_errors
    async def _request(self, method: str, url: StrOrURL, **kwargs) -> aiohttp.ClientResponse:
        """
        Process request
        
        Args:
            method: HTTP method
            url: URL
            kwargs: Other parameters
            
        Returns:
            Response object
        """
        # Resolve service URL
        str_url = str(url)
        resolved_url = await self.resolver.resolve_url_async(str_url, strategy=self.strategy)
        
        # If URL is resolved (service discovery), update URL
        if resolved_url != str_url:
            logger.debug(f"Service discovery: {str_url} -> {resolved_url}")
            url = resolved_url
        
        # Send request
        return await super()._request(method, url, **kwargs)


# Alias to maintain consistency with other libraries
ServiceDiscoverySession = ServiceDiscoveryClientSession


def create_service_discovery_session(service_discovery: NacosServiceDiscovery,
                                   strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                                   **kwargs) -> ServiceDiscoveryClientSession:
    """
    Create a client session with service discovery support
    
    Args:
        service_discovery: Service discovery object
        strategy: Load balancing strategy
        kwargs: Other parameters
        
    Returns:
        Service discovery client session
    """
    return ServiceDiscoveryClientSession(service_discovery, strategy=strategy, **kwargs)
