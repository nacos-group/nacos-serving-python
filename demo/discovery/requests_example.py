#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
requests Example
Shows how to use requests with Nacos service discovery
"""

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

# Import from nacos.auto.discovery.ext.requests instead of requests
from nacos.auto.discovery.ext.requests import (
    get, post, put, delete, 
    session, request, 
    Session,
    Response
)


def simple_functions_example():
    """Simple functions example"""
    logger.info("=== Simple functions example ===")
    
    try:
        # GET request
        response = get('http://user-service/api/users/1')
        logger.info(f"GET Status: {response.status_code}")
        logger.info(f"GET Content: {response.text[:100]}...")
        
        # POST request
        data = {'name': 'John Doe', 'email': 'john@example.com'}
        response = post('http://user-service/api/users', json=data)
        logger.info(f"POST Status: {response.status_code}")
        logger.info(f"POST Content: {response.text[:100]}...")
        
        # PUT request
        update_data = {'name': 'John Smith', 'email': 'john@example.com'}
        response = put('http://user-service/api/users/1', json=update_data)
        logger.info(f"PUT Status: {response.status_code}")
        
        # DELETE request
        response = delete('http://user-service/api/users/2')
        logger.info(f"DELETE Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Request failed: {e}")


def session_example():
    """Session example"""
    logger.info("\n=== Session example ===")
    
    try:
        # Create a session for multiple requests
        with session() as s:
            # Session maintains cookies, headers, etc. across requests
            
            # First request - login
            login_data = {'username': 'testuser', 'password': 'password123'}
            response = s.post('http://auth-service/api/login', json=login_data)
            logger.info(f"Login Status: {response.status_code}")
            
            # Second request - get user data (session cookies are maintained)
            response = s.get('http://user-service/api/profile')
            logger.info(f"Profile Status: {response.status_code}")
            logger.info(f"Profile Content: {response.text[:100]}...")
    except Exception as e:
        logger.error(f"Session requests failed: {e}")


def custom_session_example():
    """Custom session example"""
    logger.info("\n=== Custom session example ===")
    
    try:
        # Create a custom session with specific settings
        with Session() as s:
            # Set custom headers for all requests in this session
            s.headers.update({
                'User-Agent': 'NacosDiscoveryDemo/1.0',
                'Accept-Language': 'en-US,en;q=0.9'
            })
            
            # Set custom timeout
            s.timeout = 5
            
            # Make requests with the custom session
            response = s.get('http://order-service/api/orders')
            logger.info(f"Custom session Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Custom session request failed: {e}")


def advanced_requests_example():
    """Advanced requests example"""
    logger.info("\n=== Advanced requests example ===")
    
    try:
        # Request with parameters
        params = {'status': 'active', 'sort': 'created_at'}
        response = get('http://order-service/api/orders', params=params)
        logger.info(f"Params request Status: {response.status_code}")
        
        # Request with headers
        headers = {'X-API-Key': 'test-key', 'Accept': 'application/json'}
        response = get('http://product-service/api/products', headers=headers)
        logger.info(f"Headers request Status: {response.status_code}")
        
        # Request with timeout
        try:
            response = get('http://inventory-service/api/inventory', timeout=1)
            logger.info(f"Timeout request Status: {response.status_code}")
        except Exception as e:
            logger.info(f"Timeout request expected error: {e}")
        
        # File upload
        files = {'file': ('report.csv', 'column1,column2\nvalue1,value2', 'text/csv')}
        response = post('http://file-service/api/upload', files=files)
        logger.info(f"File upload Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Advanced request failed: {e}")


def retry_example():
    """Retry example"""
    logger.info("\n=== Retry example ===")
    
    def retry_request(method, url, max_retries=3, **kwargs):
        """Request with retry logic"""
        import time
        from requests.exceptions import RequestException
        
        for attempt in range(max_retries):
            try:
                return request(method, url, **kwargs)
            except RequestException as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                
                wait_time = 1 * (2 ** attempt)  # exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
    
    try:
        response = retry_request('get', 'http://inventory-service/api/inventory')
        logger.info(f"Retry succeeded! Status: {response.status_code}")
    except Exception as e:
        logger.error(f"All retries failed: {e}")


def main():
    """Main function"""
    try:
        logger.info("Starting requests examples")
        
        # Run examples
        simple_functions_example()
        session_example()
        custom_session_example()
        advanced_requests_example()
        retry_example()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
