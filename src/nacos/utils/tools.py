# pyright: reportAssignmentType=false
"""
Common Utility Module
Contains various public utility methods
"""

import asyncio
import json
import os
import re
import socket
import sys
import time
import logging
import urllib.parse
import concurrent.futures

from functools import lru_cache
from typing import Any, Dict, List, Optional, Union
from threading import current_thread

import psutil
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, Future
from v2.nacos.common.nacos_exception import NacosException, \
    INVALID_INTERFACE_ERROR, INVALID_PARAM

# Setup logger
from ..auto.constants import NAMING_MODULE

logger = logging.getLogger(NAMING_MODULE)


class NetworkUtils:
    """Network Utilities"""
    
    @staticmethod
    @lru_cache(maxsize=1)
    def get_local_ip() -> str:
        """Get local IP address"""
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        return addr.address
            raise NacosException(INVALID_INTERFACE_ERROR, "no valid non-loopback IPv4 interface found")
        except socket.gaierror as err:
            raise NacosException(INVALID_INTERFACE_ERROR, f"failed to query local IP address, error: {str(err)}")
    
    @staticmethod
    def is_valid_port(port: Union[int, str]) -> bool:
        """Check if port number is valid"""
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False


class EnvironmentUtils:
    """Environment Detection Utilities"""
    web_modules = ['fastapi', 'django', 'flask', 'starlette', 'tornado']
    @staticmethod
    def is_web_environment() -> bool:
        """Check if running in a web environment (like FastAPI, Django, etc.)"""
        if current_thread().daemon:
            return True
        
        return any([mod in sys.modules for mod in EnvironmentUtils.web_modules])


class StringUtils:
    """String Processing Utilities"""
    
    @staticmethod
    def is_blank(s: Optional[str]) -> bool:
        """Check if string is empty or contains only whitespace"""
        return not s or not s.strip()
    
    @staticmethod
    def is_not_blank(s: Optional[str]) -> bool:
        """Check if string is not empty"""
        return not StringUtils.is_blank(s)
    
    @staticmethod
    def url_encode(s: str, encoding: str = 'utf-8') -> str:
        """URL encode"""
        return urllib.parse.quote(s.encode(encoding), safe='')
    
    @staticmethod
    def url_decode(s: str, encoding: str = 'utf-8') -> str:
        """URL decode"""
        return urllib.parse.unquote(s, encoding=encoding)
    
    @staticmethod
    def match_pattern(text: str, pattern: str) -> bool:
        """Pattern matching"""
        try:
            return bool(re.match(pattern, text))
        except re.error:
            return False


