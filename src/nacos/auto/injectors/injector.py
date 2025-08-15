# -*- coding: utf-8 -*-
"""
CLI Injector
Implements non-invasive service registration through command line startup method
"""

import logging
import sys
import os
import ast
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from argparse import ArgumentParser

from ..config.loader import ConfigLoader
from ..config.validator import ConfigValidator
from ..detectors.service_detector import ServiceDetector
from ..detectors.framework_detector import FrameworkDetector
from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class CLIInjector:
    """CLI Injector"""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
        self.config_validator = ConfigValidator()
        self.config = None
        self.target_app = None
        self.after_init_module = None  # For executing additional operations after module loading
    
    def create_argument_parser(self):
        """Create command line argument parser"""
        import argparse
        
        parser = NacosArgumentParser(
            prog='python -m nacos.auto.registration',
            description='Non-invasive Nacos service registration launcher',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Usage examples:
  python -m nacos.auto.registration app.py
  python -m nacos.auto.registration app:app --port 8080
  python -m nacos.auto.registration app.py --nacos-server localhost:8848
  python -m nacos.auto.registration app.py --service-name my-service --group MY_GROUP

Supported application formats:
  app.py              - Python file
  app:application     - module:app_object
  package.module:app  - package.module:app_object
            """
        )
        
        # Target application parameters
        parser.add_argument(
            'app',
            help='Target application (format: file.py or module:app)'
        )
        
        # Nacos server configuration
        parser.add_argument(
            '--nacos-server',
            default='localhost:8848',
            help='Nacos server address (default: localhost:8848)'
        )
        
        parser.add_argument(
            '--namespace',
            default='',
            help='Nacos namespace'
        )
        
        parser.add_argument(
            '--username',
            default='',
            help='Nacos username'
        )
        
        parser.add_argument(
            '--password',
            default='',
            help='Nacos password'
        )
        
        # Service configuration
        parser.add_argument(
            '--service-name',
            default=None,
            help='Service name (default: auto-detect)'
        )
        
        parser.add_argument(
            '--service-port',
            type=int,
            default=None,
            help='Service port (default: auto-detect)'
        )
        
        parser.add_argument(
            '--service-ip',
            default=None,
            help='Service IP address (default: auto-detect)'
        )
        
        parser.add_argument(
            '--group',
            default='DEFAULT_GROUP',
            help='Service group (default: DEFAULT_GROUP)'
        )
        
        parser.add_argument(
            '--cluster',
            default='default',
            help='Cluster name (default: default)'
        )
        
        # Control options
        parser.add_argument(
            '--register-on-startup',
            action='store_true',
            default=False,
            help='Register service immediately on startup'
        )
        
        parser.add_argument(
            '--no-register-on-request',
            action='store_true',
            default=False,
            help='Disable registration on first request'
        )
        
        parser.add_argument(
            '--disable-graceful-shutdown',
            action='store_true',
            default=False,
            help='Disable graceful shutdown'
        )
        
        # Debug options
        parser.add_argument(
            '--debug',
            action='store_true',
            default=False,
            help='Enable debug mode'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Dry run mode, don\'t actually register services'
        )
        
        parser.add_argument(
            '--show-config',
            action='store_true',
            default=False,
            help='Show configuration information'
        )
        
        parser.add_argument(
            '--show-detection',
            action='store_true',
            default=False,
            help='Show service detection information'
        )
        
        return parser
    
    def parse_app_spec(self, app_spec: str) -> Tuple[str, Optional[str]]:
        """
        Parse application specification
        
        Args:
            app_spec: Application specification string
            
        Returns:
            (module_path, app_object_name)
        """
        if ':' in app_spec:
            # Format: module:app or file.py:app
            module_path, app_name = app_spec.split(':', 1)
            return module_path, app_name
        else:
            # Format: file.py or module
            return app_spec, None
    
    def load_app(self, app_spec: str):
        """
        Load application object
        
        Args:
            app_spec: Application specification string
            
        Returns:
            Application object
        """
        module_path, app_name = self.parse_app_spec(app_spec)
        
        # Check if it's a file path
        if module_path.endswith('.py') and Path(module_path).exists():
            # Load Python file
            spec = importlib.util.spec_from_file_location("__main__", module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load module from {module_path}")
            
            module = importlib.util.module_from_spec(spec)
            # sys.modules["__main__"] = module
            main_code = extract_main_block(module_path)
            def after_import():
                """Execute after module loading"""
                try:
                    import __main__
                    # del module.__spec__  # Delete __file__ attribute to avoid affecting subsequent imports
                    __main__.__spec__ = None
                    __main__.__file__ = module_path  # Set __file__ attribute
                    exec(main_code, module.__dict__)
                except Exception as e:
                    logger.error(f"Failed to execute module {module_path}: {e}")

            self.after_init_module = after_import

        try:
            tmp_module_path = module_path
            if tmp_module_path.endswith('.py'):
                # If it's a file path, load directly
                tmp_module_path = tmp_module_path[:-3]  # Remove .py suffix
            module = importlib.import_module(tmp_module_path)
        except ImportError as e:
            raise ImportError(f"Cannot import module {module_path}: {e}")
        
        # Get application object
        if app_name:
            if not hasattr(module, app_name):
                raise AttributeError(f"Module {module_path} has no attribute {app_name}")
            app = getattr(module, app_name)
        else:
            # Try to auto-detect application object
            app = self._detect_app_object(module)
            if app is None:
                raise ValueError(f"Cannot detect app object in {module_path}")
        
        return app
    
    def _detect_app_object(self, module):
        """Auto-detect application object"""
        # Common application object names
        app_names = ['app', 'application', 'main', 'server']
        
        for name in app_names:
            if hasattr(module, name):
                obj = getattr(module, name)
                if self._is_web_app(obj):
                    return obj
        
        # Check all attributes
        for name in dir(module):
            if not name.startswith('_'):
                obj = getattr(module, name)
                if self._is_web_app(obj):
                    return obj
        
        return None
    
    def _is_web_app(self, obj) -> bool:
        """Check if object is a web application"""
        # Flask application
        if hasattr(obj, 'wsgi_app') and hasattr(obj, 'route'):
            return True
        
        # FastAPI application
        if hasattr(obj, 'add_middleware') and hasattr(obj, 'get'):
            return True
        
        # Django application (usually a function)
        if callable(obj) and hasattr(obj, '__name__'):
            if 'wsgi' in obj.__name__.lower() or 'asgi' in obj.__name__.lower():
                return True
        
        # Generic WSGI/ASGI application
        if callable(obj):
            return True
        
        return False
    
    def inject_middleware(self, app):
        """Inject middleware into application"""
        framework = FrameworkDetector.detect_framework()
        
        if not framework:
            logger.warning("Cannot detect framework, trying generic injection...")
        
        # Inject appropriate middleware based on framework type
        if framework in ['flask', 'django'] or self._is_wsgi_app(app):
            from ..middleware.wsgi import inject_wsgi_middleware
            return inject_wsgi_middleware(app, self.config)
        
        elif framework in ['fastapi'] or self._is_asgi_app(app):
            from ..middleware.asgi import inject_asgi_middleware
            return inject_asgi_middleware(app, self.config)
        
        else:
            logger.warning("Unknown framework, trying WSGI injection...")
            from ..middleware.wsgi import inject_wsgi_middleware
            return inject_wsgi_middleware(app, self.config)
    
    def _is_wsgi_app(self, app) -> bool:
        """Check if it's a WSGI application"""
        return hasattr(app, 'wsgi_app') or (callable(app) and not hasattr(app, 'add_middleware'))
    
    def _is_asgi_app(self, app) -> bool:
        """Check if it's an ASGI application"""
        return hasattr(app, 'add_middleware') or hasattr(app, '__call__')
    
    def run(self, args=None):
        """Run command line injector"""
        parser = self.create_argument_parser()

        try:
            parsed_args = parser.parse_args(args)
        except Exception as e:
            # Handle parsing errors
            logger.error("Argument parsing failed")
            return

        try:
            # Load configuration
            self.config = self.config_loader.load_config(parsed_args)
            
            # Validate configuration
            is_valid, errors, warnings = self.config_validator.validate_config(self.config)
            
            if not is_valid:
                logger.error("Configuration validation failed:")
                for error in errors:
                    logger.error(f"   - {error}")
                sys.exit(1)
            
            if warnings:
                logger.warning("Configuration warnings:")
                for warning in warnings:
                    logger.warning(f"   - {warning}")
            
            # Show configuration information
            if parsed_args.show_config:
                logger.info(self.config_loader.get_config_summary(self.config))
                logger.info("")
            
            # Show detection information
            if parsed_args.show_detection:
                logger.info(ServiceDetector.get_detection_report())
                logger.info("")
                logger.info(FrameworkDetector.get_detection_report())
                logger.info("")
            
            # Dry run mode
            if parsed_args.dry_run:
                logger.info("Dry run mode - configuration validated successfully")
                return
            
            # Load application
            logger.info(f"Loading application: {parsed_args.app}")
            self.target_app = self.load_app(parsed_args.app)
            
            # Inject middleware
            logger.info("Injecting Nacos middleware...")
            self.target_app = self.inject_middleware(self.target_app)
            
            logger.info("Application loaded and middleware injected successfully")
            logger.info("Nacos auto-registration is now active")
            
            # If it's script mode, keep running
            if parsed_args.app.endswith('.py'):

                if self.after_init_module:
                    logger.info("Running real app module after module initialization...")
                    self.after_init_module()
                
                logger.info("Keeping application running...")
                try:
                    # Keep main thread running
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, shutting down...")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            if parsed_args.debug:
                import traceback
                traceback.print_exc()
            sys.exit(1)


def extract_main_block(module_path):
    """Extract main code block from module"""
    with open(module_path, 'r') as f:
        tree = ast.parse(f.read())
    
    # Find if __name__ == '__main__' node
    for node in tree.body:
        if (isinstance(node, ast.If) and 
            isinstance(node.test, ast.Compare) and
            isinstance(node.test.left, ast.Name) and
            node.test.left.id == '__name__'):
            # Extract main code block
            return ast.unparse(node.body)
        
    return None


class NacosArgumentParser(ArgumentParser):
    """Custom ArgumentParser that handles error output"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    
    def error(self, message):
        """Override error method to print error message"""
        pass

def main():
    """Main entry function"""
    injector = CLIInjector()
    injector.run()


if __name__ == '__main__':
    main()

