# -*- coding: utf-8 -*-
"""
httpx Extension
Provides service discovery capability for httpx library
"""

import logging
from typing import Dict, Union, Optional, Any, Callable

import httpx
from httpx._types import URLTypes, AuthTypes, HeaderTypes, CookieTypes
from httpx._transports.base import BaseTransport
from httpx._models import Request, Response

from .nacos_discovery import NacosServiceDiscovery
from .url_resolver import ServiceUrlResolver
from .core import LoadBalanceStrategy
from .utils import is_connection_error, extract_host_port
from .error_handlers import handle_connection_errors, handle_async_connection_errors

logger = logging.getLogger(__name__)


class ServiceDiscoveryTransport(BaseTransport):
    """Service discovery transport layer"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery,
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 inner_transport: Optional[BaseTransport] = None):
        """
        Initialize service discovery transport layer
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
            inner_transport: Inner transport object
        """
        self.resolver = ServiceUrlResolver(service_discovery)
        self.strategy = strategy
        self.service_discovery = service_discovery
        self.inner_transport = inner_transport or httpx.HTTPTransport()
    
    @handle_connection_errors
    def handle_request(self, request: Request) -> Response:
        """
        Process request
        
        Args:
            request: Request object
            
        Returns:
            Response object
        """
        # Resolve service URL
        url = str(request.url)
        resolved_url = self.resolver.resolve_url(url, strategy=self.strategy)
        
        # If URL is resolved (service discovery), update the request
        if resolved_url != url:
            logger.debug(f"Service discovery: {url} -> {resolved_url}")
            request.url = httpx.URL(resolved_url)
        
        # Use inner transport to process the request
        return self.inner_transport.handle_request(request)
    
    def close(self) -> None:
        """Close transport layer"""
        if hasattr(self.inner_transport, 'close'):
            self.inner_transport.close()


class AsyncServiceDiscoveryTransport(httpx.AsyncBaseTransport):
    """Async service discovery transport layer"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery,
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 inner_transport: Optional[httpx.AsyncBaseTransport] = None):
        """
        Initialize async service discovery transport layer
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
            inner_transport: Inner transport object
        """
        self.service_discovery = service_discovery
        self.resolver = ServiceUrlResolver(service_discovery)
        self.strategy = strategy
        self.inner_transport = inner_transport or httpx.AsyncHTTPTransport()
    
    @handle_async_connection_errors
    async def handle_async_request(self, request: Request) -> Response:
        """
        Asynchronously process request
        
        Args:
            request: Request object
            
        Returns:
            Response object
        """
        # Resolve service URL
        url = str(request.url)
        resolved_url = await self.resolver.resolve_url_async(url, strategy=self.strategy)
        
        # If URL is resolved (service discovery), update the request
        if resolved_url != url:
            logger.debug(f"Service discovery: {url} -> {resolved_url}")
            request.url = httpx.URL(resolved_url)
        
        # Use inner transport to process the request
        return await self.inner_transport.handle_async_request(request)
    
    async def aclose(self) -> None:
        """Close async transport layer"""
        if hasattr(self.inner_transport, 'aclose'):
            await self.inner_transport.aclose()


class ServiceDiscoveryClient(httpx.Client):
    """Service discovery client"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery,
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 **kwargs):
        """
        Initialize service discovery client
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
            kwargs: Other parameters
        """
        transport = kwargs.pop('transport', None)
        sd_transport = ServiceDiscoveryTransport(
            service_discovery, 
            strategy=strategy,
            inner_transport=transport
        )
        super().__init__(transport=sd_transport, **kwargs)


class AsyncServiceDiscoveryClient(httpx.AsyncClient):
    """Async service discovery client"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery,
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 **kwargs):
        """
        Initialize async service discovery client
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
            kwargs: Other parameters
        """
        transport = kwargs.pop('transport', None)
        sd_transport = AsyncServiceDiscoveryTransport(
            service_discovery, 
            strategy=strategy,
            inner_transport=transport
        )
        super().__init__(transport=sd_transport, **kwargs)
