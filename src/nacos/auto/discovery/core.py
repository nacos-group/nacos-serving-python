# -*- coding: utf-8 -*-
"""
Service Discovery Core Module
Defines core interfaces, data structures and utility functions
"""

import enum
import time
import threading
import logging
import asyncio
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic, Set, Tuple
import concurrent.futures

T = TypeVar('T')


class ServiceDiscoveryError(Exception):
    """Common service discovery exception"""
    pass


class NoAvailableInstanceError(ServiceDiscoveryError):
    """Exception for no available service instance"""
    
    def __init__(self, service_name: str, namespace: Optional[str] = None, message: Optional[str] = None):
        self.service_name = service_name
        self.namespace = namespace
        default_message = f"Service '{service_name}' {f'(namespace: {namespace})' if namespace else ''} has no available instances"
        super().__init__(message or default_message)


class LoadBalanceStrategy(enum.Enum):
    """Load balancing strategy"""
    ROUND_ROBIN = "round_robin"       # Round-robin strategy - select instances in sequence
    RANDOM = "random"                 # Random strategy - select instances randomly
    WEIGHTED_RANDOM = "weighted_random" # Weighted random - select instances based on their weight


class ServiceInstance:
    """Service instance class"""
    
    def __init__(self, service_name: str, ip: str, port: int, 
                 metadata: Optional[Dict[str, Any]] = None,
                 weight: float = 1.0, 
                 healthy: bool = True,
                 enabled: bool = True,
                 ephemeral: bool = True,
                 cluster_name: str = "DEFAULT",
                 namespace_id: str = ""):
        """
        Initialize service instance
        
        Args:
            service_name: Service name
            ip: Instance IP address
            port: Instance port
            metadata: Metadata dictionary
            weight: Weight value
            healthy: Whether instance is healthy
            enabled: Whether instance is enabled
            ephemeral: Whether instance is ephemeral
            cluster_name: Cluster name
            namespace_id: Namespace ID
        """
        self.service_name = service_name
        self.ip = ip
        self.port = port
        self.metadata = metadata or {}
        self.weight = weight
        self.healthy = healthy
        self.enabled = enabled
        self.ephemeral = ephemeral
        self.cluster_name = cluster_name
        self.namespace_id = namespace_id
        
    @property
    def address(self) -> str:
        """Get full address: ip:port"""
        return f"{self.ip}:{self.port}"
    
    @property
    def url_prefix(self) -> str:
        """Get URL prefix: http://ip:port"""
        return f"http://{self.ip}:{self.port}"
    
    def __str__(self) -> str:
        return f"{self.service_name}@{self.address} ({self.cluster_name})"
    
    def __repr__(self) -> str:
        return f"ServiceInstance(service_name='{self.service_name}', ip='{self.ip}', port={self.port}, " \
               f"weight={self.weight}, healthy={self.healthy}, cluster_name='{self.cluster_name}')"


class ServiceInstanceCache(Generic[T]):
    """Service instance cache"""
    
    def __init__(self):
        """
        Initialize cache
        """
        self._cache: Dict[str, Dict[str, Any]] = {}  # {key: {data, timestamp}}
    
    def get(self, key: str) -> Optional[T]:
        """
        Get cached data
        
        Args:
            key: Cache key
            
        Returns:
            Cached data, or None if not exists or expired
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
                
        return entry['data']
    
    def put(self, key: str, data: T) -> None:
        """
        Store cached data
        
        Args:
            key: Cache key
            data: Data to cache
        """
        self._cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        Clear cache
        
        Args:
            key: Specific key to clear, if None then clear all cache
        """
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]
    
    def set_ttl(self, ttl: int) -> None:
        """
        Set cache TTL
        
        Args:
            ttl: Cache time-to-live (seconds)
        """
        self._ttl = ttl


