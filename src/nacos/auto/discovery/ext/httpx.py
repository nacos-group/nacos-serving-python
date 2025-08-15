# -*- coding: utf-8 -*-
"""
httpx Extension
Provides drop-in replacement for httpx module with Nacos service discovery
"""

import logging

# Import all from httpx
try:
    import httpx
except ImportError:
    raise ImportError("httpx module is required for" \
    " nacos.auto.discovery.ext.httpx")

from ..httpx_ext import (
    ServiceDiscoveryClient, 
    AsyncServiceDiscoveryClient,
    ServiceDiscoveryTransport, 
    AsyncServiceDiscoveryTransport
)
from .manager import get_discovery_client, DEFAULT_STRATEGY
from ...constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


def _create_service_discovery_client(**kwargs):
    """Create a HTTPX client with service discovery"""
    try:
        service_discovery = get_discovery_client()
        return ServiceDiscoveryClient(
            service_discovery, 
            strategy=DEFAULT_STRATEGY,
            **kwargs
        )
    except Exception as e:
        logger.debug(f"Error creating service discovery httpx client: {e}", exc_info=True)
        return httpx.Client(**kwargs)

def request(method, url, **kwargs):
    """
    Send a request using Nacos service discovery
    
    Args:
        method: HTTP method
        url: URL to send request to
        kwargs: Additional arguments to pass to httpx
        
    Returns:
        Response object
    """
    with _create_service_discovery_client() as client:
        return client.request(method, url, **kwargs)


def get(url, **kwargs):
    """GET request with service discovery"""
    return request('GET', url, **kwargs)


def post(url, **kwargs):
    """POST request with service discovery"""
    return request('POST', url, **kwargs)


def put(url, **kwargs):
    """PUT request with service discovery"""
    return request('PUT', url, **kwargs)


def patch(url, **kwargs):
    """PATCH request with service discovery"""
    return request('PATCH', url, **kwargs)


def delete(url, **kwargs):
    """DELETE request with service discovery"""
    return request('DELETE', url, **kwargs)


def head(url, **kwargs):
    """HEAD request with service discovery"""
    return request('HEAD', url, **kwargs)


def options(url, **kwargs):
    """OPTIONS request with service discovery"""
    return request('OPTIONS', url, **kwargs)


def stream(method, url, **kwargs):
    """Stream request with service discovery"""
    client = _create_service_discovery_client()
    return client.stream(method, url, **kwargs)


class Client(httpx.Client):
    """Client with service discovery support"""
    
    def __init__(self, **kwargs):
        # Extract service discovery parameters
        service_discovery = get_discovery_client()
        transport = kwargs.pop('transport', None)
        strategy = kwargs.pop('strategy', DEFAULT_STRATEGY)
        
        # Create service discovery transport
        sd_transport = ServiceDiscoveryTransport(
            service_discovery,
            strategy=strategy,
            inner_transport=transport
        )
        
        # Initialize with service discovery transport
        super().__init__(transport=sd_transport, **kwargs)


class AsyncClient(httpx.AsyncClient):
    """Async client with service discovery support"""
    
    def __init__(self, **kwargs):
        # Extract service discovery parameters
        service_discovery = get_discovery_client()
        transport = kwargs.pop('transport', None)
        strategy = kwargs.pop('strategy', DEFAULT_STRATEGY)
        
        # Create service discovery transport
        sd_transport = AsyncServiceDiscoveryTransport(
            service_discovery,
            strategy=strategy,
            inner_transport=transport
        )
        
        # Initialize with service discovery transport
        super().__init__(transport=sd_transport, **kwargs)


# Override the module's original functions and classes with our versions
__all__ = ["request", 
           "get", 
           "post", 
           "put", 
           "patch", 
           "delete", 
           "head", 
           "options", 
           "stream", 
           "Client", 
           "AsyncClient"]

