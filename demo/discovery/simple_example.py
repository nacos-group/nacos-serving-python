#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Examples
Basic usage examples showing the simplicity of integrating Nacos service discovery
"""
import logging
import os
import trace
import threading
import sys
import psutil
from nacos.utils.tools import run_async_safely

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename="/tmp/nacos.log",
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Nacos service discovery once at the start of your application


def urllib_example():
    """Simple urllib example"""
    #from urllib.request import urlopen
    from nacos.auto.discovery.ext.urllib import urlopen
    
    logger.info("=== urllib example ===")
    try:
        with urlopen('http://nacos-flask-service/health') as response:
            data = response.read().decode('utf-8')
            logger.info(f"Status: {response.status}")
            logger.info(f"Data: {data[:100]}...")
    except Exception as e:
        logger.error(f"Error: {e}")


def requests_example():
    """Simple requests example"""
    # from requests import get, post
    from nacos.auto.discovery.ext.requests import get, post
    
    logger.info("\n=== requests example ===")
    try:
        # GET request
        response = get('http://nacos-flask-service/health')
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Data: {response.json()}")
        
        # POST request
        data = {'name': 'John Doe', 'email': 'john@example.com'}
        response = post('http://nacos-flask-service/health', json=data)
        logger.info(f"POST Status: {response.status_code}")
        logger.info(f"POST Response: {response.text}")
    except Exception as e:
        logger.error(f"Error: {e}")


def httpx_sync_example():
    """Simple httpx synchronous example"""
    # from httpx import Client
    from nacos.auto.discovery.ext.httpx import Client
    
    logger.info("\n=== httpx sync example ===")
    try:
        with Client() as client:
            response = client.get('http://nacos-flask-service/health')
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Data: {response.json()}")
    except Exception as e:
        logger.error(f"Error: {e}")


async def httpx_async_example():
    """Simple httpx asynchronous example"""
    # from httpx import AsyncClient
    from nacos.auto.discovery.ext.httpx import AsyncClient
    
    logger.info("\n=== httpx async example ===")
    try:
        async with AsyncClient() as client:
            response = await client.get('http://nacos-flask-service/health')
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Data: {response.json()}")
    except Exception as e:
        logger.error(f"Error: {e}")


async def aiohttp_example():
    """Simple aiohttp example"""
    # from aiohttp import ClientSession
    from nacos.auto.discovery.ext.aiohttp import ClientSession
    
    logger.info("\n=== aiohttp example ===")
    try:
        async with ClientSession() as session:
            async with session.get('http://nacos-flask-service/health') as response:
                data = await response.json()
                logger.info(f"Status: {response.status}")
                logger.info(f"Data: {data}")
    except Exception as e:
        logger.error(f"Error: {e}")


async def main():
    """Main function"""
    
    # Run synchronous examples
    urllib_example()
    requests_example()
    httpx_sync_example()
    
    # Run asynchronous examples
    await httpx_async_example()
    await aiohttp_example()


count = 0
async def async_test():
    logger.info(f"Running async test {count} ...")

    await try_sync_test()

async def try_sync_test():
    global count
    if count<1:
        count += 1
        return sync_test()

    logger.info(f"Exiting: Async test {count} completed.")
    return count

def sync_test():
    global count
    """Synchronous test function"""
    
    logger.info(f"Running sync test {count}...")
    return run_async_safely(async_test, timeout=30)


def main_sync():
    """Main synchronous function"""
    b = sync_test()
    logger.info(f"Sync test result: {b}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    # main_sync()

    # logger.info("\n\n=== ======== sync calls example ===\n\n")
    # urllib_example()
    # requests_example()
    # httpx_sync_example()
