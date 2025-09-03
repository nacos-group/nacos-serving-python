# -*- coding: utf-8 -*-
"""
Configuration Loader
Supports multiple configuration sources: command line arguments, environment variables, configuration files, default configuration
"""

import logging
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from ..constants import NAMING_MODULE, CONFIG_FILE_NAMES, DEFAULT_NACOS_SERVER, DEFAULT_GROUP, DEFAULT_CLUSTER

logger = logging.getLogger(NAMING_MODULE)


class ConfigLoader:
    """Configuration Loader"""
    
    def __init__(self):
        self.config_files = CONFIG_FILE_NAMES
    
    def load_config(self, cli_args=None) -> Dict[str, Any]:
        """
        Load configuration, with priority from high to low:
        1. Command line arguments
        2. Environment variables
        3. Configuration files
        4. Default configuration
        """
        config = {}
        
        # 1. Load default configuration
        config.update(self._load_default_config())
        
        # 2. Load from configuration files
        file_config = self._load_config_file()
        if file_config:
            config = self._merge_config(config, file_config)
        
        # 3. Load from environment variables
        env_config = self._load_env_config()
        config = self._merge_config(config, env_config)
        
        # 4. Load from command line arguments
        if cli_args:
            cli_config = self._load_cli_config(cli_args)
            config = self._merge_config(config, cli_config)
        
        # 5. Load spas config in EDAS environment
        config = self._load_spas_config(config)
        return config

    def _load_spas_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load SPAS configuration in EDAS environment"""

        namespace, ak, sk = _read_credentials()
        
        if namespace:
            self._set_nested_config(config, 'nacos.namespace', namespace)
        
        if ak:
            self._set_nested_config(config, 'nacos.access_key', ak)
        
        if sk:
            self._set_nested_config(config, 'nacos.secret_key', sk)
        
        return config
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            'nacos': {
                'server': None,
                'namespace': 'public',
                'username': None,
                'password': None,
                'access_key': None,
                'secret_key': None,
                'endpoint': None,
                'service': {
                    'name': None,  # Will be auto-detected
                    'port': None,  # Will be auto-detected
                    'ip': 'auto',
                    'group': DEFAULT_GROUP,
                    'cluster': DEFAULT_CLUSTER,
                    'weight': 1.0,
                    'metadata': {},
                    'enabled': True,
                    'healthy': True,
                    'ephemeral': True,
                },
                'registration': {
                    'auto_register': True,
                    'register_on_startup': True,
                    'register_on_request': True,
                    'retry_times': 3,
                    'retry_interval': 5,
                },
                'heartbeat': {
                    'interval': 30,
                    'timeout': 3,
                },
                'shutdown': {
                    'graceful': True,
                    'timeout': 30,
                    'deregister': True,
                },
                'logging': {
                    'level': 'INFO',
                    'file': None,
                    'format': None,
                },
                'advanced': {
                    'cache_dir': '~/.nacos/cache',
                    'log_dir': '~/.nacos/logs',
                    'config_cache_time': 300,
                }, 
                'discovery': {
                    'empty_protection': True,
                }
            }
        }
    
    def _load_config_file(self) -> Optional[Dict[str, Any]]:
        """Load configuration from files"""
        for config_file in self.config_files:
            config_path = Path(config_file)
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        if config_file.endswith(('.yaml', '.yml')):
                            return yaml.safe_load(f) or {}
                        elif config_file.endswith('.json'):
                            return json.load(f) or {}
                except Exception as e:
                    logger.warning(f"Failed to load config file {config_file}: {e}")
        
        return None
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        # Nacos server configuration
        if os.getenv('NACOS_SERVER'):
            self._set_nested_config(config, 'nacos.server', os.getenv('NACOS_SERVER'))
        
        if os.getenv('NACOS_NAMESPACE'):
            self._set_nested_config(config, 'nacos.namespace', os.getenv('NACOS_NAMESPACE'))
        
        if os.getenv('NACOS_USERNAME'):
            self._set_nested_config(config, 'nacos.username', os.getenv('NACOS_USERNAME'))
        
        if os.getenv('NACOS_PASSWORD'):
            self._set_nested_config(config, 'nacos.password', os.getenv('NACOS_PASSWORD'))
        
        if os.getenv('EDAS_ADDRESS_SERVER_DOMAIN'):
            server_domain = os.getenv('EDAS_ADDRESS_SERVER_DOMAIN')
            server_port = os.getenv('EDAS_ADDRESS_SERVER_PORT', '8080')
            self._set_nested_config(config, 'nacos.endpoint', f'{server_domain}:{server_port}')

        if os.getenv('NACOS_ENABLE_EMPTY_PROTECTION'):
            empty_protection = os.getenv('NACOS_ENABLE_EMPTY_PROTECTION').lower() == 'true'
            self._set_nested_config(config, 'nacos.discovery.empty_protection', empty_protection)
        # Service configuration
        if os.getenv('NACOS_SERVICE_NAME'):
            self._set_nested_config(config, 'nacos.service.name', os.getenv('NACOS_SERVICE_NAME'))
        
        if os.getenv('NACOS_SERVICE_PORT'):
            try:
                port = int(os.getenv('NACOS_SERVICE_PORT'))
                self._set_nested_config(config, 'nacos.service.port', port)
            except ValueError:
                pass
        
        if os.getenv('NACOS_SERVICE_IP'):
            self._set_nested_config(config, 'nacos.service.ip', os.getenv('NACOS_SERVICE_IP'))
        
        if os.getenv('NACOS_SERVICE_GROUP'):
            self._set_nested_config(config, 'nacos.service.group', os.getenv('NACOS_SERVICE_GROUP'))
        
        # Control switches
        if os.getenv('NACOS_AUTO_REGISTER'):
            auto_register = os.getenv('NACOS_AUTO_REGISTER').lower() == 'true'
            self._set_nested_config(config, 'nacos.registration.auto_register', auto_register)
        
        if os.getenv('NACOS_REGISTER_ON_STARTUP'):
            register_on_startup = os.getenv('NACOS_REGISTER_ON_STARTUP').lower() == 'true'
            self._set_nested_config(config, 'nacos.registration.register_on_startup', register_on_startup)
        
        if os.getenv('NACOS_GRACEFUL_SHUTDOWN'):
            graceful = os.getenv('NACOS_GRACEFUL_SHUTDOWN').lower() == 'true'
            self._set_nested_config(config, 'nacos.shutdown.graceful', graceful)
        
        # Heartbeat configuration
        if os.getenv('NACOS_HEARTBEAT_INTERVAL'):
            try:
                interval = int(os.getenv('NACOS_HEARTBEAT_INTERVAL'))
                self._set_nested_config(config, 'nacos.heartbeat.interval', interval)
            except ValueError:
                pass
        
        return config
    
    def _load_cli_config(self, cli_args) -> Dict[str, Any]:
        """Load configuration from command line arguments"""
        config = {}
        
        if hasattr(cli_args, 'nacos_server') and cli_args.nacos_server:
            self._set_nested_config(config, 'nacos.server', cli_args.nacos_server)
        
        if hasattr(cli_args, 'service_name') and cli_args.service_name:
            self._set_nested_config(config, 'nacos.service.name', cli_args.service_name)
        
        if hasattr(cli_args, 'service_port') and cli_args.service_port:
            self._set_nested_config(config, 'nacos.service.port', cli_args.service_port)
        
        if hasattr(cli_args, 'namespace') and cli_args.namespace:
            self._set_nested_config(config, 'nacos.namespace', cli_args.namespace)
        
        if hasattr(cli_args, 'group') and cli_args.group:
            self._set_nested_config(config, 'nacos.service.group', cli_args.group)
        
        return config
    
    def _set_nested_config(self, config: Dict[str, Any], key_path: str, value: Any):
        """Set nested configuration"""
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_config_summary(self, config: Dict[str, Any]) -> str:
        """Get configuration summary"""
        nacos_config = config.get('nacos', {})
        service_config = nacos_config.get('service', {})
        
        summary = f"""
