# -*- coding: utf-8 -*-
"""
WSGI Middleware
Provides Nacos service registration support for Flask and other WSGI applications
"""

import logging
import time
from typing import Dict, Any, Callable, List, Tuple

from nacos.utils.tools import ProcessUtils

from ..services.manager import ServiceManager
from ..config.loader import ConfigLoader
from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class NacosWSGIMiddleware:
    """Nacos WSGI Middleware"""
    
    def __init__(self, app: Callable, config: Dict[str, Any]):
        """
        Initialize WSGI middleware
        
        Args:
            app: WSGI application
            config: Nacos configuration
        """
        self.app = app
        self.config = config
        self.service_manager = ServiceManager(config)
        
        # Initialization flag
        self._first_request_handled = False
        
        logger.info("Nacos WSGI Middleware initialized")
        
        # Initialize immediately if configured to register on startup
        self.service_manager.initialize_if_needed()
    
    def __call__(self, environ: Dict[str, Any], start_response: Callable) -> List[bytes]:
        """
        WSGI application call
        
        Args:
            environ: WSGI environment variables
            start_response: Response start function
            
        Returns:
            Response data
        """
        # Handle first request
        if not self._first_request_handled:
            self._handle_first_request(environ)
            self._first_request_handled = True
            
        return self.app(environ, start_response)
    
    def _handle_first_request(self, environ: Dict[str, Any]):
        """Handle first request"""
        try:
            logger.info(f"First WSGI request: {environ.get('REQUEST_METHOD', 'GET')} {environ.get('PATH_INFO', '/')}")
            self.service_manager.handle_first_request()
        except Exception as e:
            logger.error(f"Error handling first request: {e}")
    
    
    def get_middleware_info(self) -> Dict[str, Any]:
        """Get middleware information"""
        return {
            'type': 'wsgi',
            'first_request_handled': self._first_request_handled,
            'service_manager_status': self.service_manager.get_status(),
        }


def create_wsgi_middleware(config: Dict[str, Any]) -> Callable:
    """
    Create WSGI middleware factory function
    
    Args:
        config: Nacos configuration
        
    Returns:
        Middleware factory function
    """
    def middleware_factory(app: Callable) -> NacosWSGIMiddleware:
        return NacosWSGIMiddleware(app, config)
    
    return middleware_factory


def inject_wsgi_middleware(app, config: Dict[str, Any] = None):
    """
    Inject WSGI middleware into application
    
    Args:
        app: WSGI application object
        config: Nacos configuration
    """
    if not ProcessUtils.try_inject_environment_label():
        logger.info("Injecting Nacos middleware into WSGI app as another process already injected.")
        return app  # If unable to inject environment label, return original app directly
    
    if config is None:
        config = ConfigLoader().load_config()

    if hasattr(app, 'wsgi_app'):
        # Flask application
        logger.info("Injecting Nacos middleware into Flask app")
        app.wsgi_app = NacosWSGIMiddleware(app.wsgi_app, config)
    elif callable(app):
        # Generic WSGI application
        logger.info("Injecting Nacos middleware into WSGI app")
        return NacosWSGIMiddleware(app, config)
    else:
        logger.warning("Unable to inject middleware: unsupported app type")
        return app
    
    return app

