# -*- coding: utf-8 -*-
"""
Injector Module
Implements non-invasive service registration injection
"""

from .injector import CLIInjector
from .import_hook import ImportHook

__all__ = ['CLIInjector', 'ImportHook']

