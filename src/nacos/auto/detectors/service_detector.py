# -*- coding: utf-8 -*-
"""
Service Detector
Automatically detects running service information
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from ...utils.tools import (
    NetworkUtils, EnvironmentUtils, StringUtils,
    get_local_ip, is_web_environment, is_not_blank
)
from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class ServiceDetector:
    """Service Detector"""
    
    @staticmethod
    def detect_ip() -> Optional[str]:
        """Detect service IP"""
        try:
            return get_local_ip()
        except Exception:
            return None
    
    @staticmethod
    def detect_port() -> Optional[int]:
        """Detect service port"""
        # Detect from environment variables
        port_env = os.getenv('PORT') or os.getenv('SERVER_PORT')
        if port_env and NetworkUtils.is_valid_port(port_env):
            return int(port_env)
        
        # Detect from common frameworks
        if is_web_environment():
            # FastAPI/Uvicorn default port
            if 'uvicorn' in str(os.environ.get('_', '')):
                return 8000
            # Django default port
            if 'django' in str(os.environ.get('_', '')):
                return 8000
        
        return None
 
    @staticmethod
    def detect_service_name() -> Optional[str]:
        """Detect service name"""
        # 1. Get from project directory name
        current_dir = Path.cwd().name
        if current_dir and current_dir != '/' and current_dir != 'root':
            return ServiceDetector._normalize_service_name(current_dir)
        
        # 2. Get from setup.py
        name = ServiceDetector._get_name_from_setup_py()
        if name:
            return ServiceDetector._normalize_service_name(name)
        
        # 3. Get from pyproject.toml
        name = ServiceDetector._get_name_from_pyproject()
        if name:
            return ServiceDetector._normalize_service_name(name)
        
        # 4. Get from package.json (mixed projects)
        name = ServiceDetector._get_name_from_package_json()
        if name:
            return ServiceDetector._normalize_service_name(name)
        
        # 5. Get from main file name
        name = ServiceDetector._get_name_from_main_file()
        if name:
            return ServiceDetector._normalize_service_name(name)
        
        return None
    
    @staticmethod
    def _get_name_from_setup_py() -> Optional[str]:
        """Get project name from setup.py"""
        setup_py = Path('setup.py')
        if setup_py.exists():
            try:
                with open(setup_py, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Match name='xxx' or name="xxx"
                    match = re.search(r'name\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                    if match:
                        return match.group(1)
            except Exception:
                pass
        return None
    
    @staticmethod
    def _get_name_from_pyproject() -> Optional[str]:
        """Get project name from pyproject.toml"""
        pyproject = Path('pyproject.toml')
        if pyproject.exists():
            try:
                # Simple parsing without depending on toml library
                with open(pyproject, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Match name = "xxx" under [tool.poetry]
                    poetry_section = False
                    for line in content.split('\n'):
                        line = line.strip()
                        if line == '[tool.poetry]':
                            poetry_section = True
                            continue
                        elif line.startswith('[') and poetry_section:
                            break
                        elif poetry_section and line.startswith('name'):
                            match = re.search(r'name\s*=\s*[\'"]([^\'"]+)[\'"]', line)
                            if match:
                                return match.group(1)
            except Exception:
                pass
        return None
    
    @staticmethod
    def _get_name_from_package_json() -> Optional[str]:
        """Get project name from package.json"""
        package_json = Path('package.json')
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('name')
            except Exception:
                pass
        return None
    
    @staticmethod
    def _get_name_from_main_file() -> Optional[str]:
        """Get project name from main file name"""
        main_files = ['app.py', 'main.py', 'server.py', 'run.py', 'wsgi.py', 'asgi.py']
        for main_file in main_files:
            if Path(main_file).exists():
                return Path(main_file).stem
        return None
    
    @staticmethod
    def _normalize_service_name(name: str) -> str:
        """Normalize service name"""
        # Convert to lowercase
        name = name.lower()
        
        # Replace underscores with hyphens
        name = name.replace('_', '-')
        
        # Remove invalid characters
        name = re.sub(r'[^a-z0-9-]', '', name)
        
        # Remove leading and trailing hyphens
        name = name.strip('-')
        
        return name or 'unknown-service'
    
    @staticmethod
    def detect_framework() -> Optional[str]:
        """Detect the web framework being used"""
        # Check imported modules
        frameworks = {
            'flask': 'flask',
            'fastapi': 'fastapi',
            'django': 'django',
            'tornado': 'tornado',
            'bottle': 'bottle',
            'pyramid': 'pyramid',
            'falcon': 'falcon',
        }
        
        for framework, module_name in frameworks.items():
            if module_name in sys.modules:
                return framework
        
        # Check project files
        if Path('manage.py').exists():
            return 'django'
        
        if Path('requirements.txt').exists():
            try:
                with open('requirements.txt', 'r') as f:
                    content = f.read().lower()
                    for framework in frameworks:
                        if framework in content:
                            return framework
            except Exception:
                pass
        
        return None
        
    @staticmethod
    def detect_all() -> Dict[str, Any]:
        """Detect all service information"""
        return {
            'ip': ServiceDetector.detect_ip(),
            'port': ServiceDetector.detect_port(),
            'service_name': ServiceDetector.detect_service_name(),
            'framework': ServiceDetector.detect_framework(),
        }
    
    @staticmethod
    def get_detection_report() -> str:
        """Get detection report"""
        info = ServiceDetector.detect_all()
        
        report = [
            "Service Detection Report:",
            "=" * 30,
            f"IP Address: {info['ip'] or 'Not detected'}",
            f"Port: {info['port'] or 'Not detected'}",
            f"Service Name: {info['service_name'] or 'Not detected'}",
            f"Framework: {info['framework'] or 'Not detected'}",
        ]
        
        return "\n".join(report)

