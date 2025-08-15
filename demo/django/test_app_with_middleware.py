#!/usr/bin/env python3

import os
import sys
import django

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# 初始化Django
django.setup()

from django.core.wsgi import get_wsgi_application
from nacos.auto.middleware.wsgi import inject_wsgi_middleware


def main():
    """启动带中间件的Django应用"""
    # 获取WSGI应用
    application = get_wsgi_application()
    
    # 注入中间件
    application = inject_wsgi_middleware(application)
    
    # 获取端口
    port = int(os.environ.get('PORT', 8002))
    
    print(f"Starting Django demo app with middleware on port {port}...")
    
    # 使用Gunicorn或者简单的WSGI服务器
    try:
        import gunicorn.app.wsgiapp
        
        # 使用Gunicorn启动
        sys.argv = [
            'gunicorn',
            '--bind', f'0.0.0.0:{port}',
            '--workers', '1',
            'myproject.wsgi:application'
        ]
        gunicorn.app.wsgiapp.run()
        
    except ImportError:
        # 如果没有Gunicorn，使用简单的WSGI服务器
        from wsgiref.simple_server import make_server
        
        server = make_server('0.0.0.0', port, application)
        print(f"Django app with middleware running on http://0.0.0.0:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