Nacos Configuration Summary:
  Server: {nacos_config.get('server', DEFAULT_NACOS_SERVER)}
  Namespace: {nacos_config.get('namespace', 'public')}
  Service Name: {service_config.get('name', 'auto-detect')}
  Service Port: {service_config.get('port', 'auto-detect')}
  Service Group: {service_config.get('group', DEFAULT_GROUP)}
  Auto Register: {nacos_config.get('registration', {}).get('auto_register', True)}
  Register On Request: {nacos_config.get('registration', {}).get('register_on_request', True)}
  Graceful Shutdown: {nacos_config.get('shutdown', {}).get('graceful', True)}
"""
        return summary.strip()


def _read_credentials():
    path = '/home/admin/.spas_key/%s'
    ns_path = path % 'tenantId'
    if os.path.exists(ns_path):
        namespace = _read_from_file(path % 'tenantId')
        ak = _read_from_file(path % 'accessKey')
        sk = _read_from_file(path % 'secretKey')
    else:
        namespace = os.getenv('ALIBABA_NACOS_NAMESPACE')
        ak = os.getenv('ALIBABA_ACCESS_KEY')
        sk = os.getenv('ALIBABA_SECRET_KEY')

    return namespace, ak, sk

def _read_from_file(path):
    with open(path) as f:
        return f.read()
