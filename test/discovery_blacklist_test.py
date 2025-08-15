# -*- coding: utf8 -*-

import asyncio
import socket
import threading
import unittest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from nacos.auto.discovery.core import BlacklistManager, LoadBalanceStrategy
from nacos.auto.discovery.nacos_discovery import NacosServiceDiscovery
from nacos.auto.discovery.core import ServiceInstance
from v2.nacos.naming.nacos_naming_service import NacosNamingService


class TestBlacklistManager(unittest.TestCase):
    """Test BlacklistManager functionality"""

    def setUp(self):
        self.blacklist_manager = BlacklistManager(ttl_seconds=2, probe_interval=1, connection_timeout=0.5)

    def tearDown(self):
        self.blacklist_manager.stop()
        time.sleep(0.5)  # Allow time for thread to stop

    def test_add_to_blacklist(self):
        """Test adding an instance to the blacklist"""
        # Add an instance to the blacklist
        self.blacklist_manager.add(ip="192.168.1.1", port=8080, reason="test")
        
        # Verify the instance is in the blacklist
        self.assertTrue(self.blacklist_manager.is_blacklisted("192.168.1.1", 8080))
        
        # Check the blacklist contains the instance
        all_blacklisted = self.blacklist_manager.get_all()
        self.assertEqual(len(all_blacklisted), 1)
        self.assertTrue("192.168.1.1:8080" in all_blacklisted)

    def test_clear_blacklist(self):
        """Test clearing the entire blacklist"""
        # Add multiple instances
        self.blacklist_manager.add(ip="192.168.1.3", port=8080, reason="test1")
        self.blacklist_manager.add(ip="192.168.1.4", port=8080, reason="test2")
        
        # Verify instances are in blacklist
        self.assertTrue(self.blacklist_manager.is_blacklisted("192.168.1.3", 8080))
        self.assertTrue(self.blacklist_manager.is_blacklisted("192.168.1.4", 8080))
        
        # Clear blacklist
        self.blacklist_manager.clear()
        
        # Verify blacklist is empty
        self.assertFalse(self.blacklist_manager.is_blacklisted("192.168.1.3", 8080))
        self.assertFalse(self.blacklist_manager.is_blacklisted("192.168.1.4", 8080))
        all_blacklisted = self.blacklist_manager.get_all()
        self.assertEqual(len(all_blacklisted), 0)

    def test_configuration_updates(self):
        """Test updating configuration parameters"""
        # Initial configuration
        self.assertEqual(self.blacklist_manager._ttl_seconds, 2)
        self.assertEqual(self.blacklist_manager._probe_interval, 1)
        self.assertEqual(self.blacklist_manager._connection_timeout, 0.5)
        
        # Update configuration
        self.blacklist_manager.set_ttl(5)
        self.blacklist_manager.set_probe_interval(2)
        self.blacklist_manager.set_connection_timeout(1.0)
        
        # Verify configuration updates
        self.assertEqual(self.blacklist_manager._ttl_seconds, 5)
        self.assertEqual(self.blacklist_manager._probe_interval, 2)
        self.assertEqual(self.blacklist_manager._connection_timeout, 1.0)

    @patch('asyncio.open_connection')
    async def _mock_probe_test(self, mock_open_connection, success=True):
        """Helper method for testing probe functionality with mocked connection"""
        if success:
            # Mock successful connection
            mock_writer = MagicMock()
            mock_writer.close.return_value = None  # close 本身同步
            # 修复：wait_closed 需可等待
            mock_writer.wait_closed = AsyncMock(return_value=None)
            mock_open_connection.return_value = (None, mock_writer)
        else:
            # Mock failed connection
            mock_open_connection.side_effect = ConnectionRefusedError("Connection refused")
        
        # Test the probe functionality
        result = await self.blacklist_manager._probe_instance("192.168.1.5", 8080)
        return result

    def test_probe_failure(self):
        """Test probe failure scenario"""
        # Run probe test with connection failure
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(self._mock_probe_test(success=False))
        loop.close()
        
        # Verify probe failed
        self.assertFalse(result)

    def test_probe_success(self):
        """Test probe success scenario"""
        # Run probe test with connection success
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(self._mock_probe_test(success=True))
        loop.close()
        
        # Verify probe succeeded
        self.assertTrue(result)


