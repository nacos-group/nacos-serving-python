# -*- coding: utf-8 -*-
"""
Nacos Service Discovery Implementation
Implements service discovery functionality using Nacos SDK
"""

import logging
import random
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from v2.nacos import NacosNamingService, ListInstanceParam, \
        Instance, SubscribeServiceParam
from ...utils.tools import run_async_safely
from ..constants import NAMING_MODULE

from .core import ServiceInstance, LoadBalanceStrategy, \
        ServiceDiscoveryError, NoAvailableInstanceError, \
        ServiceInstanceCache, BlacklistManager

logger = logging.getLogger(NAMING_MODULE)


class NacosServiceDiscovery:
    """Nacos service discovery class"""
    
    def __init__(self, nacos_client: NacosNamingService, 
                 empty_protection: bool = True,
                 namespace_id: str = "", 
                 group_name: str = "DEFAULT_GROUP",
                 blacklist_ttl: int = 60,
                 blacklist_probe_interval: int = 3,
                 blacklist_connection_timeout: float = 0.5):
        """
        Initialize Nacos service discovery
        
        Args:
            nacos_client: Nacos naming service client
            empty_protection: Whether to enable empty protection (prevent returning empty instance list)
            namespace_id: Namespace ID
            group_name: Group name
            blacklist_ttl: Time-to-live in seconds for blacklist entries
            blacklist_probe_interval: Interval in seconds for probing blacklisted instances
            blacklist_connection_timeout: Timeout in seconds for probe connections
        """
        self.nacos_client = nacos_client
        self.namespace_id = namespace_id
        self.group_name = group_name
        self.cache = ServiceInstanceCache()
        self._round_robin_counters: Dict[str, int] = {}
        self._lock = threading.Lock()
        self.instances = None
        # Track subscribed services to avoid duplicate subscriptions
        self._subscribed_services = set()
        self._empty_protection = empty_protection
        # Initialize blacklist manager
        self.blacklist = BlacklistManager(
            ttl_seconds=blacklist_ttl,
            probe_interval=blacklist_probe_interval,
            connection_timeout=blacklist_connection_timeout
        )
    
    async def get_instances_async(self, service_name: str, 
                          cluster_names: Optional[List[str]] = None) -> List[ServiceInstance]:
        """
        Asynchronously get service instance list
        
        Args:
            service_name: Service name
            cluster_names: Cluster name list
        
        Returns:
            List of service instances
        
        Raises:
            ServiceDiscoveryError: Service discovery error
        """
        logger.info(f"Getting instances for service {service_name} with clusters {cluster_names}")
        cache_key = self._get_cache_key(service_name, cluster_names)
        
        # Try to get from cache
        cached_instances = self.cache.get(cache_key)
        if cached_instances is not None:
            logger.debug(f"Retrieved instances for {service_name} from cache, count: {len(cached_instances)}")
            return cached_instances
        
        logger.info(f"Cache miss for {service_name}, fetching from Nacos server")   
        # Get instances from Nacos server for first discovery
        try:
            # Check if service is already subscribed
            if cache_key not in self._subscribed_services:
                logger.info(f"First discovery of service {service_name}, subscribing to service changes")
                # Subscribe to service changes
                await self._subscribe_service_async(service_name, cluster_names)
                self._subscribed_services.add(cache_key)
            
            param = ListInstanceParam(
                service_name=service_name,
                group_name=self.group_name,
                healthy_only=True
            )

            logger.info(f"Fetching instances for {service_name} from Nacos with params: {param}")
            nacos_instances = await self.nacos_client.list_instances(param)

            logger.info(f"Retrieved instances for {service_name} from Nacos, count: {len(nacos_instances)}")
            instances = self._convert_instances(nacos_instances, service_name)
            
            # Store in cache
            self.cache.put(cache_key, instances)
            logger.debug(f"Updated cache for {service_name}, new instance count: {len(instances)}")
            
            return instances
            
        except Exception as e:
            logger.error(f"Failed to get service instances from Nacos: {e}", exc_info=True)
            raise ServiceDiscoveryError(f"Failed to get service '{service_name}' instances: {str(e)}")
    
    def get_instances_sync(self, service_name: str, 
                   cluster_names: Optional[List[str]] = None) -> List[ServiceInstance]:
        """
        Synchronously get service instance list
        
        Args:
            service_name: Service name
            cluster_names: Cluster name list
        
        Returns:
            List of service instances
        
        Raises:
            ServiceDiscoveryError: Service discovery error
        """
        cache_key = self._get_cache_key(service_name, cluster_names)
        
        # Try to get from cache
        cached_instances = self.cache.get(cache_key)
        if cached_instances is not None:
            logger.debug(f"Retrieved instances for {service_name} from cache, count: {len(cached_instances)}")
            return cached_instances
        
        # Cache doesn't exist, use run_async_safely to get instances asynchronously
        logger.info(f"Cache miss for {service_name}, fetching from Nacos server")
        try:
            instances = run_async_safely(
                lambda: self.get_instances_async(service_name, cluster_names)
            )
            return instances or []
        except Exception as e:
            logger.error(f"Failed to get service instances from Nacos: {e}", exc_info=True)
            raise ServiceDiscoveryError(f"Failed to get service '{service_name}' instances: {str(e)}")

    async def get_instance_async(self, service_name: str, 
                        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                        cluster_names: Optional[List[str]] = None) -> ServiceInstance:
        """
        Asynchronously get a single service instance (using load balancing)
        
        Args:
            service_name: Service name
            strategy: Load balancing strategy
            cluster_names: Cluster name list
        
        Returns:
            Single service instance
        
        Raises:
            NoAvailableInstanceError: No available service instance
        """
        # Try to get instances from cache first
        instances = await self.get_instances_async(service_name, cluster_names)
        return self._select_instance(instances, service_name, strategy)

    def get_instance_sync(self, service_name: str, 
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 cluster_names: Optional[List[str]] = None) -> ServiceInstance:
        """
        Synchronously get a single service instance (using load balancing)
        
        Args:
            service_name: Service name
            strategy: Load balancing strategy
            cluster_names: Cluster name list
        
        Returns:
            Single service instance
        
        Raises:
            NoAvailableInstanceError: No available service instance
        """
        # Try to get instances from cache first
        cache_key = self._get_cache_key(service_name, cluster_names)
        cached_instances = self.cache.get(cache_key)
        
        if cached_instances is not None:
            logger.debug(f"Selecting instance for {service_name} from cached instances")
            return self._select_instance(cached_instances, service_name, strategy)
        
        # Cache miss, fetch instances using async method
        logger.info(f"No cached instances for {service_name}, fetching from Nacos server")
        
        async def sync_get_instance_caller():
            return await self.get_instance_async(service_name, 
                                                 strategy, 
                                                 cluster_names)
        
        try:
            instance = run_async_safely(sync_get_instance_caller)
            return instance
        except Exception as e:
            logger.error(f"Failed to get service instance from Nacos: {e}", exc_info=True)
            raise ServiceDiscoveryError(f"Failed to get service '{service_name}' instance: {str(e)}")

    async def _subscribe_service_async(self, service_name: str, cluster_names: Optional[List[str]] = None):
        """
        Subscribe to service changes to receive updates
        
        Args:
            service_name: Service name
            cluster_names: Cluster names
        """
        cache_key = self._get_cache_key(service_name, cluster_names)
        
        try:
            # Define callback function to handle service changes
            async def service_changed_callback(instances: Dict[str, Any]):
                logger.info(f"Received service change notification for {service_name}")
                if self._empty_protection and not instances:
                    logger.warning(f"EMPTY PROTECTION ENABLED: No instances available for {service_name}, skipping cache update")
                    return
                
                self.cache.put(cache_key, instances)
                logger.debug(f"Updated cache for {service_name} due to service change, new count: {len(instances)}")
            
            param = SubscribeServiceParam(
                service_name=service_name,
                group_name=self.group_name,
                clusters=cluster_names or [],
                subscribe_callback=service_changed_callback
            )

            # Subscribe to service changes
            await self.nacos_client.subscribe(param)
            logger.info(f"Successfully subscribed to service changes for {service_name}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to service {service_name}: {e}", exc_info=True)
            # Don't raise exception to allow get_instances to continue

    def _get_cache_key(self, service_name: str, cluster_names: Optional[List[str]] = None) -> str:
        """
        Generate cache key for service
        
        Args:
            service_name: Service name
            cluster_names: Cluster names
        
        Returns:
            Cache key string
        """
        clusters_str = ""
        if cluster_names:
            if isinstance(cluster_names, list):
                clusters_str = ",".join(sorted(cluster_names))
            else:
                clusters_str = str(cluster_names)
        
        return f"{self.namespace_id}:{self.group_name}:{service_name}:{clusters_str}"

    def _select_instance(self, instances: List[ServiceInstance], service_name: str, 
                        strategy: LoadBalanceStrategy) -> ServiceInstance:
        """
        Select service instance based on load balancing strategy
        
        Args:
            instances: Service instance list
            service_name: Service name
            strategy: Load balancing strategy
        
        Returns:
            Selected service instance
        
        Raises:
            NoAvailableInstanceError: No available service instance
        """
        # Filter out blacklisted instances
        available_instances = [
            instance for instance in instances 
            if not self.blacklist.is_blacklisted(instance.ip, instance.port)
        ]
        
        if not available_instances:
            # If no available instances after filtering, 
            # check if there were any before filtering, lucky for the emergency fallback
            if instances:
                logger.warning(f"All {len(instances)} instances for service '{service_name}' are blacklisted, temporarily allowing blacklisted instances")
                available_instances = instances  # Use blacklisted instances in emergency situations
            else:
                raise NoAvailableInstanceError(service_name, self.namespace_id)
        
        if len(available_instances) == 1:
            return available_instances[0]
        
        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin_select(available_instances, service_name)
        elif strategy == LoadBalanceStrategy.WEIGHTED_RANDOM:
            return self._weighted_random_select(available_instances)
        else:
            # Default to random selection
            return self._random_select(available_instances)

    def _round_robin_select(self, instances: List[ServiceInstance], service_name: str) -> ServiceInstance:
        """Round-robin selection strategy"""
        with self._lock:
            counter = self._round_robin_counters.get(service_name, 0)
            instance = instances[counter % len(instances)]
            self._round_robin_counters[service_name] = counter + 1
        return instance

    def _random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Random selection strategy"""
        return random.choice(instances)

    def _weighted_random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted random selection strategy"""
        # Calculate total weight
        total_weight = sum(instance.weight for instance in instances)
        
        # Select based on weight
        choice = random.uniform(0, total_weight)
        current_weight = 0
        for instance in instances:
            current_weight += instance.weight
            if choice <= current_weight:
                return instance
        
        # Default to last instance
        return instances[-1]

    def _convert_instances(self, nacos_instances: List[Instance], service_name: str) -> List[ServiceInstance]:
        """Convert Nacos instances to ServiceInstance objects"""
        result = []
        for instance in nacos_instances:
            if not instance.enabled or not instance.healthy:
                continue
                
            result.append(ServiceInstance(
                service_name=service_name,
                ip=instance.ip,
                port=instance.port,
                metadata=instance.metadata,
                weight=instance.weight,
                healthy=instance.healthy,
                enabled=instance.enabled,
                ephemeral=instance.ephemeral,
                namespace_id=self.namespace_id
            ))
                
        return result
    
    def clear_cache(self, service_name: Optional[str] = None) -> None:
        """
        Clear cache
        
        Args:
            service_name: Service name, if None then clear all cache
        """
        if service_name is None:
            self.cache.clear()
            logger.info("Cleared all service instance caches")
        else:
            # Clear all related cache for the specified service
            cache_key = self._get_cache_key(service_name)
            self.cache.clear(cache_key)
            logger.info(f"Cleared cache for service {service_name}")

    def set_cache_ttl(self, ttl: int) -> None:
        """
        Set cache TTL
        
        Args:
            ttl: Cache time-to-live (seconds)
        """
        self.cache.set_ttl(ttl)
        logger.debug(f"Set cache TTL to {ttl} seconds")
        """
        Set cache TTL
        
        Args:
            ttl: Cache time-to-live (seconds)
        """
        self.cache.set_ttl(ttl)
        logger.debug(f"Set cache TTL to {ttl} seconds")
    
    def add_to_blacklist(self, ip: str, port: int, reason: str = "connection_error") -> None:
        """
        Add an instance to the blacklist
        
        Args:
            ip: Instance IP
            port: Instance port
            reason: Reason for blacklisting
        """
        self.blacklist.add(ip, port, reason)
    
    def get_blacklist(self) -> Dict[str, datetime]:
        """
        Get current blacklist
        
        Returns:
            Blacklist dictionary
        """
        return self.blacklist.get_all()
    
    def clear_blacklist(self) -> None:
        """Clear the blacklist"""
        self.blacklist.clear()
    
    def set_blacklist_ttl(self, ttl_seconds: int) -> None:
        """
        Set blacklist TTL
        
        Args:
            ttl_seconds: TTL in seconds
        """
        self.blacklist.set_ttl(ttl_seconds)

    def set_blacklist_probe_interval(self, interval: int) -> None:
        """
        Set blacklist probe interval
        
        Args:
            interval: Probe interval in seconds
        """
        self.blacklist.set_probe_interval(interval)
    
    def set_blacklist_connection_timeout(self, timeout: float) -> None:
        """
        Set blacklist probe connection timeout
        
        Args:
            timeout: Connection timeout in seconds
        """
        self.blacklist.set_connection_timeout(timeout)
