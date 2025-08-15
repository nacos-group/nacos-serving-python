#!/usr/bin/env python3
"""
Django示例应用
用于测试Nacos无侵入服务注册
"""

import os
import sys
import django

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# 初始化Django
django.setup()

from django.core.wsgi import get_wsgi_application
from django.core.management import execute_from_command_line


def main():
    """启动Django应用"""
    # 获取端口
    port = os.environ.get('PORT', '8001')
    
    print(f"Starting Django demo app on port {port}...")
    
    # 使用Django的runserver命令
    sys.argv = ['manage.py', 'runserver', f'0.0.0.0:{port}']
    try:
        execute_from_command_line(sys.argv)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error starting Django app: {e}")


if __name__ == "__main__":
    main()
