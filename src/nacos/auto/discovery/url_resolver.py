# -*- coding: utf-8 -*-
"""
URL Resolver
Resolves service URLs and converts them to actual addresses
"""

import re
import logging
from typing import Optional, Tuple, Dict
from urllib.parse import urlparse, urlunparse, ParseResult

from .core import ServiceInstance, LoadBalanceStrategy, NoAvailableInstanceError
from .nacos_discovery import NacosServiceDiscovery

NAMING_LOGGER_NAME = "nacos.discovery.url_resolver"

logger = logging.getLogger(NAMING_LOGGER_NAME)

class ServiceUrlResolver:
    """Service URL resolver"""
    
    def __init__(self, service_discovery: NacosServiceDiscovery):
        """
        Initialize URL resolver
        
        Args:
            service_discovery: Service discovery object
        """
        self.service_discovery = service_discovery
    
    def resolve_url(self, url: str, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN) -> str:
        """
        Resolve URL, converting service name to actual address
        
        Args:
            url: URL with service name
            strategy: Load balancing strategy
        
        Returns:
            URL with actual address
        
        Raises:
            NoAvailableInstanceError: No available service instance
        """
        service_name, parsed_url = self._parse_url(url)
        
        # If not a service URL, return directly
        if not service_name:
            return url
        try:
            # Get service instance (黑名单过滤在服务发现类的_select_instance方法中处理)
            instance = self.service_discovery.get_instance_sync(service_name, strategy=strategy) 
            # Replace host and port
            return self._replace_host_port(parsed_url, instance.ip, instance.port)
        except NoAvailableInstanceError as e:
            # Raise exception if no available instance
            logger.error(f"No available instance for service '{service_name}': {e}")
            raise 
    
    async def resolve_url_async(self, url: str, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN) -> str:
        """
        Asynchronously resolve URL, converting service name to actual address
        
        Args:
            url: URL with service name
            strategy: Load balancing strategy
        
        Returns:
            URL with actual address
        
        Raises:
            NoAvailableInstanceError: No available service instance
        """
        service_name, parsed_url = self._parse_url(url)
        
        # If not a service URL, return directly
        if not service_name:
            return url
        
        # Get service instance
        instance = await self.service_discovery.get_instance_async(service_name, strategy=strategy)
        
        # Replace host and port
        return self._replace_host_port(parsed_url, instance.ip, instance.port)
    
    def _parse_url(self, url: str) -> Tuple[Optional[str], ParseResult]:
        """
        Parse URL, extract service name
        
        Args:
            url: URL string
        
        Returns:
            (service_name, parsed URL object)
        """
        parsed_url = urlparse(url)
        
        # Check if it's an IP address and port
        if self._is_ip_port(parsed_url.netloc):
            return None, parsed_url
        
        # Check if it contains a port
        if ':' in parsed_url.netloc:
            service_name, port = parsed_url.netloc.split(':', 1)
            # This is a special case, service name with port
            # TODO: Consider how to handle this case
            return service_name, parsed_url
        
        # Normal service name
        return parsed_url.netloc, parsed_url
    
    def _is_ip_port(self, host: str) -> bool:
        """
        Check if host is in IP:port format
        
        Args:
            host: Host string
        
        Returns:
            Whether it's in IP:port format
        """
        # Simple IPv4 address check
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(:\d+)?$'
        return bool(re.match(ip_pattern, host))
    
    def _replace_host_port(self, parsed_url: ParseResult, ip: str, port: int) -> str:
        """
        Replace URL host and port
        
        Args:
            parsed_url: Parsed URL object
            ip: IP address
            port: Port
        
        Returns:
            URL string with replaced host and port
        """
        new_netloc = f"{ip}:{port}"
        new_parts = (
            parsed_url.scheme,
            new_netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        )
        return urlunparse(new_parts)
    
    def get_service_name(self, url: str) -> Optional[str]:
        """
        Get service name from URL
        
        Args:
            url: URL string
        
        Returns:
            Service name, or None if not a service URL
        """
        service_name, _ = self._parse_url(url)
        return service_name
