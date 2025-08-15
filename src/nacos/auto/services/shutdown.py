# -*- coding: utf-8 -*-
"""
Graceful Shutdown Manager
Handles service deregistration and resource cleanup when application shuts down
"""

import atexit
import logging
import os
import signal
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..constants import NAMING_MODULE
from ...utils.tools import EnvironmentUtils

logger = logging.getLogger(NAMING_MODULE)


class ShutdownState(Enum):
    """Shutdown state enumeration"""
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class ShutdownConfig:
    """Shutdown configuration"""
    timeout: float = 30.0
    deregister_on_shutdown: bool = True
    graceful_enabled: bool = True
    force_exit: bool = False
    signal_timeout: float = 5.0  # Time window for repeated signals


@dataclass
class SignalInfo:
    """Signal information"""
    count: int = 0
    first_time: Optional[float] = None
    last_time: Optional[float] = None


class GracefulShutdownManager:
    """Graceful shutdown manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self._config = self._parse_config(config)
        self._state = ShutdownState.IDLE
        self._exit_requested = False
        self._signal_info: Dict[int, SignalInfo] = {}
        self._shutdown_handlers: List[Callable] = []
        self._lock = threading.RLock()
        
        if self._config.graceful_enabled:
            self._setup_signal_handlers()
            atexit.register(self._atexit_handler)
    
    @property
    def is_shutdown_in_progress(self) -> bool:
        """Check if shutdown is in progress"""
        with self._lock:
            return self._state == ShutdownState.IN_PROGRESS
    
    @property
    def is_exit_requested(self) -> bool:
        """Check if exit is requested"""
        return self._exit_requested
    
    def _parse_config(self, config: Dict[str, Any]) -> ShutdownConfig:
        """Parse configuration"""
        nacos_config = config.get('nacos', {})
        shutdown_config = nacos_config.get('shutdown', {})
        
        return ShutdownConfig(
            timeout=shutdown_config.get('timeout', 30.0),
            deregister_on_shutdown=shutdown_config.get('deregister', True),
            graceful_enabled=shutdown_config.get('graceful', True),
            force_exit=shutdown_config.get('force_exit', False),
            signal_timeout=shutdown_config.get('signal_timeout', 5.0)
        )
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers"""
        signals_to_handle = [
            getattr(signal, sig_name, None) 
            for sig_name in ['SIGTERM', 'SIGINT', 'SIGHUP']
            if hasattr(signal, sig_name)
        ]
        
        for sig in filter(None, signals_to_handle):
            try:
                signal.signal(sig, self._handle_signal)
            except (OSError, ValueError) as e:
                logger.warning(f"Cannot register handler for signal {sig}: {e}")
    
    def _handle_signal(self, signum: int, frame) -> None:
        """Handle system signal"""
        signal_name = self._get_signal_name(signum)
        current_time = time.time()
        
        # Update signal information
        signal_info = self._update_signal_info(signum, current_time)
        
        # Check if force exit is needed
        if self._should_force_exit(signal_info, current_time):
            self._force_exit(signal_name, signal_info.count)
            return
        
        logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        if signal_info.count > 1:
            logger.info(f"(Signal received {signal_info.count} times - press Ctrl+C again to force exit)")
        
        self._exit_requested = True
        
        # Execute graceful shutdown on first signal
        if signal_info.count == 1:
            self._start_graceful_shutdown()
    
    def _get_signal_name(self, signum: int) -> str:
        """Get signal name"""
        signal_names = {
            signal.SIGTERM: 'SIGTERM',
            signal.SIGINT: 'SIGINT',
        }
        
        if hasattr(signal, 'SIGHUP'):
            signal_names[signal.SIGHUP] = 'SIGHUP'
        
        return signal_names.get(signum, f'Signal {signum}')
    
    def _update_signal_info(self, signum: int, current_time: float) -> SignalInfo:
        """Update signal information"""
        if signum not in self._signal_info:
            self._signal_info[signum] = SignalInfo(first_time=current_time)
        
        signal_info = self._signal_info[signum]
        signal_info.count += 1
        signal_info.last_time = current_time
        
        return signal_info
    
    def _should_force_exit(self, signal_info: SignalInfo, current_time: float) -> bool:
        """Determine if force exit should occur"""
        if signal_info.count >= 3:
            return True
        
        if (signal_info.count == 2 and 
            signal_info.first_time and 
            (current_time - signal_info.first_time) < self._config.signal_timeout):
            return True
        
        return False
    
    def _force_exit(self, signal_name: str, count: int) -> None:
        """Force exit"""
        if count >= 3:
            logger.error(f"Received {signal_name} {count} times! Emergency exit!")
            exit_code = 2
        else:
            logger.error(f"Received {signal_name} again! Force exiting...")
            exit_code = 1
        
        try:
            os._exit(exit_code)
        except Exception:
            sys.exit(exit_code)
    
    def _start_graceful_shutdown(self) -> None:
        """Start graceful shutdown"""
        try:
            shutdown_thread = threading.Thread(
                target=self._threaded_shutdown, 
                daemon=True,
                name="GracefulShutdown"
            )
            shutdown_thread.start()
            shutdown_thread.join(timeout=self._config.timeout)
            
            if shutdown_thread.is_alive():
                logger.warning("Graceful shutdown timeout, continuing...")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        # Exit process handling for non-web environment
        if self._should_exit_process():
            self._exit_process()
    
    def _threaded_shutdown(self) -> None:
        """Execute shutdown logic in thread"""
        try:
            self.shutdown()
        except Exception as e:
            logger.error(f"Error in threaded shutdown: {e}")
    
    def _should_exit_process(self) -> bool:
        """Determine if process should exit"""
        return (not self._is_web_environment() and 
                (self._config.force_exit or len(self._signal_info) > 0))
    
    def _exit_process(self) -> None:
        """Exit process"""
        try:
            logger.info("Exiting application...")
            sys.exit(0)
        except SystemExit:
            pass
    
    @staticmethod
    def _is_web_environment() -> bool:
        """Check if running in web environment"""
        return EnvironmentUtils.is_web_environment()
    
    def _atexit_handler(self) -> None:
        """Program exit handler"""
        if self._state == ShutdownState.IDLE:
            logger.info("Application exiting, initiating graceful shutdown...")
            self.shutdown()
    
    @contextmanager
    def _shutdown_lock(self):
        """Shutdown lock context manager"""
        with self._lock:
            if self._state != ShutdownState.IDLE:
                yield False
                return
            
            self._state = ShutdownState.IN_PROGRESS
            yield True
            self._state = ShutdownState.COMPLETED
    
    def add_shutdown_handler(self, handler: Callable) -> None:
        """Add shutdown handler"""
        with self._lock:
            if handler not in self._shutdown_handlers:
                self._shutdown_handlers.append(handler)
    
    def remove_shutdown_handler(self, handler: Callable) -> None:
        """Remove shutdown handler"""
        with self._lock:
            if handler in self._shutdown_handlers:
                self._shutdown_handlers.remove(handler)
    
    def shutdown(self) -> None:
        """Execute graceful shutdown"""
        with self._shutdown_lock() as should_proceed:
            if not should_proceed:
                return
            
            logger.info("Starting graceful shutdown...")
            start_time = time.time()
            
            self._execute_shutdown_handlers()
            
            elapsed_time = time.time() - start_time
            logger.info(f"Graceful shutdown completed in {elapsed_time:.2f}s")
    
    def _execute_shutdown_handlers(self) -> None:
        """Execute shutdown handlers"""
        if not self._shutdown_handlers:
            return
        
        handler_timeout = min(
            self._config.timeout / len(self._shutdown_handlers), 
            10.0
        )
        
        for i, handler in enumerate(self._shutdown_handlers):
            handler_name = getattr(handler, '__name__', f'Handler {i+1}')
            
            try:
                logger.info(f"Executing {handler_name}...")
                self._execute_with_timeout(handler, handler_timeout)
            except Exception as e:
                logger.error(f"Error in shutdown handler {handler_name}: {e}")
    
    def _execute_with_timeout(self, handler: Callable, timeout: float) -> Any:
        """Execute handler with timeout"""
        result = []
        exception = []
        
        def target():
            try:
                result.append(handler())
            except Exception as e:
                exception.append(e)
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            logger.warning(f"Handler timeout after {timeout:.1f}s")
        
        if exception:
            raise exception[0]
        
        return result[0] if result else None
    
    def get_shutdown_status(self) -> Dict[str, Any]:
        """Get shutdown status"""
        return {
            'graceful_enabled': self._config.graceful_enabled,
            'deregister_on_shutdown': self._config.deregister_on_shutdown,
            'shutdown_timeout': self._config.timeout,
            'force_exit': self._config.force_exit,
            'state': self._state.value,
            'exit_requested': self._exit_requested,
            'handlers_count': len(self._shutdown_handlers),
            'is_web_environment': self._is_web_environment(),
            'signal_info': {
                sig: {'count': info.count, 'first_time': info.first_time}
                for sig, info in self._signal_info.items()
            },
        }
    
    def create_service_shutdown_handler(self, service_registry) -> Callable:
        """Create service shutdown handler"""
        def service_shutdown_handler():
            """Service shutdown handler"""
            try:
                if self._config.deregister_on_shutdown:
                    self._deregister_service(service_registry)
                else:
                    logger.info("Service deregistration disabled")
                    
            except Exception as e:
                logger.error(f"Error in service shutdown handler: {e}")
        
        service_shutdown_handler.__name__ = 'service_shutdown_handler'
        return service_shutdown_handler
    
    def _deregister_service(self, service_registry) -> None:
        """Deregister service"""
        logger.info("Deregistering service...")
        
        deregister_methods = [
            ('sync', lambda: service_registry.deregister_service_sync()),
            ('mock', lambda: self._mock_deregister(service_registry)),
            ('force', lambda: self._force_deregister(service_registry))
        ]
        
        for method_name, method in deregister_methods:
            try:
                if method():
                    logger.info("Service deregistered successfully")
                    return
            except Exception as e:
                logger.warning(f"{method_name.title()} deregister failed: {e}")
        
        logger.error("Failed to deregister service")
    
    def _mock_deregister(self, service_registry) -> bool:
        """Mock mode deregistration"""
        if hasattr(service_registry, '_mock_mode') and service_registry._mock_mode:
            service_registry.registered = False
            return True
        return False
    
    def _force_deregister(self, service_registry) -> bool:
        """Force deregister service"""
        try:
            with service_registry._lock:
                service_registry.registered = False
            logger.info("Service marked as deregistered (forced)")
            return True
        except Exception as e:
            logger.error(f"Force deregister failed: {e}")
            return False
    
    def get_shutdown_report(self) -> str:
        """Get shutdown status report"""
        status = self.get_shutdown_status()
        
        report_lines = [
            "Graceful Shutdown Status:",
            "=" * 30,
            f"Enabled: {'✅ Yes' if status['graceful_enabled'] else '❌ No'}",
            f"Deregister on Shutdown: {'✅ Yes' if status['deregister_on_shutdown'] else '❌ No'}",
            f"Timeout: {status['shutdown_timeout']}s",
            f"Handlers: {status['handlers_count']}",
            f"State: {status['state'].title()}",
            f"Web Environment: {'✅ Yes' if status['is_web_environment'] else '❌ No'}",
        ]
        
        return "\n".join(report_lines)

