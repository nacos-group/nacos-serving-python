#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
httpx Example
Shows how to use httpx with Nacos service discovery
"""

import asyncio
import logging
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Nacos service discovery (needed just once per application)
from nacos.auto.discovery.ext import configure
configure(server_address=os.environ.get("NACOS_SERVER", "localhost:8848"))

# Import from nacos.auto.discovery.ext.httpx instead of httpx
from nacos.auto.discovery.ext.httpx import (
    get, post, put, delete,
    Client, AsyncClient,
    stream, request
)


def sync_functions_example():
    """Synchronous functions example"""
    logger.info("=== Synchronous functions example ===")
    
    try:
        # GET request
        response = get('http://user-service/api/users/1')
        logger.info(f"GET Status: {response.status_code}")
        logger.info(f"GET Content: {response.text[:100]}...")
        
        # POST request
        data = {'name': 'John Doe', 'email': 'john@example.com'}
        response = post('http://user-service/api/users', json=data)
        logger.info(f"POST Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Request failed: {e}")


def sync_client_example():
    """Synchronous client example"""
    logger.info("\n=== Synchronous client example ===")
    
    try:
        # Create a client with custom settings
        with Client(timeout=10.0, follow_redirects=True) as client:
            # GET request
            response = client.get('http://order-service/api/orders')
            logger.info(f"Client GET Status: {response.status_code}")
            
            # POST request with client
            data = {'product_id': 123, 'quantity': 2}
            response = client.post('http://order-service/api/orders', json=data)
            logger.info(f"Client POST Status: {response.status_code}")
            
            # PUT request with client
            update_data = {'quantity': 3}
            response = client.put('http://order-service/api/orders/1', json=update_data)
            logger.info(f"Client PUT Status: {response.status_code}")
            
            # DELETE request with client
            response = client.delete('http://order-service/api/orders/2')
            logger.info(f"Client DELETE Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Client request failed: {e}")


async def async_client_example():
    """Asynchronous client example"""
    logger.info("\n=== Asynchronous client example ===")
    
    try:
        # Create an async client with custom settings
        async with AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Async GET request
            response = await client.get('http://product-service/api/products')
            logger.info(f"Async GET Status: {response.status_code}")
            logger.info(f"Async GET Content: {response.text[:100]}...")
            
            # Async POST request
            data = {'name': 'New Product', 'price': 99.99}
            response = await client.post('http://product-service/api/products', json=data)
            logger.info(f"Async POST Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Async client request failed: {e}")


async def concurrent_requests_example():
    """Concurrent requests example"""
    logger.info("\n=== Concurrent requests example ===")
    
    try:
        # Create an async client
        async with AsyncClient() as client:
            # Define a list of URLs to request
            urls = [
                'http://product-service/api/products/1',
                'http://product-service/api/products/2',
                'http://product-service/api/products/3',
            ]
            
            # Create tasks for each request
            tasks = []
            for url in urls:
                tasks.append(client.get(url))
            
            # Execute requests concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process responses
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    logger.error(f"Request to {urls[i]} failed: {response}")
                else:
                    logger.info(f"Response from {urls[i]}: Status {response.status_code}")
    except Exception as e:
        logger.error(f"Concurrent requests failed: {e}")


def streaming_example():
    """Streaming example"""
    logger.info("\n=== Streaming example ===")
    
    try:
        with Client() as client:
            with client.stream('GET', 'http://file-service/api/large-file') as response:
                logger.info(f"Stream Status: {response.status_code}")
                
                # Read the stream in chunks
                total_bytes = 0
                for chunk in response.iter_bytes(chunk_size=8192):
                    total_bytes += len(chunk)
                    # In a real application, you might write this to a file
                
                logger.info(f"Total streamed bytes: {total_bytes}")
    except Exception as e:
        logger.error(f"Streaming request failed: {e}")


async def main():
    """Main function"""
    try:
        logger.info("Starting httpx examples")
        
        # Run synchronous examples
        sync_functions_example()
        sync_client_example()
        
        # Run asynchronous examples
        await async_client_example()
        await concurrent_requests_example()
        
        # Run streaming example
        streaming_example()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
    
    import httpx
    
    # 1. 同步自定义传输层
    logger.info("同步自定义传输层:")
    try:
        # 创建传输层
        transport = ServiceDiscoveryTransport(
            service_discovery,
            strategy=LoadBalanceStrategy.WEIGHTED_RANDOM
        )
        
        # 创建客户端
        client = httpx.Client(transport=transport)
        
        # 发送请求
        response = client.get('http://inventory-service/api/inventory')
        logger.info(f"自定义传输层GET响应状态码: {response.status_code}")
        
        client.close()
    except Exception as e:
        logger.error(f"同步自定义传输层失败: {e}")
    
    # 2. 异步自定义传输层
    logger.info("\n异步自定义传输层:")
    try:
        # 创建传输层
        transport = AsyncServiceDiscoveryTransport(
            service_discovery,
            strategy=LoadBalanceStrategy.ROUND_ROBIN
        )
        
        # 创建客户端
        async with httpx.AsyncClient(transport=transport) as client:
            # 发送请求
            response = await client.get('http://inventory-service/api/inventory')
            logger.info(f"异步自定义传输层GET响应状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"异步自定义传输层失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
