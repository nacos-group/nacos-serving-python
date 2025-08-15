# -*- coding: utf-8 -*-
"""
ASGI Middleware
Provides Nacos service registration support for FastAPI and other ASGI applications
"""

import logging
import time
import asyncio
from typing import Dict, Any, Callable, Awaitable

from nacos.utils.tools import ProcessUtils

from ..services.manager import ServiceManager
from ..config.loader import ConfigLoader
from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class NacosASGIMiddleware:
    """Nacos ASGI Middleware"""
    
    def __init__(self, app: Callable, config: Dict[str, Any]):
        """
        Initialize ASGI middleware
        
        Args:
            app: ASGI application
            config: Nacos configuration
        """
        self.app = app
        self.config = config
        self.service_manager = ServiceManager(config)
        
        # Initialization flag
        self._first_request_handled = False
        self._initialization_lock = asyncio.Lock()
        
        logger.info("Nacos ASGI Middleware initialized")
        
        # Initialize immediately if configured to register on startup
        self.service_manager.initialize_if_needed()
    
    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable):
        """
        ASGI application call
        
        Args:
            scope: ASGI scope
            receive: Receive function
            send: Send function
        """
        # Only handle HTTP requests
        if scope["type"] == "http":
            await self._handle_http_request(scope, receive, send)
        else:
            # Pass other request types directly to the original application
            await self.app(scope, receive, send)
    
    async def _handle_http_request(self, scope: Dict[str, Any], receive: Callable, send: Callable):
        """Handle HTTP request"""
        # Handle first request
        if not self._first_request_handled:
            async with self._initialization_lock:
                if not self._first_request_handled:
                    await self._handle_first_request(scope)
                    self._first_request_handled = True
        
        # forward request to the original application  
        await self.app(scope, receive, send)
        
    
    async def _handle_first_request(self, scope: Dict[str, Any]):
        """Handle first request"""
        try:
            method = scope.get("method", "GET")
            path = scope.get("path", "/")
            logger.info(f"First ASGI request: {method} {path}")
            
            await self.service_manager.handle_first_request_async()
        except Exception as e:
            logger.error(f"Error handling first request: {e}")
    
    def _get_service_identifier(self) -> str:
        """Get service identifier"""
        service_info = self.service_manager.get_service_info()
        if service_info:
            return f"{service_info['service_name']}:{service_info['port']}"
        return "unknown-service"

    def get_middleware_info(self) -> Dict[str, Any]:
        """Get middleware information"""
        return {
            'type': 'asgi',
            'first_request_handled': self._first_request_handled,
            'service_manager_status': self.service_manager.get_status(),
        }


class NacosBaseHTTPMiddleware:
    """
    Nacos middleware based on BaseHTTPMiddleware
    Suitable for FastAPI and other frameworks
    """
    
    def __init__(self, config: Dict[str, Any], app):
        self.config = config
        self.service_manager = ServiceManager(config)
        self._first_request_handled = False
        self.app = app
        
        logger.info("Nacos BaseHTTPMiddleware initialized")
        self.service_manager.initialize_if_needed()
    
    async def dispatch(self, request, call_next):
        """Handle request"""
        # Handle first request
        if not self._first_request_handled:
            await self._handle_first_request(request)
            self._first_request_handled = True
            
        return await call_next(request)

    
    async def _handle_first_request(self, request):
        """Handle first request"""
        try:
            
            await self.service_manager.handle_first_request_async()
        except Exception as e:
            logger.error(f"Error handling first request: {e}")
    
    def _get_service_identifier(self) -> str:
        """Get service identifier"""
        service_info = self.service_manager.get_service_info()
        if service_info:
            return f"{service_info['service_name']}:{service_info['port']}"
        return "unknown-service"
    


def create_asgi_middleware(config: Dict[str, Any]) -> Callable:
    """
    Create ASGI middleware factory function
    
    Args:
        config: Nacos configuration
        
    Returns:
        Middleware factory function
    """
    def middleware_factory(app: Callable) -> NacosASGIMiddleware:
        return NacosASGIMiddleware(app, config)
    
    return middleware_factory


def inject_asgi_middleware(app, config: Dict[str, Any] = None):
    """
    Inject ASGI middleware into application
    
    Args:
        app: ASGI application object
        config: Nacos configuration
    """
    if not ProcessUtils.try_inject_environment_label():
        logger.info("Injecting Nacos middleware into ASGI app as another process already injected.")
        return app  # If unable to inject environment label, return original app directly

    if config is None:
        config = ConfigLoader().load_config()

    try:
        # Check if it's a FastAPI application
        if hasattr(app, 'add_middleware'):
            logger.info("Injecting Nacos middleware into FastAPI app")
            
            # Try using BaseHTTPMiddleware
            try:
                from starlette.middleware.base import BaseHTTPMiddleware
                
                class NacosMiddleware(BaseHTTPMiddleware):
                    def __init__(self, app, **kwargs):
                        super().__init__(app)
                        self.nacos_middleware = NacosBaseHTTPMiddleware(config, app)
                    
                    async def dispatch(self, request, call_next):
                        return await self.nacos_middleware.dispatch(request, call_next)
                
                app.add_middleware(NacosMiddleware)
                
            except ImportError:
                # If starlette is not available, use raw ASGI middleware
                logger.warning("Starlette not available, using raw ASGI middleware")
                return NacosASGIMiddleware(app, config)
        
        elif callable(app):
            # Generic ASGI application
            logger.info("Injecting Nacos middleware into ASGI app")
            return NacosASGIMiddleware(app, config)
        
        else:
            logger.warning("Unable to inject middleware: unsupported app type")
            return app
    
    except Exception as e:
        logger.error(f"Error injecting ASGI middleware: {e}")
        return app
    
    return app

