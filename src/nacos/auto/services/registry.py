# -*- coding: utf-8 -*-
"""
Service Registry
Responsible for registering and deregistering services with Nacos
"""

import fcntl
import logging
import os
import threading
from typing import Dict, Any, Optional

from ..detectors.service_detector import ServiceDetector
from ...utils.tools import (
    EnvironmentUtils, AsyncUtils, TimeUtils, ValidationUtils, FileUtils, ProcessUtils,
    run_async_safely, current_millis, validate_required, ensure_dir, get_current_pid
)
from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class ServiceRegistry:
    """Service Registry"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.nacos_config = config.get('nacos', {})
        self.service_config = self.nacos_config.get('service', {})
        
        self.nacos_client = None
        self.registered = False
        self.service_info = None
        self._lock = threading.Lock()
        self._retry_count = 0
        self._max_retries = self.nacos_config.get('registration', {}).get('retry_times', 3)
        self._retry_interval = self.nacos_config.get('registration', {}).get('retry_interval', 5)
        
        # Process lock related
        self._lock_file = None
        self._lock_fd = None
        self._enable_process_lock = self.nacos_config.get('registration', {}).get('enable_process_lock', True)
        
        # Check if it's mock mode
        self._mock_mode = self._is_mock_mode()
        if self._mock_mode:
            logger.info("Running in mock mode - no actual Nacos server will be contacted")
    
    def _is_mock_mode(self) -> bool:
        """Check if it's mock mode"""
        server = self.nacos_config.get('server', '')
        return server and server.startswith('mock:') or server == 'mock'
    
    def _run_async_safely(self, async_func, timeout=30):
        """Safely run an async function, intelligently handling event loops"""
        return run_async_safely(async_func, timeout)

    def _is_web_environment(self) -> bool:
        """Check if running in web environment"""
        return EnvironmentUtils.is_web_environment()

    async def initialize_async(self):
        """Asynchronously initialize Nacos client"""
        if self._mock_mode:
            return
        
        # Always recreate client to ensure it's bound to the current event loop
        try:
            from v2.nacos import NacosNamingService, ClientConfigBuilder
            
            client_config = (ClientConfigBuilder()
                           .server_address(self.nacos_config.get('server', 'localhost:8848'))
                           .namespace_id(self.nacos_config.get('namespace', ''))
                           .username(self.nacos_config.get('username', ''))
                           .password(self.nacos_config.get('password', ''))
                           .endpoint_query_header({'Request-Module': 'Naming'})
                           .access_key(self.nacos_config.get('access_key', ''))
                           .secret_key(self.nacos_config.get('secret_key', ''))
                           .endpoint(self.nacos_config.get('endpoint', ''))
                           .log_level('INFO')
                           .build())
            
            self.nacos_client = await NacosNamingService.create_naming_service(client_config)
            logger.info(f"Nacos client initialized: {self.nacos_config.get('server', 'localhost:8848')}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Nacos client: {e}")
            raise
    
    def initialize_sync(self):
        """Synchronously initialize Nacos client"""
        if self._mock_mode:
            # No need to initialize client in mock mode
            return
            
        if self.nacos_client is None:
            try:
                self._run_async_safely(self.initialize_async)
            except Exception as e:
                logger.error(f"Failed to initialize Nacos client: {e}")
                raise
    
    def prepare_service_info(self) -> Dict[str, Any]:
        """Prepare service information"""
        if self.service_info is None:
            # Detect service information
            detected_info = ServiceDetector.detect_all()
            
            # Merge configuration and detected information
            ip = self.service_config.get('ip', 'auto')
            if ip == 'auto':
                ip = detected_info['ip'] or '127.0.0.1'
            
            port = self.service_config.get('port')
            if port is None or port == 'auto':
                port = detected_info['port'] or 8000
            
            service_name = self.service_config.get('name')
            if service_name is None:
                service_name = detected_info['service_name'] or 'unknown-service'
            
            # Build service information
            self.service_info = {
                'service_name': service_name,
                'group_name': self.service_config.get('group', 'DEFAULT_GROUP'),
                'ip': ip,
                'port': int(port),
                'weight': self.service_config.get('weight', 1.0),
                'cluster_name': self.service_config.get('cluster', 'default'),
                'metadata': dict(self.service_config.get('metadata', {})),
                'enabled': self.service_config.get('enabled', True),
                'healthy': self.service_config.get('healthy', True),
                'ephemeral': self.service_config.get('ephemeral', True),
            }
            
            # Add framework information to metadata
            if detected_info['framework']:
                self.service_info['metadata']['framework'] = detected_info['framework']
            
            # Add registration time - using utility method
            self.service_info['metadata']['register_time'] = str(TimeUtils.current_seconds())
        
        return self.service_info
    
    async def register_service_async(self) -> bool:
        """Asynchronously register service"""
        if self.registered:
            return True
        
        try:
            if self._mock_mode:
                # Mock mode returns success directly
                service_info = self.prepare_service_info()
                with self._lock:
                    self.registered = True
                    self._retry_count = 0
                
                logger.info(f"Service registered successfully (MOCK MODE): {service_info['service_name']}:{service_info['port']}")
                logger.info(f"   Server: {self.nacos_config.get('server', 'mock')}")
                logger.info(f"   Namespace: {self.nacos_config.get('namespace', 'public')}")
                logger.info(f"   Group: {service_info['group_name']}")
                
                return True
            
            # Normal mode
            await self.initialize_async()
            service_info = self.prepare_service_info()
            
            # Validate required parameters
            validate_required(service_info['service_name'], 'service_name')
            validate_required(service_info['ip'], 'ip')
            validate_required(service_info['port'], 'port')
            
            from v2.nacos import RegisterInstanceParam
            
            param = RegisterInstanceParam(
                service_name=service_info['service_name'],
                group_name=service_info['group_name'],
                ip=service_info['ip'],
                port=service_info['port'],
                weight=service_info['weight'],
                cluster_name=service_info['cluster_name'],
                metadata=service_info['metadata'],
                enabled=service_info['enabled'],
                healthy=service_info['healthy'],
                ephemeral=service_info['ephemeral']
            )
            
            response = await self.nacos_client.register_instance(param)
            
            with self._lock:
                self.registered = True
                self._retry_count = 0
            
            logger.info(f"Service registered successfully: {service_info['service_name']}:{service_info['port']}")
            logger.info(f"   Server: {self.nacos_config.get('server', 'localhost:8848')}")
            logger.info(f"   Namespace: {self.nacos_config.get('namespace', 'public')}")
            logger.info(f"   Group: {service_info['group_name']}")
            
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to register service: {e}")
            
            # Retry logic
            if self._retry_count < self._max_retries:
                self._retry_count += 1
                logger.info(f"Retrying registration ({self._retry_count}/{self._max_retries}) in {self._retry_interval}s...")
                import asyncio
                await asyncio.sleep(self._retry_interval)
                return await self.register_service_async()
            
            return False
    
    def  register_service_sync(self) -> bool:
        """Synchronously register service"""
        try:
            if self._mock_mode:
                # Mock mode returns success directly
                service_info = self.prepare_service_info()
                with self._lock:
                    self.registered = True
                    self._retry_count = 0
                
                logger.info(f"Service registered successfully (MOCK MODE): {service_info['service_name']}:{service_info['port']}")
                logger.info(f"   Server: {self.nacos_config.get('server', 'mock')}")
                logger.info(f"   Namespace: {self.nacos_config.get('namespace', 'public')}")
                logger.info(f"   Group: {service_info['group_name']}")
                
                return True
            
            return self._run_async_safely(self.register_service_async)
                
        except Exception as e:
            logger.error(f"Failed to register service: {e}")
            return False
    
    async def deregister_service_async(self) -> bool:
        """Asynchronously deregister service"""
        with self._lock:
            if not self.registered or (self.nacos_client is None and not self._mock_mode):
                return True
        
        try:
            if self._mock_mode:
                service_info = self.service_info
                with self._lock:
                    self.registered = False
                
                logger.info(f"Service deregistered successfully (MOCK MODE): {service_info['service_name']}:{service_info['port']}")
                return True
            
            # Ensure client is initialized in the current event loop
            await self.initialize_async()
            
            service_info = self.service_info
            if service_info:
                from v2.nacos import DeregisterInstanceParam
                
                param = DeregisterInstanceParam(
                    service_name=service_info['service_name'],
                    group_name=service_info['group_name'],
                    ip=service_info['ip'],
                    port=service_info['port'],
                    cluster_name=service_info['cluster_name']
                )
                
                await self.nacos_client.deregister_instance(param)
                
                with self._lock:
                    self.registered = False
                
                logger.info(f"Service deregistered successfully: {service_info['service_name']}:{service_info['port']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister service: {e}")
            return False

    def deregister_service_sync(self) -> bool:
        """Synchronously deregister service"""
        try:
            if self._mock_mode:
                service_info = self.service_info
                with self._lock:
                    self.registered = False
                
                logger.info(f"Service deregistered successfully (MOCK MODE): {service_info['service_name']}:{service_info['port']}")
                return True
            
            # Use shorter timeout to avoid blocking too long
            return self._run_async_safely(self.deregister_service_async, timeout=10)
        except Exception as e:
            logger.error(f"Failed to deregister service: {e}")
            # If deregistration fails, at least mark local state and release lock
            try:
                with self._lock:
                    self.registered = False
            except Exception:
                pass
            return False


    def check_service_health_sync(self) -> bool:
        """Synchronously check service health status"""
        try:
            if self._mock_mode:
                # Mock mode always returns healthy
                return True
            
            # Normal mode - intelligently handle event loop
            return self._run_async_safely(self.check_service_health_async)
        except Exception as e:
            logger.error(f"Failed to check service health: {e}")
            return False

    async def check_service_health_async(self) -> bool:
        """Asynchronously check service health status"""
        if not self.registered or self.nacos_client is None:
            return False
        
        try:
            service_info = self.service_info
            if service_info:
                from v2.nacos import GetServiceParam
                
                param = GetServiceParam(
                    service_name=service_info['service_name'],
                    group_name=service_info['group_name'],
                    cluster_names=[service_info['cluster_name']]
                )
                
                service = await self.nacos_client.get_service(param)
                
                # Check if current instance is in service list and healthy
                for host in service.hosts:
                    if (host.ip == service_info['ip'] and 
                        host.port == service_info['port'] and 
                        host.healthy):
                        return True
                
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check service health: {e}")
            return False


    def update_instance_sync(self, **kwargs) -> bool:
        """Synchronously update instance information"""
        try:
            if self._mock_mode:
                # Mock mode returns success directly
                if self.service_info:
                    self.service_info.update(kwargs)
                logger.info("Instance updated successfully (MOCK MODE)")
                return True
            
            # Normal mode - intelligently handle event loop
            return self._run_async_safely(lambda: self.update_instance_async(**kwargs))
        except Exception as e:
            logger.error(f"Failed to update instance: {e}")
            return False

    async def update_instance_async(self, **kwargs) -> bool:
        """Asynchronously update instance information"""
        if not self.registered or self.nacos_client is None:
            return False
        
        try:
            service_info = self.service_info
            if service_info:
                # Update local service information
                service_info.update(kwargs)
                
                from v2.nacos import UpdateInstanceParam
                
                param = UpdateInstanceParam(
                    service_name=service_info['service_name'],
                    group_name=service_info['group_name'],
                    ip=service_info['ip'],
                    port=service_info['port'],
                    weight=service_info.get('weight', 1.0),
                    cluster_name=service_info['cluster_name'],
                    metadata=service_info['metadata'],
                    enabled=service_info.get('enabled', True),
                    healthy=service_info.get('healthy', True),
                    ephemeral=service_info.get('ephemeral', True)
                )
                
                await self.nacos_client.update_instance(param)
                logger.info(f"Instance updated successfully: {service_info['service_name']}:{service_info['port']}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update instance: {e}")
            return False

    def is_registered(self) -> bool:
        """Check if service is registered"""
        return self.registered
    
    def get_service_info(self) -> Optional[Dict[str, Any]]:
        """Get service information, including real heartbeat status"""
        if not self.service_info:
            return None
            
        # Basic service information
        info = dict(self.service_info)
        
        # Add real-time status information
        info['runtime_status'] = {
            'registered': self.registered,
            'retry_count': self._retry_count,
            'max_retries': self._max_retries,
            'mock_mode': self._mock_mode,
            'process_lock_enabled': self._enable_process_lock,
            'process_lock_acquired': self._lock_fd is not None,
            'process_pid': get_current_pid(),
            'last_update_time': TimeUtils.current_millis()
        }
        
        # If not in mock mode and registered, get real heartbeat information
        if not self._mock_mode and self.registered and self.nacos_client:
            try:
                # Synchronously get real-time health status
                health_status = self._run_async_safely(self._get_real_health_status, timeout=5)
                if health_status:
                    info['runtime_status'].update(health_status)
            except Exception as e:
                logger.warning(f"Failed to get real-time health status: {e}")
                info['runtime_status']['health_check_error'] = str(e)
        
        return info
    
    async def _get_real_health_status(self) -> Optional[Dict[str, Any]]:
        """Get real health status information"""
        try:
            if not self.nacos_client or not self.service_info:
                return None
            
            # Implement real health status check if needed
            return None
                
        except Exception as e:
            logger.error(f"Error getting real health status: {e}")
            return None
            
    def get_registration_status(self) -> Dict[str, Any]:
        """Get registration status"""
        return {
            'registered': self.registered,
            'service_info': self.service_info,
            'retry_count': self._retry_count,
            'max_retries': self._max_retries,
            'nacos_server': self.nacos_config.get('server', 'localhost:8848'),
            'mock_mode': self._mock_mode,
            'process_lock_enabled': self._enable_process_lock,
            'process_lock_acquired': self._lock_fd is not None,
            'lock_file': self._lock_file,
            'process_pid': get_current_pid(),
        }
    
    def _acquire_process_lock(self) -> bool:
        """Acquire process lock to prevent duplicate registration from multiple processes"""
        if not self._enable_process_lock:
            return True
            
        try:
            # Prepare service information to generate lock filename
            service_info = self.prepare_service_info()
            lock_filename = FileUtils.get_file_lock_name(
                service_info['service_name'], 
                service_info['ip'], 
                service_info['port']
            )
            
            # Lock file path
            lock_dir = os.path.join(os.path.expanduser("~"), ".nacos", "locks")
            ensure_dir(lock_dir)
            self._lock_file = os.path.join(lock_dir, lock_filename)
            
            # Try to acquire file lock
            self._lock_fd = open(self._lock_file, 'w')
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write current process information
            process_info = ProcessUtils.get_process_info()
            self._lock_fd.write(f"pid={process_info['pid']}\n")
            self._lock_fd.write(f"service={service_info['service_name']}\n")
            self._lock_fd.write(f"ip={service_info['ip']}\n")
            self._lock_fd.write(f"port={service_info['port']}\n")
            self._lock_fd.write(f"timestamp={process_info['timestamp']}\n")
            self._lock_fd.write(f"platform={process_info['platform']}\n")
            self._lock_fd.write(f"python_version={process_info['python_version']}\n")
            self._lock_fd.write(f"cwd={process_info['cwd']}\n")
            self._lock_fd.flush()
            
            logger.info(f"Acquired process lock: {self._lock_file}")
            return True
            
        except (OSError, IOError) as e:
            if self._lock_fd:
                self._lock_fd.close()
                self._lock_fd = None
            
            # Check existing lock file information
            self._check_existing_lock()
            logger.warning(f"Another process is already managing this service instance: {e}")
            return False
    
    def _check_existing_lock(self):
        """Check existing lock file information"""
        try:
            if self._lock_file and os.path.exists(self._lock_file):
                with open(self._lock_file, 'r') as f:
                    lock_info = f.read()
                logger.info(f"Existing lock info:\n{lock_info}")
                
                # Try to parse PID and check if process is still running
                for line in lock_info.split('\n'):
                    if line.startswith('pid='):
                        try:
                            existing_pid = int(line.split('=')[1])
                            if not ProcessUtils.is_process_running(existing_pid):
                                logger.warning(f"Process {existing_pid} is no longer running, lock may be stale")
                        except (ValueError, IndexError):
                            pass
        except Exception:
            pass
    
    def _release_process_lock(self):
        """Release process lock"""
        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
                self._lock_fd.close()
                logger.info(f"Released process lock: {self._lock_file}")
            except Exception as e:
                logger.warning(f"Error releasing process lock: {e}")
            finally:
                self._lock_fd = None
                
        # Delete lock file
        if self._lock_file and os.path.exists(self._lock_file):
            try:
                os.remove(self._lock_file)
            except Exception:
                pass

    def __del__(self):
        """Destructor, ensure resources are released"""
        try:
            self._release_process_lock()
        except Exception:
            pass

