#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urllib Example
Shows how to use urllib with Nacos service discovery
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

# Import from nacos.auto.discovery.ext.urllib instead of urllib.request
from nacos.auto.discovery.ext.urllib import (
    urlopen, 
    Request, 
    build_opener, 
    install_opener,
    HTTPHandler
)


def simple_urlopen_example():
    """Simple urlopen example"""
    logger.info("=== Simple urlopen example ===")
    
    try:
        # Note: user-service is the service name that will be resolved via Nacos
        with urlopen('http://nacos-flask-service/health') as response:
            content = response.read().decode('utf-8')
            logger.info(f"Status: {response.status}")
            logger.info(f"Content: {content[:100]}...")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Request failed: {e}")


def request_object_example():
    """Request object example"""
    logger.info("\n=== Request object example ===")
    
    try:
        # Create a Request object
        req = Request(
            'http://nacos-flask-service/health',
            headers={'Accept': 'application/json'}
        )
        
        # Open the request
        with urlopen(req) as response:
            content = response.read().decode('utf-8')
            logger.info(f"Status: {response.status}")
            logger.info(f"Content: {content[:100]}...")
    except Exception as e:
        logger.error(f"Request failed: {e}")


def custom_opener_example():
    """Custom opener example"""
    logger.info("\n=== Custom opener example ===")
    
    try:
        # Create a custom opener with additional handlers
        opener = build_opener(HTTPHandler())
        
        # Install it as the default opener (optional)
        install_opener(opener)
        
        # Use the opener
        with opener.open('http://nacos-flask-service/health') as response:
            content = response.read().decode('utf-8')
            logger.info(f"Status: {response.status}")
            logger.info(f"Content: {content[:100]}...")
    except Exception as e:
        logger.error(f"Request failed: {e}")


def post_request_example():
    """POST request example"""
    logger.info("\n=== POST request example ===")
    
    try:
        # Prepare data for POST request
        import json
        data = {'name': 'New Product', 'price': 29.99}
        data_bytes = json.dumps(data).encode('utf-8')
        
        # Create a Request object for POST
        req = Request(
            'http://nacos-flask-service/health', 
            data=data_bytes,
            headers={'Content-Type': 'application/json'}
        )
        
        # Send POST request
        with urlopen(req) as response:
            content = response.read().decode('utf-8')
            logger.info(f"POST Status: {response.status}")
            logger.info(f"POST Response: {content[:100]}...")
    except Exception as e:
        logger.error(f"POST request failed: {e}")


def retry_example():
    """Retry example"""
    logger.info("\n=== Retry example ===")
    
    def retry_request(url, max_retries=3):
        """Request with retry logic"""
        from urllib.error import URLError
        
        for attempt in range(max_retries):
            try:
                return urlopen(url)
            except URLError as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                
                import time
                wait_time = 1 * (2 ** attempt)  # exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
    
    try:
        with retry_request('http://nacos-flask-service/health') as response:
            content = response.read().decode('utf-8')
            logger.info(f"Retry succeeded! Content: {content[:100]}...")
    except Exception as e:
        logger.error(f"All retries failed: {e}")


def main():
    """Main function"""
    try:
        logger.info("Starting urllib examples")
        
        simple_urlopen_example()
        request_object_example()
        custom_opener_example()
        post_request_example()
        retry_example()
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
