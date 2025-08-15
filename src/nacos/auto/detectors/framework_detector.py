# -*- coding: utf-8 -*-
"""
Framework Detector
Detects the web framework type and version being used in the current application
"""

import logging
import sys
import inspect
from typing import Optional, Dict, Any, List

from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class FrameworkDetector:
    """Web Framework Detector"""
    
    @staticmethod
    def detect_framework() -> Optional[str]:
        """Detect the current web framework"""
        # Detect frameworks by priority
        detectors = [
            FrameworkDetector._detect_flask,
            FrameworkDetector._detect_fastapi,
            FrameworkDetector._detect_django,
            FrameworkDetector._detect_tornado,
            FrameworkDetector._detect_bottle,
            FrameworkDetector._detect_pyramid,
            FrameworkDetector._detect_falcon,
        ]
        
        for detector in detectors:
            framework = detector()
            if framework:
                return framework
        
        return None
    
    @staticmethod
    def _detect_flask() -> Optional[str]:
        """Detect Flask framework"""
        if 'flask' in sys.modules:
            return 'flask'
        
        # Check if there's Flask-related code in the call stack
        frame = inspect.currentframe()
        while frame:
            filename = frame.f_code.co_filename
            if 'flask' in filename.lower():
                return 'flask'
            frame = frame.f_back
        
        return None
    
    @staticmethod
    def _detect_fastapi() -> Optional[str]:
        """Detect FastAPI framework"""
        if 'fastapi' in sys.modules:
            return 'fastapi'
        
        # Check if there's uvicorn or other ASGI server
        asgi_servers = ['uvicorn', 'hypercorn', 'daphne']
        for server in asgi_servers:
            if server in sys.modules:
                # Further check if it's FastAPI
                if 'fastapi' in str(sys.modules.get(server, '')):
                    return 'fastapi'
        
        return None
    
    @staticmethod
    def _detect_django() -> Optional[str]:
        """Detect Django framework"""
        if 'django' in sys.modules:
            return 'django'
        
        # Check Django-specific environment variables
        import os
        if 'DJANGO_SETTINGS_MODULE' in os.environ:
            return 'django'
        
        return None
    
    @staticmethod
    def _detect_tornado() -> Optional[str]:
        """Detect Tornado framework"""
        if 'tornado' in sys.modules:
            return 'tornado'
        return None
    
    @staticmethod
    def _detect_bottle() -> Optional[str]:
        """Detect Bottle framework"""
        if 'bottle' in sys.modules:
            return 'bottle'
        return None
    
    @staticmethod
    def _detect_pyramid() -> Optional[str]:
        """Detect Pyramid framework"""
        if 'pyramid' in sys.modules:
            return 'pyramid'
        return None
    
    @staticmethod
    def _detect_falcon() -> Optional[str]:
        """Detect Falcon framework"""
        if 'falcon' in sys.modules:
            return 'falcon'
        return None
    
    @staticmethod
    def get_framework_info() -> Dict[str, Any]:
        """Get detailed framework information"""
        framework = FrameworkDetector.detect_framework()
        if not framework:
            return {'framework': None, 'version': None, 'type': None}
        
        info = {
            'framework': framework,
            'version': FrameworkDetector._get_framework_version(framework),
            'type': FrameworkDetector._get_framework_type(framework),
        }
        
        return info
    
    @staticmethod
    def _get_framework_version(framework: str) -> Optional[str]:
        """Get framework version"""
        try:
            if framework == 'flask' and 'flask' in sys.modules:
                import flask
                return getattr(flask, '__version__', None)
            
            elif framework == 'fastapi' and 'fastapi' in sys.modules:
                import fastapi
                return getattr(fastapi, '__version__', None)
            
            elif framework == 'django' and 'django' in sys.modules:
                import django
                return getattr(django, '__version__', None)
            
            elif framework == 'tornado' and 'tornado' in sys.modules:
                import tornado
                return getattr(tornado, 'version', None)
            
            elif framework == 'bottle' and 'bottle' in sys.modules:
                import bottle
                return getattr(bottle, '__version__', None)
            
            elif framework == 'pyramid' and 'pyramid' in sys.modules:
                import pyramid
                return getattr(pyramid, '__version__', None)
            
            elif framework == 'falcon' and 'falcon' in sys.modules:
                import falcon
                return getattr(falcon, '__version__', None)
        
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def _get_framework_type(framework: str) -> str:
        """Get framework type (WSGI/ASGI)"""
        wsgi_frameworks = ['flask', 'django', 'bottle', 'pyramid', 'falcon']
        asgi_frameworks = ['fastapi', 'django']  # Django supports both
        
        if framework in asgi_frameworks:
            # Django supports both WSGI and ASGI, needs further detection
            if framework == 'django':
                return FrameworkDetector._detect_django_type()
            return 'asgi'
        elif framework in wsgi_frameworks:
            return 'wsgi'
        else:
            return 'unknown'
    
    @staticmethod
    def _detect_django_type() -> str:
        """Detect if Django is using WSGI or ASGI"""
        try:
            # Check if there's an ASGI application configuration
            import os
            settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
            if settings_module:
                # Try to import settings module
                import importlib
                settings = importlib.import_module(settings_module)
                
                # Check if ASGI application is configured
                if hasattr(settings, 'ASGI_APPLICATION'):
                    return 'asgi'
        except Exception:
            pass
        
        # Default to WSGI
        return 'wsgi'
    
    @staticmethod
    def detect_app_instances() -> List[Dict[str, Any]]:
        """Detect application instances"""
        instances = []
        framework = FrameworkDetector.detect_framework()
        
        if framework == 'flask':
            instances.extend(FrameworkDetector._find_flask_instances())
        elif framework == 'fastapi':
            instances.extend(FrameworkDetector._find_fastapi_instances())
        elif framework == 'django':
            instances.extend(FrameworkDetector._find_django_instances())
        
        return instances
    
    @staticmethod
    def _find_flask_instances() -> List[Dict[str, Any]]:
        """Find Flask application instances"""
        instances = []
        
        if 'flask' not in sys.modules:
            return instances
        
        import flask
        
        # Search through all global variables for Flask instances
        frame = inspect.currentframe()
        while frame:
            for name, obj in frame.f_globals.items():
                if isinstance(obj, flask.Flask):
                    instances.append({
                        'type': 'flask',
                        'name': name,
                        'instance': obj,
                        'module': frame.f_code.co_filename,
                    })
            frame = frame.f_back
        
        return instances
    
    @staticmethod
    def _find_fastapi_instances() -> List[Dict[str, Any]]:
        """Find FastAPI application instances"""
        instances = []
        
        if 'fastapi' not in sys.modules:
            return instances
        
        import fastapi
        
        # Search through all global variables for FastAPI instances
        frame = inspect.currentframe()
        while frame:
            for name, obj in frame.f_globals.items():
                if isinstance(obj, fastapi.FastAPI):
                    instances.append({
                        'type': 'fastapi',
                        'name': name,
                        'instance': obj,
                        'module': frame.f_code.co_filename,
                    })
            frame = frame.f_back
        
        return instances
    
    @staticmethod
    def _find_django_instances() -> List[Dict[str, Any]]:
        """Find Django application instances"""
        instances = []
        
        if 'django' not in sys.modules:
            return instances
        
        # Django typically uses settings module configuration, not direct application instances
        import os
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        if settings_module:
            instances.append({
                'type': 'django',
                'name': 'django_app',
                'instance': None,  # Django doesn't have a single application instance
                'module': settings_module,
            })
        
        return instances
    
    @staticmethod
    def get_detection_report() -> str:
        """Get framework detection report"""
        framework_info = FrameworkDetector.get_framework_info()
        instances = FrameworkDetector.detect_app_instances()
        
        report = [
            "Framework Detection Report:",
            "=" * 35,
            f"Framework: {framework_info['framework'] or 'Not detected'}",
            f"Version: {framework_info['version'] or 'Unknown'}",
            f"Type: {framework_info['type'] or 'Unknown'}",
        ]
        
        if instances:
            report.append(f"\nDetected {len(instances)} application instance(s):")
            for i, instance in enumerate(instances, 1):
                report.append(f"  {i}. {instance['name']} ({instance['type']}) in {instance['module']}")
        else:
            report.append("\nNo application instances detected")
        
        return "\n".join(report)