class BlacklistManager:
    """Blacklist manager for handling problematic service instances"""
    
    def __init__(self, ttl_seconds: int = 60, probe_interval: int = 3, 
                 connection_timeout: float = 0.5):
        """
        Initialize blacklist manager
        
        Args:
            ttl_seconds: Time-to-live in seconds for blacklist entries
            probe_interval: Interval in seconds for probing blacklisted instances
            connection_timeout: Timeout in seconds for probe connections
        """
        self._blacklist = {}  # {address: expiration_time}
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds
        self._probe_interval = probe_interval
        self._connection_timeout = connection_timeout
        self._logger = logging.getLogger(f"{__name__}.blacklist")
        self._running = False
        self._probe_thread = None
        self._addresses = set()  # {(ip, port)} for quick lookup
        
        # Start the probe thread
        self._start_probe_thread()
    
    def _start_probe_thread(self):
        """Start the background probe thread"""
        if self._probe_thread is not None and self._probe_thread.is_alive():
            return
            
        self._running = True
        self._probe_thread = threading.Thread(
            target=self._probe_loop,
            daemon=True,
            name="BlacklistProbeThread"
        )
        # self._probe_thread.start()
        self._logger.info(f"Started blacklist probe thread with interval: {self._probe_interval}s")
    
    def _probe_loop(self):
        """Background loop for probing blacklisted instances"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while self._running:
                # Get all addresses to probe
                addresses_to_probe = self._get_addresses_to_probe()
                
                if not addresses_to_probe:
                    time.sleep(self._probe_interval)
                    continue
                    
                self._logger.debug(f"Probing {len(addresses_to_probe)} blacklisted instances")
                
                # Run the probe coroutine and process recovered instances
                recovered = loop.run_until_complete(
                    self._probe_blacklisted_instances(addresses_to_probe)
                )
                
                # Remove recovered instances from blacklist
                if recovered:
                    self._remove_recovered_instances(recovered)
                
                # Sleep until next probe interval
                time.sleep(self._probe_interval)
        except Exception as e:
            self._logger.error(f"Error in blacklist probe thread: {e}", exc_info=True)
        finally:
            loop.close()
            self._logger.info("Blacklist probe thread stopped")
    
    def _remove_recovered_instances(self, recovered: List[Tuple[str, int]]) -> None:
        """
        Remove recovered instances from blacklist
        
        Args:
            recovered: List of recovered (ip, port) tuples
        """
        if not recovered:
            return
            
        self._logger.info(f"Recovered {len(recovered)} instances from blacklist: {recovered}")
        with self._lock:
            for ip, port in recovered:
                address = f"{ip}:{port}"
                if address in self._blacklist:
                    del self._blacklist[address]
                    self._addresses.discard((ip, port))

    def _get_addresses_to_probe(self) -> List[Tuple[str, int]]:
        """Get addresses to probe from blacklist"""
        with self._lock:
            # Make a copy to avoid holding the lock during probing
            return [(ip, port) for ip, port in self._addresses]
    
    async def _probe_blacklisted_instances(self, addresses: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """
        Asynchronously probe blacklisted instances
        
        Args:
            addresses: List of (ip, port) tuples to probe
            
        Returns:
            List of recovered (ip, port) tuples
        """
        tasks = []
        for ip, port in addresses:
            tasks.append(self._probe_instance(ip, port))
        
        # Wait for all probes to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect recovered instances
        recovered = []
        for i, (ip, port) in enumerate(addresses):
            if isinstance(results[i], bool) and results[i]:
                recovered.append((ip, port))
        
        return recovered
    
    async def _probe_instance(self, ip: str, port: int) -> bool:
        """
        Probe a single instance
        
        Args:
            ip: IP address
            port: Port
            
        Returns:
            True if instance is reachable, False otherwise
        """
        try:
            # Use asyncio to create TCP connection with timeout
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=self._connection_timeout
            )
            
            # Close the connection immediately
            writer.close()
            await writer.wait_closed()
            
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            # Instance still unreachable
            return False
        except Exception as e:
            self._logger.debug(f"Unexpected error during instance probe {ip}:{port}: {e}")
            return False
    
    def add(self, ip: str, port: int, reason: str = "connection_error") -> None:
        """
        Add an address to the blacklist
        
        Args:
            ip: IP address
            port: Port
            reason: Reason for blacklisting
        """
        address = f"{ip}:{port}"
        expiration = datetime.now() + timedelta(seconds=self._ttl_seconds)
        
        with self._lock:
            self._blacklist[address] = expiration
            self._addresses.add((ip, port))
            self._logger.warning(f"Added instance to blacklist: {address}, reason: {reason}, will expire at {expiration}")
        
        # Ensure probe thread is running
        if not self._running or (self._probe_thread and not self._probe_thread.is_alive()):
            self._start_probe_thread()
    
    def is_blacklisted(self, ip: str, port: int) -> bool:
        """
        Check if an address is blacklisted
        
        Args:
            ip: IP address
            port: Port
            
        Returns:
            Whether the address is blacklisted
        """
        address = f"{ip}:{port}"
        # If address not in blacklist, return False directly
        return address in self._blacklist

    def clear(self) -> None:
        """Clear the blacklist"""
        with self._lock:
            self._blacklist.clear()
            self._addresses.clear()
            self._logger.info("Blacklist has been cleared")
    
    def get_all(self) -> Dict[str, datetime]:
        """
        Get all blacklist entries
        
        Returns:
            Blacklist dictionary {address: expiration_time}
        """
        with self._lock:
            # Remove expired entries
            now = datetime.now()
            expired = [addr for addr, exp in self._blacklist.items() if now > exp]
            for addr in expired:
                del self._blacklist[addr]
                ip, port = addr.split(':')
                self._addresses.discard((ip, int(port)))
                
            # Return current valid blacklist entries
            return self._blacklist.copy()
            
    def set_ttl(self, ttl_seconds: int) -> None:
        """
        Set the time-to-live for blacklist entries
        
        Args:
            ttl_seconds: Time-to-live in seconds
        """
        self._ttl_seconds = ttl_seconds
        self._logger.info(f"Blacklist TTL has been set to {ttl_seconds} seconds")
    
    def set_probe_interval(self, interval: int) -> None:
        """
        Set the probe interval
        
        Args:
            interval: Probe interval in seconds
        """
        self._probe_interval = interval
        self._logger.info(f"Blacklist probe interval has been set to {interval} seconds")
    
    def set_connection_timeout(self, timeout: float) -> None:
        """
        Set the connection timeout for probes
        
        Args:
            timeout: Connection timeout in seconds
        """
        self._connection_timeout = timeout
        self._logger.info(f"Blacklist probe connection timeout has been set to {timeout} seconds")
    
    def stop(self):
        """Stop the probe thread"""
        self._running = False
        if self._probe_thread and self._probe_thread.is_alive():
            self._probe_thread.join(timeout=2.0)
            self._logger.info("Blacklist probe thread stopped")
    
    def __del__(self):
        """Ensure thread is stopped on deletion"""
        self.stop()

class ConnectionError(ServiceDiscoveryError):
    """Connection error exception, used to represent errors when connecting to service instances"""
    
    def __init__(self, service_name: str, ip: str, port: int, message: Optional[str] = None):
        self.service_name = service_name
        self.ip = ip
        self.port = port
        self.address = f"{ip}:{port}"
        default_message = f"Failed to connect to service '{service_name}' instance at {self.address}"
        super().__init__(message or default_message)
