# -*- coding: utf-8 -*-
"""
Simple urllib Example
Shows how to use the drop-in replacement for urllib.request.urlopen
"""

import logging
from nacos.auto.discovery.ext.urllib import urlopen

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    try:
        # Configure Nacos (optional - will use defaults if not called)
        # This would normally be at the start of your application
        from nacos.auto.discovery.ext import configure
        configure(server_address="localhost:8848")
        
        # Use standard urlopen with service name instead of hostname
        with urlopen('http://user-service/api/users/1') as response:
            data = response.read().decode('utf-8')
            print(f"Status: {response.status}")
            print(f"Data: {data}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
