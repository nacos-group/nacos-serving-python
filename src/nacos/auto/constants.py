# -*- coding: utf-8 -*-
"""
Constants for Nacos Auto Registration
"""

# Logger module name for auto registration
NAMING_MODULE = "naming"

# Configuration file names
CONFIG_FILE_NAMES = ['nacos.yaml', 
                     'nacos.yml', 
                     'application.yaml', 
                     'application.yml']

# Default configuration values
DEFAULT_NACOS_SERVER = 'localhost:8848'
DEFAULT_GROUP = 'DEFAULT_GROUP'
DEFAULT_CLUSTER = 'default'
DEFAULT_WEIGHT = 1.0

# Request processing thresholds
SLOW_REQUEST_THRESHOLD = 1.0  # seconds
API_PATH_PREFIX = '/api/'
