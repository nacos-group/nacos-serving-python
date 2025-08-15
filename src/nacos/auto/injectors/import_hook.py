# -*- coding: utf-8 -*-
"""
Import Hook
Implements non-invasive service registration through automatic injection on import
"""

import logging
import sys
import importlib.util
from typing import Dict, Any, Optional

from ..config.loader import ConfigLoader
from ..detectors.framework_detector import FrameworkDetector
from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class ImportHook:
    """Import Hook"""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
        self.config = None
        self.hooked_modules = set()
        self.original_import = None
    
    def enable(self):
        """Enable import hook"""
        if self.original_import is not None:
            return  # Already enabled
        
        # Load configuration
        self.config = self.config_loader.load_config()
        
        # Save original __import__ function
        self.original_import = __builtins__['__import__']
        
        # Replace __import__ function
        __builtins__['__import__'] = self._hooked_import
        
        logger.info("Import hook enabled for Nacos auto-registration")
    
    def disable(self):
        """Disable import hook"""
        if self.original_import is None:
            return  # Not enabled
        
        # Restore original __import__ function
        __builtins__['__import__'] = self.original_import
        self.original_import = None
        
        logger.info("Import hook disabled")
    
    def _hooked_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        """Hooked import function"""
        # Call original import function
        module = self.original_import(name, globals, locals, fromlist, level)
        
        # Check if it's a web framework module
        if self._should_hook_module(name, module):
            self._inject_into_module(name, module)
        
        return module
    
    def _should_hook_module(self, name: str, module) -> bool:
        """Check if module should be hooked"""
        # Avoid duplicate hooking
        if name in self.hooked_modules:
            return False
        
        # Check if it's a web framework
        web_frameworks = ['flask', 'fastapi', 'django']
                
        return name in web_frameworks
    
    def _inject_into_module(self, name: str, module):
        """Inject Nacos functionality into module"""
        try:
            if name == 'flask':
                self._inject_flask_hook(module)
            elif name == 'fastapi':
                self._inject_fastapi_hook(module)
            elif name == 'django':
                self._inject_django_hook()
            
        except Exception as e:
            logger.error(f"Failed to inject hook into {name}: {e}")
    
    def _inject_flask_hook(self, flask_module):
        """Inject Flask hook"""
        if not hasattr(flask_module, 'Flask'):
            return
        
        if 'flask' in self.hooked_modules:
            return  # Avoid duplicate injection
        
        original_flask_init = flask_module.Flask.__init__
        get_config = self._get_config
        
        def hooked_flask_init(self, *args, **kwargs):
            # Call original initialization
            original_flask_init(self, *args, **kwargs)
            
            # Inject middleware
            try:
                from ..middleware.wsgi import inject_wsgi_middleware
                inject_wsgi_middleware(self, get_config())
                logger.info("Nacos middleware auto-injected into Flask app")
            except Exception as e:
                logger.error(f"Failed to auto-inject Flask middleware: {e}")
        
        # Replace Flask initialization method
        flask_module.Flask.__init__ = hooked_flask_init
        self.hooked_modules.add('flask')

    
    def _inject_fastapi_hook(self, fastapi_module):
        """Inject FastAPI hook"""
        if not hasattr(fastapi_module, 'FastAPI'):
            return
        
        if 'fastapi' in self.hooked_modules:
            return 
        
        original_fastapi_init = fastapi_module.FastAPI.__init__
        get_config = self._get_config
        
        def hooked_fastapi_init(self, *args, **kwargs):
            # Call original initialization
            original_fastapi_init(self, *args, **kwargs)
            
            # Inject middleware
            try:
                from ..middleware.asgi import inject_asgi_middleware
                inject_asgi_middleware(self, get_config())
                logger.info("Nacos middleware auto-injected into FastAPI app")
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"Failed to auto-inject FastAPI middleware: {e}")
        
        # Replace FastAPI initialization method
        fastapi_module.FastAPI.__init__ = hooked_fastapi_init
        self.hooked_modules.add('fastapi')

    def _inject_django_hook(self):
        """Inject Django hook"""
        try:
            if 'django' in self.hooked_modules:
                return
            
            import django.core.servers.basehttp as basehttp
            
            original_wsgi_getter = basehttp.get_internal_wsgi_application
            get_config = self._get_config
            def hooked_wsgi_getter(*args, **kwargs):
                app = original_wsgi_getter(*args, **kwargs)
                try:
                    from ..middleware.wsgi import inject_wsgi_middleware
                    app = inject_wsgi_middleware(app, get_config())
                    logger.info("Nacos middleware auto-injected into Django WSGI app")
                except Exception as e:
                    logger.error(f"Failed to auto-inject Django middleware: {e}")
                return app

            basehttp.get_internal_wsgi_application = hooked_wsgi_getter
            self.hooked_modules.add('django')
        except:
            return
        
    
    def _get_config(self) -> Dict[str, Any]:
        """Get configuration"""
        if self.config is None:
            self.config = self.config_loader.load_config()
        return self.config


# Global import hook instance
_import_hook = None


def enable_import_hook():
    """Enable import hook"""
    global _import_hook
    
    if _import_hook is None:
        _import_hook = ImportHook()
    
    _import_hook.enable()


def disable_import_hook():
    """Disable import hook"""
    global _import_hook
    
    if _import_hook is not None:
        _import_hook.disable()


def is_import_hook_enabled() -> bool:
    """Check if import hook is enabled"""
    global _import_hook
    return _import_hook is not None and _import_hook.original_import is not None

