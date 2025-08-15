#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error Handling Example
Shows how to handle errors with Nacos service discovery
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
from nacos.auto.discovery.ext import configure, LoadBalanceStrategy
configure(
    server_address=os.environ.get("NACOS_SERVER", "localhost:8848"),
    cache_ttl=5  # Short cache time for testing
)


async def handle_urllib_errors():
    """Handle errors with urllib"""
    logger.info("=== urllib error handling ===")
    
    # Import from nacos.auto.discovery.ext.urllib
    from nacos.auto.discovery.ext.urllib import urlopen
    from urllib.error import URLError, HTTPError
    
    # 1. Handle non-existent service
    try:
        response = urlopen('http://non-existent-service/api/test')
    except URLError as e:
        logger.info(f"Expected URLError for non-existent service: {e}")
    
    # 2. Handle HTTP errors
    try:
        response = urlopen('http://user-service/api/error/404')
    except HTTPError as e:
        logger.info(f"Expected HTTPError: {e.code} {e.reason}")
    except URLError as e:
        logger.info(f"URLError: {e}")
    
    # 3. Implement retry logic
    def retry_request(url, max_retries=3):
        """Request with retry logic"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return urlopen(url)
            except (URLError, HTTPError) as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                last_error = e
                
                import time
                time.sleep(0.5)  # Short delay for testing
        
        # Re-raise the last error if all retries failed
        if last_error:
            raise last_error
    
    try:
        response = retry_request('http://user-service/api/users/1')
        logger.info(f"Retry succeeded with status: {response.status}")
    except Exception as e:
        logger.error(f"All retries failed: {e}")


def handle_requests_errors():
    """Handle errors with requests"""
    logger.info("\n=== requests error handling ===")
    
    # Import from nacos.auto.discovery.ext.requests
    from nacos.auto.discovery.ext.requests import get, post, session
    from nacos.auto.discovery.ext.requests import RequestException, HTTPError, Timeout, ConnectionError
    
    # 1. Handle different types of exceptions
    try:
        response = get('http://user-service/api/timeout', timeout=0.001)
    except Timeout:
        logger.info("Expected Timeout exception")
    except ConnectionError:
        logger.info("Connection error")
    except RequestException as e:
        logger.info(f"Request exception: {e}")
    
    # 2. Handle HTTP error status codes
    try:
        response = get('http://user-service/api/users/999')
        # Raise an exception if the response contains an HTTP error status code
        response.raise_for_status()
    except HTTPError as e:
        logger.info(f"Expected HTTP error: {e}")
    
    # 3. Custom error handling with session
    with session() as s:
        try:
            response = s.get('http://user-service/api/error')
            if response.status_code >= 400:
                logger.info(f"Error response with status code: {response.status_code}")
                logger.info(f"Error response content: {response.text[:100]}")
            else:
                logger.info(f"Success response with status code: {response.status_code}")
        except RequestException as e:
            logger.info(f"Request failed: {e}")


async def handle_httpx_errors():
    """Handle errors with httpx"""
    logger.info("\n=== httpx error handling ===")
    
    # Import from nacos.auto.discovery.ext.httpx
    from nacos.auto.discovery.ext.httpx import AsyncClient, Client
    from nacos.auto.discovery.ext.httpx import (
        HTTPError, RequestError, ConnectError, ReadTimeout, 
        ConnectTimeout, HTTPStatusError
    )
    
    # 1. Synchronous error handling
    try:
        with Client(timeout=0.001) as client:
            response = client.get('http://user-service/api/timeout')
    except ConnectTimeout:
        logger.info("Expected Connect Timeout")
    except ReadTimeout:
        logger.info("Read Timeout")
    except HTTPError as e:
        logger.info(f"HTTP error: {e}")
    
    # 2. Asynchronous error handling
    try:
        async with AsyncClient() as client:
            response = await client.get('http://non-existent-service/api/test')
    except ConnectError:
        logger.info("Expected Connect Error for non-existent service")
    except RequestError as e:
        logger.info(f"Request error: {e}")
    
    # 3. HTTP status error handling
    try:
        async with AsyncClient() as client:
            response = await client.get('http://user-service/api/error/404')
            # Raise exception for HTTP status errors
            response.raise_for_status()
    except HTTPStatusError as e:
        logger.info(f"Expected HTTP Status error: {e}")
    
    # 4. Advanced error handling with retry
    async def retry_request(url, method='GET', max_retries=3, **kwargs):
        """Async request with retry logic"""
        async with AsyncClient() as client:
            request_method = getattr(client, method.lower())
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = await request_method(url, **kwargs)
                    response.raise_for_status()
                    return response
                except (ConnectError, ReadTimeout, HTTPStatusError) as e:
                    logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                    last_error = e
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # Short delay for testing
            
            # Re-raise the last error if all retries failed
            if last_error:
                raise last_error
    
    try:
        response = await retry_request('http://user-service/api/users/1')
        logger.info(f"Retry succeeded with status: {response.status_code}")
    except Exception as e:
        logger.error(f"All retries failed: {e}")


async def handle_aiohttp_errors():
    """Handle errors with aiohttp"""
    logger.info("\n=== aiohttp error handling ===")
    
    # Import from nacos.auto.discovery.ext.aiohttp
    from nacos.auto.discovery.ext.aiohttp import ClientSession, ClientTimeout
    from nacos.auto.discovery.ext.aiohttp import (
        ClientError, ClientConnectorError, ClientResponseError,
        ClientConnectionError, ClientPayloadError, ClientTimeout
    )
    
    # 1. Basic error handling
    try:
        async with ClientSession() as session:
            async with session.get('http://non-existent-service/api/test') as response:
                text = await response.text()
    except ClientConnectorError:
        logger.info("Expected ClientConnectorError for non-existent service")
    except ClientError as e:
        logger.info(f"Client error: {e}")
    
    # 2. Timeout handling
    try:
        timeout = ClientTimeout(total=0.001)
        async with ClientSession(timeout=timeout) as session:
            async with session.get('http://user-service/api/timeout') as response:
                text = await response.text()
    except asyncio.TimeoutError:
        logger.info("Expected TimeoutError")
    except ClientError as e:
        logger.info(f"Client error: {e}")
    
    # 3. Response error handling
    try:
        async with ClientSession() as session:
            async with session.get('http://user-service/api/error/500') as response:
                # Check status and raise for errors
                if response.status >= 400:
                    logger.info(f"HTTP Error: {response.status}")
                    response.raise_for_status()  # This will raise ClientResponseError
                text = await response.text()
    except ClientResponseError as e:
        logger.info(f"Expected ClientResponseError: {e}")
    
    # 4. Advanced error handling with retry
    async def retry_request(url, method='get', max_retries=3, **kwargs):
        """Async request with retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with ClientSession() as session:
                    request_method = getattr(session, method.lower())
                    async with request_method(url, **kwargs) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.warning(f"HTTP error {response.status}: {error_text[:100]}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(0.5)  # Short delay for testing
                                continue
                            response.raise_for_status()
                        
                        return await response.text()
            except (ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                last_error = e
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # Short delay for testing
        
        # Re-raise the last error if all retries failed
        if last_error:
            raise last_error
    
    try:
        text = await retry_request('http://user-service/api/users/1')
        logger.info(f"Retry succeeded with response length: {len(text)}")
    except Exception as e:
        logger.error(f"All retries failed: {e}")


async def test_different_load_balancing_strategies():
    """Test different load balancing strategies"""
    logger.info("\n=== Testing load balancing strategies ===")
    
    from nacos.auto.discovery.ext import configure
    from nacos.auto.discovery.ext.requests import get
    
    # Test Round Robin strategy
    logger.info("Testing ROUND_ROBIN strategy...")
    configure(server_address="localhost:8848", cache_ttl=5)
    
    for i in range(5):
        try:
            response = get('http://user-service/api/info')
            logger.info(f"Request {i+1}: {response.text[:30]}...")
        except Exception as e:
            logger.error(f"Request {i+1} failed: {e}")
    
    # Test Random strategy
    logger.info("\nTesting RANDOM strategy...")
    configure(server_address="localhost:8848", cache_ttl=5)
    
    for i in range(5):
        try:
            response = get('http://user-service/api/info')
            logger.info(f"Request {i+1}: {response.text[:30]}...")
        except Exception as e:
            logger.error(f"Request {i+1} failed: {e}")
    
    # Test Weighted Random strategy
    logger.info("\nTesting WEIGHTED_RANDOM strategy...")
    configure(server_address="localhost:8848", cache_ttl=5)
    
    for i in range(5):
        try:
            response = get('http://user-service/api/info')
            logger.info(f"Request {i+1}: {response.text[:30]}...")
        except Exception as e:
            logger.error(f"Request {i+1} failed: {e}")


async def main():
    """Main function"""
    try:
        logger.info("Starting error handling examples")
        
        # Run error handling examples
        await handle_urllib_errors()
        handle_requests_errors()
        await handle_httpx_errors()
        await handle_aiohttp_errors()
        
        # Test load balancing strategies
        await test_different_load_balancing_strategies()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
