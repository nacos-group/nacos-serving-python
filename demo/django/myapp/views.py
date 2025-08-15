import os
import time
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# 记录启动时间
start_time = time.time()


@method_decorator(csrf_exempt, name='dispatch')
class IndexView(View):
    """首页"""
    
    def get(self, request):
        return JsonResponse({
            'message': 'Django Demo for Nacos Auto Register',
            'timestamp': time.time(),
            'service': 'django-demo',
        })


@method_decorator(csrf_exempt, name='dispatch')
class HealthView(View):
    """健康检查"""
    
    def get(self, request):
        return JsonResponse({
            'status': 'UP',
            'timestamp': time.time(),
            'service': 'django-demo',
            'uptime': time.time() - start_time,
        })


@method_decorator(csrf_exempt, name='dispatch')
class InfoView(View):
    """服务信息"""
    
    def get(self, request):
        return JsonResponse({
            'service': 'django-demo',
            'version': '1.0.0',
            'framework': 'Django',
            'python': os.environ.get('PYTHON_VERSION', '3.x'),
            'environment': os.environ.get('ENVIRONMENT', 'development'),
        })


@method_decorator(csrf_exempt, name='dispatch')
class UsersView(View):
    """用户列表"""
    
    def get(self, request):
        return JsonResponse({
            'users': [
                {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
                {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
                {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'},
            ]
        })


@method_decorator(csrf_exempt, name='dispatch')
class ProductsView(View):
    """产品列表"""
    
    def get(self, request):
        return JsonResponse({
            'products': [
                {'id': 1, 'name': 'Product A', 'price': 99.99},
                {'id': 2, 'name': 'Product B', 'price': 149.99},
                {'id': 3, 'name': 'Product C', 'price': 199.99},
            ]
        })
