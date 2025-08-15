#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aiohttp Example
Shows how to use aiohttp with Nacos service discovery
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

# Import from nacos.auto.discovery.ext.aiohttp instead of aiohttp
from nacos.auto.discovery.ext.aiohttp import ClientSession, ClientTimeout


async def simple_requests_example():
    """Simple requests example"""
    logger.info("=== Simple requests example ===")
    
    try:
        # Create a client session using context manager (recommended)
        async with ClientSession() as session:
            # GET request
            async with session.get('http://user-service/api/users/1') as response:
                status = response.status
                text = await response.text()
                logger.info(f"GET Status: {status}")
                logger.info(f"GET Content: {text[:100]}...")
            
            # POST request
            data = {'name': 'John Doe', 'email': 'john@example.com'}
            async with session.post('http://user-service/api/users', json=data) as response:
                status = response.status
                logger.info(f"POST Status: {status}")
    except Exception as e:
        logger.error(f"Request failed: {e}")


async def custom_session_example():
    """Custom session example"""
    logger.info("\n=== Custom session example ===")
    
    try:
        # Create a session with custom settings
        timeout = ClientTimeout(total=30)
        async with ClientSession(timeout=timeout) as session:
            # Set custom headers for this request
            headers = {'User-Agent': 'NacosDiscoveryDemo/1.0'}
            
            async with session.get(
                'http://order-service/api/orders', 
                headers=headers
            ) as response:
                status = response.status
                text = await response.text()
                logger.info(f"Custom GET Status: {status}")
                logger.info(f"Custom GET Content: {text[:100]}...")
                
            # Binary response handling
            async with session.get('http://file-service/api/document') as response:
                binary_data = await response.read()
                logger.info(f"Binary response length: {len(binary_data)} bytes")
                
            # JSON response handling
            async with session.get('http://product-service/api/products') as response:
                json_data = await response.json()
                logger.info(f"JSON response: {str(json_data)[:100]}...")
    except Exception as e:
        logger.error(f"Custom session request failed: {e}")


async def advanced_requests_example():
    """Advanced requests example"""
    logger.info("\n=== Advanced requests example ===")
    
    try:
        async with ClientSession() as session:
            # Request with parameters
            params = {'status': 'active', 'sort': 'created_at'}
            async with session.get('http://order-service/api/orders', params=params) as response:
                logger.info(f"Params request Status: {response.status}")
            
            # Request with cookies
            cookies = {'session_id': 'test-session'}
            async with session.get(
                'http://auth-service/api/validate', 
                cookies=cookies
            ) as response:
                logger.info(f"Cookies request Status: {response.status}")
            
            # File upload using FormData
            from nacos.auto.discovery.ext.aiohttp import FormData
            form = FormData()
            form.add_field('file',
                          b'column1,column2\nvalue1,value2',
                          filename='report.csv',
                          content_type='text/csv')
            
            async with session.post('http://file-service/api/upload', data=form) as response:
                logger.info(f"File upload Status: {response.status}")
    except Exception as e:
        logger.error(f"Advanced request failed: {e}")


async def concurrent_requests_example():
    """Concurrent requests example"""
    logger.info("\n=== Concurrent requests example ===")
    
    try:
        async with ClientSession() as session:
            # Define a list of URLs to request
            urls = [
                'http://product-service/api/products/1',
                'http://product-service/api/products/2',
                'http://product-service/api/products/3',
            ]
            
            # Define fetch function
            async def fetch(url):
                try:
                    async with session.get(url) as response:
                        return {
                            'url': url,
                            'status': response.status,
                            'data': await response.text()
                        }
                except Exception as e:
                    return {'url': url, 'error': str(e)}
            
            # Create tasks for each request
            tasks = [fetch(url) for url in urls]
            
            # Execute requests concurrently
            results = await asyncio.gather(*tasks)
            
            # Process results
            for result in results:
                if 'error' in result:
                    logger.error(f"Request to {result['url']} failed: {result['error']}")
                else:
                    logger.info(f"Response from {result['url']}: Status {result['status']}")
    except Exception as e:
        logger.error(f"Concurrent requests failed: {e}")


async def streaming_example():
    """Streaming example"""
    logger.info("\n=== Streaming example ===")
    
    try:
        async with ClientSession() as session:
            async with session.get('http://file-service/api/large-file') as response:
                logger.info(f"Stream Status: {response.status}")
                
                # Read the stream in chunks
                total_bytes = 0
                async for chunk in response.content.iter_chunked(8192):
                    total_bytes += len(chunk)
                    # In a real application, you might write this to a file
                
                logger.info(f"Total streamed bytes: {total_bytes}")
    except Exception as e:
        logger.error(f"Streaming request failed: {e}")


async def retry_example():
    """Retry example"""
    logger.info("\n=== Retry example ===")
    
    async def retry_request(session, url, method='get', max_retries=3, **kwargs):
        """Request with retry logic"""
        from aiohttp.client_exceptions import ClientError
        
        for attempt in range(max_retries):
            try:
                request_method = getattr(session, method.lower())
                async with request_method(url, **kwargs) as response:
                    # Read the response here to handle any errors that might occur during reading
                    text = await response.text()
                    return {
                        'status': response.status,
                        'text': text,
                        'success': True
                    }
            except ClientError as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    return {'success': False, 'error': str(e)}
                
                # Wait before retry with exponential backoff
                await asyncio.sleep(1 * (2 ** attempt))
    
    try:
        async with ClientSession() as session:
            result = await retry_request(session, 'http://inventory-service/api/inventory')
            if result.get('success'):
                logger.info(f"Retry succeeded! Status: {result['status']}")
            else:
                logger.error(f"All retries failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"Retry mechanism failed: {e}")


async def main():
    """Main function"""
    try:
        logger.info("Starting aiohttp examples")
        
        # Run examples
        await simple_requests_example()
        await custom_session_example()
        await advanced_requests_example()
        await concurrent_requests_example()
        await streaming_example()
        await retry_example()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
            except Exception as e:
                logger.error(f"所有重试均失败: {e}")
            
        except Exception as e:
            logger.error(f"批处理请求失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
