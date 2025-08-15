# -*- coding: utf-8 -*-
"""
Service Manager
Integrates service registration, heartbeat management, graceful shutdown and other functions
"""

import logging
import time
from typing import Dict, Any, Optional

from .registry import ServiceRegistry
from .shutdown import GracefulShutdownManager
from ..constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class ServiceManager:
    """Service Manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.nacos_config = config.get('nacos', {})
        self.registration_config = self.nacos_config.get('registration', {})
        
        # Initialize various managers
        self.service_registry = ServiceRegistry(config)
        self.shutdown_manager = GracefulShutdownManager(config)
        
        # Register shutdown handler
        shutdown_handler = self.shutdown_manager.create_service_shutdown_handler(
            self.service_registry
        )
        self.shutdown_manager.add_shutdown_handler(shutdown_handler)
        
        self._initialized = False
        self._start_time = time.time()
    
    def is_registered(self) -> bool:
        """Check if service is registered"""
        return self.service_registry.is_registered()
    
    def should_auto_register(self) -> bool:
        """Check if should auto register"""
        return self.registration_config.get('auto_register', True)
    
    def should_register_on_startup(self) -> bool:
        """Check if should register on startup"""
        return self.registration_config.get('register_on_startup', False)
    
    def should_register_on_request(self) -> bool:
        """Check if should register on first request"""
        return self.registration_config.get('register_on_request', True)
    
    async def register_service_async(self) -> bool:
        """Asynchronously register service"""
        if not self.should_auto_register():
            logger.warning("Auto registration is disabled")
            return False
        
        if self.is_registered():
            logger.info("Service already registered")
            return True
        
        logger.info("Registering service...")
        success = await self.service_registry.register_service_async()
        
        if success:
            logger.info("Service management initialized successfully")
        else:
            logger.error("Failed to initialize service management")
        
        return success
    
    def register_service_sync(self) -> bool:
        """Synchronously register service"""
        if not self.should_auto_register():
            logger.warning("Auto registration is disabled")
            return False
        
        if self.is_registered():
            logger.info("Service already registered")
            return True
        
        logger.info("Registering service...")
        success = self.service_registry.register_service_sync()
        
        if success:
            logger.info("Service management initialized successfully")
        else:
            logger.error("Failed to initialize service management")
        
        return success
    
    def initialize_if_needed(self):
        """Initialize service management if needed"""
        if self._initialized:
            return
        
        # Register immediately if configured to register on startup
        if self.should_register_on_startup():
            self.register_service_sync()
        
        self._initialized = True
    
    def handle_first_request(self):
        """Handle first request"""
        if not self.is_registered() and self.should_register_on_request():
            logger.info("First request received, registering service...")
            self.register_service_sync()
    
    async def handle_first_request_async(self):
        """Asynchronously handle first request"""
        if not self.is_registered() and self.should_register_on_request():
            logger.info("First request received, registering service...")
            await self.register_service_async()
    
    def get_status(self) -> Dict[str, Any]:
        """Get service management status"""
        return {
            'initialized': self._initialized,
            'start_time': self._start_time,
            'uptime': time.time() - self._start_time,
            'registration': self.service_registry.get_registration_status(),
            'shutdown': self.shutdown_manager.get_shutdown_status(),
        }
    
    def get_service_info(self) -> Optional[Dict[str, Any]]:
        """Get service information"""
        return self.service_registry.get_service_info()
    
    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        if self.shutdown_manager.is_shutdown_in_progress:
            return False
        
        if not self.is_registered():
            return False
        
        return True
    
    def get_health_report(self) -> str:
        """Get health report"""
        status = self.get_status()
        service_info = self.get_service_info()
        
        report = [
            "Service Management Health Report:",
            "=" * 40,
            f"Overall Status: {'🟢 Healthy' if self.is_healthy() else '🔴 Unhealthy'}",
            f"Uptime: {status['uptime']:.1f}s",
        ]
        
        if service_info:
            report.extend([
                "",
                "Service Information:",
                f"  Name: {service_info['service_name']}",
                f"  Address: {service_info['ip']}:{service_info['port']}",
                f"  Group: {service_info['group_name']}",
                f"  Cluster: {service_info['cluster_name']}",
                f"  Weight: {service_info['weight']}",
                f"  Metadata: {service_info['metadata']}",
            ])
        
        # Add status of various components
        report.extend([
            "",
            "Registration Status:",
            f"  Registered: {'✅ Yes' if status['registration']['registered'] else '❌ No'}",
            f"  Retry Count: {status['registration']['retry_count']}/{status['registration']['max_retries']}",
            f"  Nacos Server: {status['registration']['nacos_server']}",
        ])
        
        report.extend([
            "",
            "Shutdown Status:",
            f"  Graceful: {'✅ Enabled' if status['shutdown']['graceful_enabled'] else '❌ Disabled'}",
            f"  In Progress: {'🛑 Yes' if status['shutdown'].get('shutdown_in_progress', False) else '✅ No'}",
            f"  Handlers: {status['shutdown']['handlers_count']}",
        ])
        
        return "\n".join(report)
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up service manager...")
                
        # Deregister service
        if self.is_registered():
            self.service_registry.deregister_service_sync()
        
        logger.info("Service manager cleanup completed")

