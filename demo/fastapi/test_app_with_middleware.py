#!/usr/bin/env python3
import sys
sys.path.append('/home/ubuntu')

from fastapi import FastAPI
import time
import os

# 创建应用
app = FastAPI()

@app.get("/")
async def index():
    return {
        'message': 'FastAPI Middleware Demo',
        'timestamp': time.time(),
    }

@app.get("/health")
async def health():
    return {
        'status': 'UP',
        'timestamp': time.time(),
    }
@app.get("/api/users")
async def users():
    """用户列表"""
    return {
        'users': [
        ]
    }

if __name__ == '__main__':
    # 导入并注入中间件
    from nacos.auto.middleware.asgi import inject_asgi_middleware
        
    # 注入中间件
    app = inject_asgi_middleware(app)
    
    # 启动应用
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
