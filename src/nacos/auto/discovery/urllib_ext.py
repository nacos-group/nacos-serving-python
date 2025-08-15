# -*- coding: utf-8 -*-
"""
urllib Extension
Provides service discovery capability for urllib library
"""

import logging
from typing import Dict, Union, List, Optional, Any
from urllib.request import Request, OpenerDirector, BaseHandler, build_opener, urlopen

from .nacos_discovery import NacosServiceDiscovery
from .url_resolver import ServiceUrlResolver
from .core import LoadBalanceStrategy
from .utils import is_connection_error, extract_host_port
from .error_handlers import handle_connection_errors

logger = logging.getLogger(__name__)


class ServiceDiscoveryHandler(BaseHandler):
    """Service discovery handler"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery, 
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        """
        Initialize service discovery handler
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
        """
        self.resolver = ServiceUrlResolver(service_discovery)
        self.strategy = strategy
        self.service_discovery = service_discovery
        # Store URL mappings for error handling
        self._url_mapping = {}
    
    def http_request(self, req: Request) -> Request:
        """
        Handle HTTP request
        
        Args:
            req: Request object
        
        Returns:
            Processed request object
        """
        # Resolve service URL
        url = req.full_url
        try:
            resolved_url = self.resolver.resolve_url(url, strategy=self.strategy)
            
            # If URL is resolved (service discovery), update request
            if resolved_url != url:
                logger.info(f"Service discovery: {url} -> {resolved_url}")
                # Store mapping for error handling
                self._url_mapping[resolved_url] = url
                req.full_url = resolved_url
        except Exception as e:
            logger.error(f"Service discovery URL resolution failed: {url}, error: {e}")
            # Continue with original URL
        
        return req
    
    # HTTPS request handling
    https_request = http_request
    
    def http_error_default(self, req, fp, code, msg, hdrs):
        """Handle HTTP errors"""
        # Get current URL
        url = req.full_url
        original_url = self._url_mapping.get(url)
        
        if code in (500, 502, 503, 504) or msg.lower() in ('connection refused', 'connection reset'):
            # Extract host and port
            host_port = extract_host_port(url)
            if host_port:
                host, port = host_port
                logger.warning(f"Server error detected: {host}:{port}, status code: {code}, message: {msg}, adding to blacklist")
                # Add failed address to blacklist
                self.service_discovery.add_to_blacklist(host, port, reason=f"HTTP Error {code}: {msg}")
        
        # Clean up mapping
        if url in self._url_mapping:
            del self._url_mapping[url]
            
        # Continue with default error handling
        return None


class ServiceDiscoveryOpener:
    """Service discovery URL opener"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery, 
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 handlers: Optional[List[BaseHandler]] = None):
        """
        Initialize service discovery URL opener
        
        Args:
            service_discovery: Service discovery object
            strategy: Load balancing strategy
            handlers: Additional handler list
        """
        self.service_discovery = service_discovery
        self.strategy = strategy
        
        # Create handlers
        sd_handler = ServiceDiscoveryHandler(service_discovery, strategy)
        all_handlers = [sd_handler]
        if handlers:
            all_handlers.extend(handlers)
        
        # Create opener
        self.opener = build_opener(*all_handlers)
    
    @handle_connection_errors
    def open(self, url: Union[str, Request], data=None, timeout=None, *,
             cafile=None, capath=None, cadefault=False, context=None):
        """
        Open URL
        
        Args:
            url: URL or request object
            data: Request data
            timeout: Timeout
            cafile: CA certificate file
            capath: CA certificate path
            cadefault: Use default CA
            context: SSL context
        
        Returns:
            Response object
        """
        return self.opener.open(
            url, data=data, timeout=timeout,
            cafile=cafile, capath=capath, cadefault=cadefault, context=context
        )
    
    def error(self, proto, *args, **kwargs):
        """
        Handle error
        
        Args:
            proto: Protocol
            args: Positional arguments
            kwargs: Keyword arguments
        
        Returns:
            Error handling result
        """
        return self.opener.error(proto, *args, **kwargs)
    
    def add_handler(self, handler: BaseHandler):
        """
        Add handler
        
        Args:
            handler: Handler
        """
        self.opener.add_handler(handler)


def create_service_discovery_opener(service_discovery: NacosServiceDiscovery,
                                  strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                                  handlers: Optional[List[BaseHandler]] = None) -> OpenerDirector:
    """
    Create service discovery URL opener
    
    Args:
        service_discovery: Service discovery object
        strategy: Load balancing strategy
        handlers: Additional handler list
        
    Returns:
        OpenerDirector: URL opener
    """
    # Create handlers
    sd_handler = ServiceDiscoveryHandler(service_discovery, strategy)
    all_handlers = [sd_handler]
    if handlers:
        all_handlers.extend(handlers)
    
    # Create opener
    return build_opener(*all_handlers)
