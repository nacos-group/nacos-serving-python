# -*- coding: utf-8 -*-
"""
Nacos HTTP Discovery
Provides automatic service discovery for mainstream Python HTTP libraries (urllib, requests, httpx, aiohttp)
"""

from .core import LoadBalanceStrategy, ServiceInstance, ServiceDiscoveryError, NoAvailableInstanceError
from .nacos_discovery import NacosServiceDiscovery

__all__ = [
    'LoadBalanceStrategy', 
    'ServiceInstance', 
    'ServiceDiscoveryError',
    'NoAvailableInstanceError',
    'NacosServiceDiscovery'
]