class TimeUtils:
    """Time Processing Utilities"""
    
    @staticmethod
    def current_millis() -> int:
        """Get current timestamp in milliseconds"""
        return int(round(time.time() * 1000))
    
    @staticmethod
    def current_seconds() -> int:
        """Get current timestamp in seconds"""
        return int(time.time())
    
    @staticmethod
    def format_timestamp(timestamp: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format timestamp"""
        if timestamp > 1e10:  # Millisecond timestamp
            timestamp = timestamp / 1000
        return time.strftime(fmt, time.localtime(timestamp))


class JsonUtils:
    """JSON Processing Utilities"""
    
    @staticmethod
    def to_json_string(obj: Union[BaseModel, Dict, List, Any]) -> Optional[str]:
        """Convert object to JSON string"""
        try:
            if isinstance(obj, BaseModel):
                return obj.model_dump_json()
            return json.dumps(obj, default=JsonUtils._json_serializer, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(f"Error serializing object to JSON: {e}")
            return None
    
    @staticmethod
    def from_json_string(json_str: str) -> Optional[Dict]:
        """Convert JSON string to object"""
        try:
            return json.loads(json_str)
        except (TypeError, ValueError) as e:
            logger.error(f"Error deserializing JSON string: {e}")
            return None
    
    @staticmethod
    def _json_serializer(obj: Any) -> Any:
        """JSON serializer"""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)


class CollectionUtils:
    """Collection Processing Utilities"""
    
    @staticmethod
    def is_empty(collection) -> bool:
        """Check if collection is empty"""
        return not collection
    
    @staticmethod
    def is_not_empty(collection) -> bool:
        """Check if collection is not empty"""
        return bool(collection)
    
    @staticmethod
    def safe_get(collection: Union[List, Dict], key: Union[int, str], default=None):
        """Safely get element from collection"""
        try:
            return collection[key]
        except (KeyError, IndexError, TypeError):
            return default
    
    @staticmethod
    def merge_dicts(*dicts: Dict, prefer_first: bool = True) -> Dict:
        """Merge multiple dictionaries"""
        result = {}
        for d in dicts:
            if not d:
                continue
            for k, v in d.items():
                if not (prefer_first and k in result):
                    result[k] = v
        return result
    
    @staticmethod
    def add_prefix_to_keys(d: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """Add prefix to dictionary keys"""
        if not d:
            return d
        return {f"{prefix}{k}": v for k, v in d.items() if k.strip()}


executor = ThreadPoolExecutor(max_workers=1, 
                              thread_name_prefix="NacosEventLoopingExecutor-")

class AsyncUtils:
    """Async Processing Utilities"""
    
    @staticmethod
    def current_loop_running() -> Any:
        """Check if there is a running event loop"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            return None
    
    @staticmethod
    def run_async_safely(async_func, timeout: float = 30.0, use_thread: bool = None):
        """Safely run async function"""
        
        future = AsyncUtils._run_in_thread(async_func)

        return future.result(timeout=timeout) 

    
    @staticmethod
    def _run_in_thread(async_func) -> Any:
        """Run async function in new thread"""
        
        future = Future()

        def done_callback(task):
            try:
                result = task.result()
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        # start the event loop in a separate thread to keep the
        # loop running, otherwise it may block by the future.result() call
        executor.submit(AsyncUtils._run_in_new_loop, 
                        async_func,
                        done_callback)
        
        return future  # Set a timeout for the future
    
    @staticmethod
    def _run_in_new_loop(async_func, done_callback):
        """Run async function in new event loop"""
        inside_web = EnvironmentUtils.is_web_environment()
        loop = AsyncUtils.current_loop_running()

        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        def run_event_loop(loop):
            try:
                logger.info("Event loop for async task started")
                loop.run_forever()
            except Exception as e:
                logger.error(f"Error in event loop: {e}")
            finally:
                logger.info("Event loop for async task stopped")
                try:
                    loop.close()
                except Exception as e:
                    pass

        try:
            
            # Create task and add callback
            task = loop.create_task(async_func())
            task.add_done_callback(done_callback)

            logger.info("Starting event loop for async task")

            if loop.is_running():
                return 
                        
            if inside_web:
                # start the event loop in a separate thread to keep the
                # Nacos health check still working
                from threading import Thread
                thread = Thread(target=run_event_loop, args=(loop,),
                                daemon=True,
                                name="NacosEventLoopingThread")
                thread.start()
            else:
                # for script tasks, just run until complete
                # run the event loop until the task is complete
                loop.run_until_complete(task)

            
        except Exception as e:
            logger.error(f"❌ Error running async function: {e}")
            raise NacosException(INVALID_INTERFACE_ERROR, f"Error running async function: {e}")
        finally:
            # loop.close()
            pass


class ValidationUtils:
    """Validation Utilities"""
    
    @staticmethod
    def validate_required(value: Any, name: str) -> None:
        """Validate required parameter"""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise NacosException(INVALID_PARAM, f"{name} cannot be empty")
    
    @staticmethod
    def validate_pattern(value: str, pattern: str, name: str) -> None:
        """Validate format"""
        if not StringUtils.match_pattern(value, pattern):
            raise NacosException(INVALID_PARAM, f"{name} format is invalid")


class FileUtils:
    """File Operation Utilities"""
    
    @staticmethod
    def ensure_dir(path: str) -> bool:
        """Ensure directory exists"""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    @staticmethod
    def safe_remove(file_path: str) -> bool:
        """Safely remove file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to remove file {file_path}: {e}")
            return False
    
    @staticmethod
    def get_file_lock_name(service_name: str, ip: str, port: int) -> str:
        """Generate file lock name"""
        return f"nacos_service_{service_name}_{ip}_{port}.lock"


class ProcessUtils:
    """Process Related Utilities"""
    
    @staticmethod
    def is_process_running(pid: int) -> bool:
        """Check if process is running"""
        try:
            # Send signal 0 to check if process exists
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    @staticmethod
    def get_current_pid() -> int:
        """Get current process ID"""
        return os.getpid()
    
    @staticmethod
    def get_process_info() -> Dict[str, Any]:
        """Get current process information"""
        import platform
        return {
            'pid': os.getpid(),
            'platform': platform.platform(),
            'cwd': os.getcwd(),
            'timestamp': TimeUtils.current_millis()
        }
    
    @staticmethod
    def is_legal_injection():
        """Check if already injected"""
        injection_flag = os.getenv(_INJECTION_FLAG)
        if not injection_flag:
            return True
        
        current_pid = str(ProcessUtils.get_current_pid())

        return injection_flag == current_pid

    @staticmethod
    def mark_injection():
        """Mark as injected"""
        os.environ[_INJECTION_FLAG] = str(ProcessUtils.get_current_pid())

    @staticmethod
    def try_inject_environment_label():
        """Main function with injection check"""
        if not ProcessUtils.is_legal_injection():
            logger.warning("⚠️  Environment already injected by another process, skipping.")
            return False
        
        ProcessUtils.mark_injection()
        return True
        

# Environment variable flag
_INJECTION_FLAG = "_NACOS_MODULE_INJECTED_"


# Convenient module-level functions
def get_local_ip() -> str:
    """Get local IP address"""
    return NetworkUtils.get_local_ip()


def is_web_environment() -> bool:
    """Check if in web environment"""
    return EnvironmentUtils.is_web_environment()


def current_millis() -> int:
    """Get current timestamp (milliseconds)"""
    return TimeUtils.current_millis()


def to_json_string(obj: Any) -> Optional[str]:
    """Convert object to JSON string"""
    return JsonUtils.to_json_string(obj)


def from_json_string(json_str: str) -> Optional[Dict]:
    """Convert JSON string to object"""
    return JsonUtils.from_json_string(json_str)


def run_async_safely(async_func, 
                     timeout: float = 30.0, 
                     use_thread: bool = None) -> Any:
    """Safely run async function"""
    return AsyncUtils.run_async_safely(async_func, timeout, use_thread)


def validate_required(value: Any, name: str) -> None:
    """Validate required parameter"""
    return ValidationUtils.validate_required(value, name)


def is_blank(s: Optional[str]) -> bool:
    """Check if string is empty"""
    return StringUtils.is_blank(s)


def is_not_blank(s: Optional[str]) -> bool:
    """Check if string is not empty"""
    return StringUtils.is_not_blank(s)


def ensure_dir(path: str) -> bool:
    """Ensure directory exists"""
    return FileUtils.ensure_dir(path)


def safe_remove(file_path: str) -> bool:
    """Safely remove file"""
    return FileUtils.safe_remove(file_path)


def is_process_running(pid: int) -> bool:
    """Check if process is running"""
    return ProcessUtils.is_process_running(pid)


def get_current_pid() -> int:
    """Get current process ID"""
    return ProcessUtils.get_current_pid()
