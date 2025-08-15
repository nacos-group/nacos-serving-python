# -*- coding: utf-8 -*-
"""
requests Extension
Provides drop-in replacement for requests module with Nacos service discovery
"""

import sys
import logging

# Import all from requests
try:
    import requests
except ImportError:
    raise ImportError("requests module is required for nacos.auto.discovery.ext.requests")

from ..requests_ext import ServiceDiscoverySession, mount_service_discovery
from .manager import get_discovery_client, DEFAULT_STRATEGY
from ...constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


def _get_service_discovery_session(**kwargs):
    """Get a requests session with service discovery"""
    try:
        service_discovery = get_discovery_client()
        return ServiceDiscoverySession(
            service_discovery, 
            strategy=DEFAULT_STRATEGY,
            **kwargs
        )
    except Exception as e:
        logger.debug(f"Error creating service discovery session: {e}", exc_info=True)
        return requests.Session()


def request(method, url, **kwargs):
    """
    Send a request using Nacos service discovery
    
    Args:
        method: HTTP method
        url: URL to send request to
        kwargs: Additional arguments to pass to requests
        
    Returns:
        Response object
    """
    with _get_service_discovery_session() as session:
        return session.request(method=method, url=url, **kwargs)


def get(url, params=None, **kwargs):
    """GET request with service discovery"""
    return request('get', url, params=params, **kwargs)


def post(url, data=None, json=None, **kwargs):
    """POST request with service discovery"""
    return request('post', url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    """PUT request with service discovery"""
    return request('put', url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    """PATCH request with service discovery"""
    return request('patch', url, data=data, **kwargs)


def delete(url, **kwargs):
    """DELETE request with service discovery"""
    return request('delete', url, **kwargs)


def head(url, **kwargs):
    """HEAD request with service discovery"""
    return request('head', url, **kwargs)


def options(url, **kwargs):
    """OPTIONS request with service discovery"""
    return request('options', url, **kwargs)


def session(**kwargs):
    """
    Create a session with service discovery
    
    Args:
        kwargs: Additional arguments to pass to Session constructor
        
    Returns:
        Session object with service discovery enabled
    """
    return _get_service_discovery_session(**kwargs)


__all__ = ["request", 
           "get", 
           "post", 
           "put", 
           "patch", 
           "delete", 
           "head", 
           "options", 
           "session"]
