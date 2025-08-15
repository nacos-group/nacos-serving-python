#!/usr/bin/env python3
"""
FastAPI示例应用
用于测试Nacos无侵入服务注册
"""

import os
import time
import logging

from typing import Dict, List, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("nacos.auto.discovery.ext.fastapi")
# 创建应用
app = FastAPI(
    title="FastAPI Demo",
    description="FastAPI Demo for Nacos Auto Register",
    version="1.0.0",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 记录启动时间
start_time = time.time()


class User(BaseModel):
    """用户模型"""
    id: int
    name: str
    email: str


class Product(BaseModel):
    """产品模型"""
    id: int
    name: str
    price: float


@app.get("/")
async def index() -> Dict[str, Any]:
    """首页"""
    return {
        'message': 'FastAPI Demo for Nacos Auto Register',
        'timestamp': time.time(),
        'service': 'fastapi-demo',
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    """健康检查"""
    return {
        'status': 'UP',
        'timestamp': time.time(),
        'service': 'fastapi-demo',
        'uptime': time.time() - start_time,
    }


@app.get("/info")
async def info() -> Dict[str, Any]:
    """服务信息"""
    return {
        'service': 'fastapi-demo',
        'version': '1.0.0',
        'framework': 'FastAPI',
        'python': os.environ.get('PYTHON_VERSION', '3.x'),
        'environment': os.environ.get('ENVIRONMENT', 'development'),
    }


@app.get("/api/users")
async def users() -> Dict[str, List[User]]:
    """用户列表"""
    return {
        'users': [
            User(id=1, name='Alice', email='alice@example.com'),
        ]
    }


@app.get("/api/products")
async def products() -> Dict[str, List[Product]]:
    """产品列表"""
    return {
        'products': [
            Product(id=1, name='Product A', price=99.99),
            Product(id=2, name='Product B', price=149.99),
            Product(id=3, name='Product C', price=199.99),
        ]
    }


#@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


if __name__ == "__main__":
    # 获取端口
    port = int(os.environ.get('PORT', 8000))
    
    print(f"Starting FastAPI demo app on port {port}...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)

