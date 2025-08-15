# -*- coding: utf-8 -*-
"""
Configuration Validator
Validates the correctness and completeness of configuration
"""

import logging
import re
from typing import Dict, Any, List, Tuple

from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class ConfigValidator:
    """Configuration Validator"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate configuration
        Returns: (is_valid, errors, warnings)
        """
        self.errors.clear()
        self.warnings.clear()
        
        nacos_config = config.get('nacos', {})
        
        # Validate Nacos server configuration
        self._validate_server_config(nacos_config)
        
        # Validate service configuration
        self._validate_service_config(nacos_config.get('service', {}))
        
        # Validate registration configuration
        self._validate_registration_config(nacos_config.get('registration', {}))
                
        # Validate shutdown configuration
        self._validate_shutdown_config(nacos_config.get('shutdown', {}))
        
        return len(self.errors) == 0, self.errors.copy(), self.warnings.copy()
    
    def _validate_server_config(self, nacos_config: Dict[str, Any]):
        """Validate server configuration"""
        server = nacos_config.get('server', '')
        if not server:
            self.errors.append("Nacos server address is required")
            return
        
        # Validate server address format
        if not self._is_valid_server_address(server):
            self.errors.append(f"Invalid Nacos server address format: {server}")
        
        # Validate namespace
        namespace = nacos_config.get('namespace', '')
        if namespace and not isinstance(namespace, str):
            self.errors.append("Namespace must be a string")
        
        # Validate username and password
        username = nacos_config.get('username')
        password = nacos_config.get('password')
        
        if username and not password:
            self.warnings.append("Username provided but password is missing")
        elif password and not username:
            self.warnings.append("Password provided but username is missing")
    
    def _validate_service_config(self, service_config: Dict[str, Any]):
        """Validate service configuration"""
        # Validate service name
        service_name = service_config.get('name')
        if service_name and not self._is_valid_service_name(service_name):
            self.errors.append(f"Invalid service name: {service_name}")
        
        # Validate port
        port = service_config.get('port')
        if port is not None:
            if not isinstance(port, int) or port <= 0 or port > 65535:
                self.errors.append(f"Invalid port number: {port}")
        
        # Validate IP address
        ip = service_config.get('ip', 'auto')
        if ip != 'auto' and not self._is_valid_ip_address(ip):
            self.errors.append(f"Invalid IP address: {ip}")
        
        # Validate weight
        weight = service_config.get('weight', 1.0)
        if not isinstance(weight, (int, float)) or weight <= 0:
            self.errors.append(f"Invalid weight: {weight}")
        
        # Validate group name
        group = service_config.get('group', 'DEFAULT_GROUP')
        if not isinstance(group, str) or not group:
            self.errors.append("Service group must be a non-empty string")
        
        # Validate cluster name
        cluster = service_config.get('cluster', 'default')
        if not isinstance(cluster, str) or not cluster:
            self.errors.append("Cluster name must be a non-empty string")
        
        # Validate metadata
        metadata = service_config.get('metadata', {})
        if not isinstance(metadata, dict):
            self.errors.append("Service metadata must be a dictionary")
    
    def _validate_registration_config(self, registration_config: Dict[str, Any]):
        """Validate registration configuration"""
        # Validate retry times
        retry_times = registration_config.get('retry_times', 3)
        if not isinstance(retry_times, int) or retry_times < 0:
            self.errors.append(f"Invalid retry times: {retry_times}")
        
        # Validate retry interval
        retry_interval = registration_config.get('retry_interval', 5)
        if not isinstance(retry_interval, (int, float)) or retry_interval <= 0:
            self.errors.append(f"Invalid retry interval: {retry_interval}")
        
        # Validate registration policy
        register_on_startup = registration_config.get('register_on_startup', False)
        register_on_request = registration_config.get('register_on_request', True)
        
        if not register_on_startup and not register_on_request:
            self.warnings.append("Neither register_on_startup nor register_on_request is enabled")
        
    def _validate_shutdown_config(self, shutdown_config: Dict[str, Any]):
        """Validate shutdown configuration"""
        # Validate shutdown timeout
        timeout = shutdown_config.get('timeout', 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            self.errors.append(f"Invalid shutdown timeout: {timeout}")
    
    def _is_valid_server_address(self, address: str) -> bool:
        """Validate server address format"""
        # Supported formats: host:port or host1:port1,host2:port2
        addresses = address.split(',')
        
        for addr in addresses:
            addr = addr.strip()
            if ':' not in addr:
                return False
            
            host, port_str = addr.rsplit(':', 1)
            
            # Validate hostname
            if not host:
                return False
            
            # Validate port
            try:
                port = int(port_str)
                if port <= 0 or port > 65535:
                    return False
            except ValueError:
                return False
        
        return True
    
    def _is_valid_service_name(self, name: str) -> bool:
        """Validate service name format"""
        if not isinstance(name, str) or not name:
            return False
        
        # Service name can only contain letters, numbers, hyphens and underscores
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name))
    
    def _is_valid_ip_address(self, ip: str) -> bool:
        """Validate IP address format"""
        if not isinstance(ip, str):
            return False
        
        # Simple IPv4 address validation
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
        except ValueError:
            return False
        
        return True
    
    def get_validation_report(self, config: Dict[str, Any]) -> str:
        """Get validation report"""
        is_valid, errors, warnings = self.validate_config(config)
        
        report = ["Configuration Validation Report:", "=" * 40]
        
        if is_valid:
            report.append("✅ Configuration is valid")
        else:
            report.append("❌ Configuration has errors")
        
        if errors:
            report.append("\nErrors:")
            for i, error in enumerate(errors, 1):
                report.append(f"  {i}. {error}")
        
        if warnings:
            report.append("\nWarnings:")
            for i, warning in enumerate(warnings, 1):
                report.append(f"  {i}. {warning}")
        
        if not errors and not warnings:
            report.append("\nNo issues found.")
        
        return "\n".join(report)

