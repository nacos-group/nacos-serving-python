#!/usr/bin/env python3
"""
Flask示例应用
用于测试Nacos无侵入服务注册
"""

import os
import time
import nacos.auto.registration.enabled # 导入时自动启用 (方法2)

from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/')
def index():
    """首页"""
    return jsonify({
        'message': 'Flask Demo for Nacos Auto Register',
        'timestamp': time.time(),
        'service': 'flask-demo',
    })


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({
        'status': 'UP',
        'timestamp': time.time(),
        'service': 'flask-demo',
        'uptime': time.time() - app.start_time,
    })


@app.route('/info')
def info():
    """服务信息"""
    return jsonify({
        'service': 'flask-demo',
        'version': '1.0.0',
        'framework': 'Flask',
        'python': os.environ.get('PYTHON_VERSION', '3.x'),
        'environment': os.environ.get('ENVIRONMENT', 'development'),
    })


@app.route('/api/users')
def users():
    """用户列表"""
    return jsonify({
        'users': [
            {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
            {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
            {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'},
        ]
    })


@app.route('/api/products')
def products():
    """产品列表"""
    return jsonify({
        'products': [
            {'id': 1, 'name': 'Product A', 'price': 99.99},
            {'id': 2, 'name': 'Product B', 'price': 149.99},
            {'id': 3, 'name': 'Product C', 'price': 199.99},
        ]
    })


@app.before_request
def before_first_request():
    """首次请求前的处理"""
    app.start_time = time.time()
    print(f"First request received at {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    # 记录启动时间
    app.start_time = time.time()
    
    # 获取端口
    port = int(os.environ.get('PORT', 5001))
    
    print(f"Starting Flask demo app on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)

