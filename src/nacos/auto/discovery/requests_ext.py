# -*- coding: utf-8 -*-
"""
requests Extension
Provides service discovery capability for requests library
"""

import logging
from typing import Dict, Union, Optional, Any, Callable

import requests
from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest
from urllib.parse import urlparse, urlunparse

from .nacos_discovery import NacosServiceDiscovery
from .url_resolver import ServiceUrlResolver
from .core import LoadBalanceStrategy
from .utils import is_connection_error, extract_host_port
from .error_handlers import handle_connection_errors

logger = logging.getLogger(__name__)


class ServiceDiscoveryAdapter(HTTPAdapter):
    """Service discovery adapter"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery,
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 **kwargs):
        """
        Initialize service discovery adapter
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
            kwargs: Other parameters passed to HTTPAdapter
        """
        super().__init__(**kwargs)
        self.resolver = ServiceUrlResolver(service_discovery)
        self.strategy = strategy
        self.service_discovery = service_discovery
    
    @handle_connection_errors
    def send(self, request: PreparedRequest, **kwargs) -> requests.Response:
        """
        Send request
        
        Args:
            request: Prepared request
            kwargs: Other parameters
            
        Returns:
            Response object
        """
        # Resolve service URL
        url = request.url
        resolved_url = self.resolver.resolve_url(url, strategy=self.strategy)
        
        # If URL is resolved (service discovery), update the request
        if resolved_url != url:
            logger.debug(f"Service discovery: {url} -> {resolved_url}")
            request.url = resolved_url
            
            # Store original URL for error handling to identify service name
            request.service_url = url
        
        return super().send(request, **kwargs)


class ServiceDiscoverySession(requests.Session):
    """Service discovery session"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery,
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 max_retries: int = None,
                 timeout: Union[float, tuple] = None,
                 **kwargs):
        """
        Initialize service discovery session
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
            max_retries: Maximum number of retries
            timeout: Timeout setting
            kwargs: Other parameters
        """
        super().__init__()
        
        # Create adapter
        adapter_kwargs = {}
        if max_retries is not None:
            adapter_kwargs['max_retries'] = max_retries
        
        adapter = ServiceDiscoveryAdapter(service_discovery, strategy, **adapter_kwargs)
        
        # Mount adapter
        self.mount('http://', adapter)
        self.mount('https://', adapter)
        
        # Set default timeout
        self.timeout = timeout or 30
    
    def request(self, method, url, **kwargs):
        """
        Send request
        
        Args:
            method: HTTP method
            url: URL
            kwargs: Other parameters
            
        Returns:
            Response object
        """
        # Ensure timeout is set
        timeout = kwargs.get('timeout')
        if timeout is None:
            kwargs['timeout'] = self.timeout
        
        return super().request(method, url, **kwargs)


def mount_service_discovery(session: requests.Session, 
                           service_discovery: NacosServiceDiscovery,
                           strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                           max_retries: int = None) -> requests.Session:
    """
    Mount service discovery adapter to session
    
    Args:
        session: Session object
        service_discovery: Service discovery object
        strategy: Load balancing strategy
        max_retries: Maximum number of retries
        
    Returns:
        Session object
    """
    adapter_kwargs = {}
    if max_retries is not None:
        adapter_kwargs['max_retries'] = max_retries
    
    adapter = ServiceDiscoveryAdapter(service_discovery, strategy, **adapter_kwargs)
    
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session
