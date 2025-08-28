# nacos-serving-python v0.1.0

## 概述

`nacos-serving-python` 聚焦 Web / HTTP 客户端的 服务注册、服务发现、配置获取 无侵入增强：

1. Flask / Django / FastAPI 三种自动注册方式：
   a) 命令行：`python -m nacos.auto.registration <app.py>`
   b) 导入触发：`import nacos.auto.registration.enabled`
   c) WSGI 中间件：`from nacos.auto.middleware.wsgi import inject_wsgi_middleware`
2. 为 urllib / requests / httpx / aiohttp 提供逻辑服务名直连能力：`http://<service-name>/path`

底层使用异步 gRPC（Nacos 2.x）以获得实时推送与更低开销。

---

## 安装并运行
```bash
# 1. install the library
pip install nacos-serving-python

# 2. cd to your project root and run

# 3. run the auto-registration CLI
python -m nacos.auto.registration --nacos-server 127.0.0.1:8848 --service-name demoservice app.py
```

---

## 快速概念
1. 构建客户端配置（地址 / 命名空间 / 凭证）
2. 创建 Config 与 Naming 客户端
3. 选择任一自动注册方式
4. 使用适配器直接按服务名发起请求
5. 优雅关闭（注销实例）

> 详细示例见 demo 目录；按需求查看。

---

## 自动注册

| 方式 | 示例 | 适用 | 侵入性 |
|------|------|------|--------|
| 命令行 | `python -m nacos.auto.registration app.py --nacos-server 127.0.0.1:8848 --service-name demo.api` | 脚本/容器启动 | 无 |
| 导入触发 | `import nacos.auto.registration.enabled` | 小改造 | 低 |
| WSGI 中间件 | `inject_wsgi_middleware(app)` | 自定义生命周期 | 低 |

WSGI 注入示例：
```python
from flask import Flask
from nacos.auto.middleware.wsgi import inject_wsgi_middleware
app = Flask(__name__)
inject_wsgi_middleware(app)
app.run()
```

配置文件（`nacos.yaml`）参考 demo，放置于当前工作目录。

---

## 启动参数 (CLI)

命令：
```bash
python -m nacos.auto.registration app.py [参数...]
```

| 参数 | 示例 | 说明 |
|------|------|------|
| --nacos-server | 127.0.0.1:8848 | Nacos 服务端地址（可多） |
| --namespace | public | 命名空间 ID |
| --service-name | demo.api | 服务名称 |
| --service-port | 8000 | 指定端口（可自动探测） |
| --service-ip | 127.0.0.1 | 指定 IP（可自动探测） |
| --service-group | DEFAULT_GROUP | 服务分组 |
| --service-cluster | default | 集群名 |
| --service-weight | 1.0 | 权重 |
| --metadata key=val | version=1.0.0 | 可重复，附加元数据 |
| --register-on-startup | (flag) | 启动即注册 |
| --register-on-request | (flag) | 首次请求时注册 |
| --no-auto-register | (flag) | 禁止自动注册 |
| --retry-times | 3 | 注册重试次数 |
| --retry-interval | 2 | 重试间隔秒 |
| --heartbeat-interval | 5 | 心跳间隔秒 |
| --heartbeat-timeout | 5 | 心跳超时秒 |
| --graceful-shutdown | (flag) | 启用优雅关闭 |
| --shutdown-timeout | 10 | 关闭等待秒 |
| --deregister-on-exit | (flag) | 退出时主动注销 |
| --log-level | INFO | 日志级别 |
| --log-file | /path/xxx.log | 输出文件 |
| --empty-protection | true/false | 空实例保护 |
| --help |  | 帮助信息 |

环境变量覆盖（优先级低于 CLI）：
NACOS_SERVER / NACOS_NAMESPACE / NACOS_SERVICE_NAME / NACOS_SERVICE_PORT / NACOS_SERVICE_IP

---

## nacos.yaml 字段

| 区域 | 字段 | 含义 |
|------|------|------|
| nacos | server | 服务器地址 |
| nacos | namespace | 命名空间 |
| service | name | 服务名 |
| service | ip / port | 实例监听地址/端口 |
| service | group | 分组 |
| service | cluster | 集群名称 |
| service | weight | 权重 |
| service | metadata | 路由 / 灰度标签 |
| registration | auto_register | 是否自动注册 |
| registration | register_on_startup | 启动注册 |
| registration | register_on_request | 首次请求注册 |
| registration | retry_times / retry_interval | 重试策略 |
| discovery | empty_protection | 空保护（避免闪断） |
| heartbeat | interval / timeout | 心跳配置 |
| shutdown | graceful / timeout / deregister | 下线策略 |
| logging | level / file | 日志 |

---

## 服务发现 (HTTP)

适配器：
- urllib: `from nacos.auto.discovery.ext.urllib import urlopen`
- requests: `from nacos.auto.discovery.ext import requests as nacos_requests`
- httpx: `from nacos.auto.discovery.ext.httpx import AsyncClient`
- aiohttp: `from nacos.auto.discovery.ext.aiohttp import get_session`

简要策略：
- 过滤：healthy & enabled
- 负载：轮询/随机
- 重试：失败换实例
- 缓存：订阅推送更新
- 空保护：开启时避免瞬时清空

---

## 迁移要点
| 旧 | 新 | 说明 |
|----|----|------|
| 同步函数 | 异步 await | 释放阻塞 |
| 散列参数 | Param 数据类 | 明确语义 |
| 轮询监听 | gRPC 推送 | 低延迟 |
| 手写发现 | 适配器 | 减少样板 |
| 手动心跳 | 托管 | 简化 |

---

## 最佳实践
| 场景 | 建议 |
|------|------|
| 多环境 | namespace 隔离 |
| 灰度 | metadata.version 匹配 |
| 安全 | TLS + AK/SK |
| 降级 | 缓存最后可用实例 |
| 回调 | 非阻塞处理 |
| 监控 | 解析耗时 / 失败率 |

---

## 排障
| 现象 | 原因 | 处理 |
|------|------|------|
| 不能自动注册 | 未触发方式 | 检查 CLI / import / middleware |
| 逻辑域名失败 | 未导入适配器 / 无实例 | 导入适配器 & 确认实例 |
| 配置不更新 | 未注册监听 | 调用 add_listener |
| 实例残留 | 未优雅关闭 | 开启 graceful + deregister |
| 解析超时 | 网络 / 防火墙 | 检查端口 9848/9849 |

调试：
```python
ClientConfigBuilder().log_level("DEBUG")
```

---

## 版本策略
0.x：迭代期（可能非兼容）  
锁定：`>=0.1.0,<1.0.0`

---

## 贡献
Fork -> 分支 -> 代码/测试 -> 文档 -> PR（含背景/风险/回滚）。

---

## 许可证
Apache 2.0

---

## 参考
- Nacos: https://nacos.io
- OpenAPI: https://nacos.io/zh-cn/docs/open-API.html
