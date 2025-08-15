# -*- coding: utf-8 -*-
"""
Detector Module
Used for automatic detection of framework types, service information, etc.
"""

from .service_detector import ServiceDetector
from .framework_detector import FrameworkDetector

__all__ = ['ServiceDetector', 'FrameworkDetector']

