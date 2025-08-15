#!/usr/bin/env python3

from flask import Flask, jsonify
import time
import os

# 创建应用
app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'message': 'Flask Middleware Demo',
        'timestamp': time.time(),
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'UP',
        'timestamp': time.time(),
    })

if __name__ == '__main__':
    # 导入并注入中间件
    
    from nacos.auto.middleware.wsgi import inject_wsgi_middleware
    
    # 注入中间件
    app = inject_wsgi_middleware(app)
    
    # 启动应用
    app.run(host='0.0.0.0', port=5004)