class TestBlacklistRecovery(unittest.TestCase):
    """Test BlacklistManager recovery functionality"""

    @patch('asyncio.open_connection')
    async def _setup_recovery_test(self, mock_open_connection, addresses_to_recover=None):
        """Helper method to set up and run a recovery test"""
        # Create a blacklist manager with controlled probe interval
        blacklist_manager = BlacklistManager(ttl_seconds=10, probe_interval=1, connection_timeout=0.5)
        
        # Add test instances to blacklist
        blacklist_manager.add(ip="192.168.1.10", port=8080, reason="test_recovery_1")
        blacklist_manager.add(ip="192.168.1.11", port=8080, reason="test_recovery_2")
        
        # Setup mock behavior for connections
        async def mock_connection(*args, **kwargs):
            ip = args[0]
            port = args[1]
            address = f"{ip}:{port}"
            
            # If this address should be recovered, return successful connection
            if addresses_to_recover and (ip, port) in addresses_to_recover:
                mock_writer = MagicMock()
                mock_writer.close.return_value = None
                # 修复：wait_closed 需为可等待协程
                mock_writer.wait_closed = AsyncMock(return_value=None)
                return (None, mock_writer)
            
            # Otherwise, fail the connection
            raise ConnectionRefusedError(f"Connection to {address} refused")
        
        mock_open_connection.side_effect = mock_connection
        
        await blacklist_manager._probe_instance("192.168.1.10", 8080)
        await blacklist_manager._probe_instance("192.168.1.11", 8080)
        # Let the probe thread run for a bit
        await asyncio.sleep(3)
        
        # Get blacklist state after probing
        result = {
            "192.168.1.10:8080": blacklist_manager.is_blacklisted("192.168.1.10", 8080),
            "192.168.1.11:8080": blacklist_manager.is_blacklisted("192.168.1.11", 8080)
        }
        
        # Clean up
        blacklist_manager.stop()
        return result

    def test_automatic_recovery(self):
        """Test automatic recovery of reachable instances"""
        # Set up recovery test where 192.168.1.10:8080 becomes reachable
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self._setup_recovery_test(addresses_to_recover=[("192.168.1.10", 8080)])
            )
            
            # Verify that 192.168.1.10:8080 was recovered (not blacklisted)
            self.assertFalse(result["192.168.1.10:8080"])
            
            # Verify that 192.168.1.11:8080 is still blacklisted
            self.assertTrue(result["192.168.1.11:8080"])
        finally:
            loop.close()

    def test_no_recovery_for_unreachable(self):
        """Test that unreachable instances remain blacklisted"""
        # Set up recovery test where no instances become reachable
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self._setup_recovery_test(addresses_to_recover=[])
            )
            
            # Verify that both instances remain blacklisted
            self.assertTrue(result["192.168.1.10:8080"])
            self.assertTrue(result["192.168.1.11:8080"])
        finally:
            loop.close()

    def test_selective_recovery(self):
        """Test that only reachable instances are recovered"""
        # Set up recovery test where only one instance becomes reachable
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Make only 192.168.1.11:8080 reachable
            result = loop.run_until_complete(
                self._setup_recovery_test(addresses_to_recover=[("192.168.1.11", 8080)])
            )
            
            # Verify that 192.168.1.10:8080 remains blacklisted
            self.assertTrue(result["192.168.1.10:8080"])
            
            # Verify that 192.168.1.11:8080 was recovered
            self.assertFalse(result["192.168.1.11:8080"])
        finally:
            loop.close()


class TestNacosServiceDiscoveryWithBlacklist(unittest.TestCase):
    """Test NacosServiceDiscovery integration with BlacklistManager"""

    def setUp(self):
        # Mock NacosNamingService for testing
        self.mock_nacos_client = MagicMock(spec=NacosNamingService)
        
        # Create service discovery with blacklist
        self.service_discovery = NacosServiceDiscovery(
            self.mock_nacos_client,
            blacklist_ttl=2,
            blacklist_probe_interval=1,
            blacklist_connection_timeout=0.5
        )

    def tearDown(self):
        # Ensure blacklist probe thread is stopped
        self.service_discovery.blacklist.stop()

    def test_blacklist_integration(self):
        """Test basic blacklist integration with NacosServiceDiscovery"""
        # Add instance to blacklist
        self.service_discovery.add_to_blacklist("192.168.1.20", 8080, "test_integration")
        
        # Verify instance is blacklisted
        self.assertTrue(self.service_discovery.blacklist.is_blacklisted("192.168.1.20", 8080))
        
        # Get blacklist from service discovery
        blacklist = self.service_discovery.get_blacklist()
        self.assertEqual(len(blacklist), 1)
        self.assertTrue("192.168.1.20:8080" in blacklist)
        
        # Clear blacklist
        self.service_discovery.clear_blacklist()
        
        # Verify blacklist is cleared
        self.assertFalse(self.service_discovery.blacklist.is_blacklisted("192.168.1.20", 8080))
        blacklist = self.service_discovery.get_blacklist()
        self.assertEqual(len(blacklist), 0)

    def test_instance_filtering(self):
        """Test that blacklisted instances are filtered during selection"""
        # Create test instances
        instances = [
            ServiceInstance(service_name="test-service", ip="192.168.1.21", port=8080),
            ServiceInstance(service_name="test-service", ip="192.168.1.22", port=8080),
            ServiceInstance(service_name="test-service", ip="192.168.1.23", port=8080)
        ]
        
        # Blacklist one instance
        self.service_discovery.add_to_blacklist("192.168.1.22", 8080, "test_filtering")
        
        # Mock get_instances to return our test instances
        self.service_discovery.get_instances_sync = MagicMock(return_value=instances)
        
        # Select an instance and verify it's not the blacklisted one
        selected_instance = self.service_discovery._select_instance(
            instances, "test-service", strategy=LoadBalanceStrategy.RANDOM
        )
        
        # Verify the selected instance is not the blacklisted one
        self.assertNotEqual(selected_instance.ip, "192.168.1.22")

    def test_emergency_fallback(self):
        """Test that when all instances are blacklisted, one is still returned"""
        # Create test instances
        instances = [
            ServiceInstance(service_name="test-service", ip="192.168.1.24", port=8080),
            ServiceInstance(service_name="test-service", ip="192.168.1.25", port=8080)
        ]
        
        # Blacklist all instances
        for instance in instances:
            self.service_discovery.add_to_blacklist(instance.ip, instance.port, "test_fallback")
        
        # Select an instance and verify one is returned despite all being blacklisted
        selected_instance = self.service_discovery._select_instance(
            instances, "test-service", strategy=LoadBalanceStrategy.RANDOM
        )
        
        # Verify an instance was returned
        self.assertIsNotNone(selected_instance)
        self.assertTrue(selected_instance.ip in ["192.168.1.24", "192.168.1.25"])


if __name__ == '__main__':
    unittest.main()
