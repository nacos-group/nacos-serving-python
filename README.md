# nacos-serving-python v0.1.3
<!-- ...existing code... -->

## Overview

`nacos-serving-python` focuses on seamless Service Registration & Discovery plus Config access for Python web apps and HTTP clients.

Core capabilities:
1. Auto register Flask / Django / FastAPI in three ways:
   a) CLI (module run)  
   b) Import-triggered  
   c) WSGI middleware injection  
2. Built‑in service discovery for urllib / requests / httpx / aiohttp so you can call `http://<service-name>/path` directly.

Built atop the async Nacos v2 SDK (gRPC push + structured params).

---

## Installation & Usage
```bash
# 1. install the library
pip install nacos-serving-python

# 2. cd to your project root and run

# 3. run the auto-registration CLI
python -m nacos.auto.registration --nacos-server 127.0.0.1:8848 --service-name demoservice app.py

```

---

## Quick Start (Conceptual)
1. Build a client config (server address, namespace, credentials)  
2. Create Config & Naming services (async)  
3. Optionally: auto register your web service (one of 3 methods)  
4. Use logical hostnames via adapters (urllib / requests / httpx / aiohttp)  
5. Graceful shutdown: deregister ephemeral instance  

(Full code samples removed for brevity—see `demo/` & Chinese README.)

---

## Auto Registration (3 Methods)

| Method | How | Use Case | Intrusive |
|--------|-----|----------|-----------|
| CLI | `python -m nacos.auto.registration app.py ...` | Zero code change | None |
| Import | `import nacos.auto.registration.enabled` | Simple & explicit | Low |
| WSGI Middleware | `from nacos.auto.middleware.wsgi import inject_wsgi_middleware` then `inject_wsgi_middleware(app)` | Custom lifecycle / delayed | Low |

### Example (Import Trigger – Flask)
```python
import nacos.auto.registration.enabled
from flask import Flask
app = Flask(__name__)

@app.route("/health")
def health(): return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
```

### Example (WSGI Middleware – Flask)
```python
from flask import Flask
from nacos.auto.middleware.wsgi import inject_wsgi_middleware
app = Flask(__name__)
inject_wsgi_middleware(app)
app.run()
```

### Configuration File (nacos.yaml)
Placed at project root (`nacos.yaml` or `application.yaml`). See `demo/*/nacos.yaml`.

---

## CLI Startup Parameters

Invoke:
```bash
python -m nacos.auto.registration app.py [options]
```

| Parameter | Example | Meaning |
|-----------|---------|---------|
| --nacos-server | 127.0.0.1:8848 | Nacos server address (host:port[,host:port...]) |
| --namespace | public | Namespace ID |
| --service-name | demo.api | Logical service name |
| --service-port | 8000 | Explicit service port (auto-detect if omitted) |
| --service-ip | 192.168.1.10 | Explicit bind IP (auto-detect if omitted) |
| --service-group | DEFAULT_GROUP | Service group |
| --service-cluster | default | Cluster name (topology segmentation) |
| --service-weight | 1.0 | Load balancing weight |
| --metadata key=val | version=1.0.0 | Repeatable: attach metadata entries |
| --register-on-startup | (flag) | Register immediately at startup |
| --register-on-request | (flag) | Lazy register on first request |
| --no-auto-register | (flag) | Disable auto registration (override defaults) |
| --retry-times | 3 | Registration retry count |
| --retry-interval | 2 | Retry interval seconds |
| --heartbeat-interval | 5 | Heartbeat interval seconds |
| --heartbeat-timeout | 5 | Heartbeat timeout seconds |
| --graceful-shutdown | (flag) | Enable graceful shutdown |
| --shutdown-timeout | 10 | Graceful shutdown max wait seconds |
| --deregister-on-exit | (flag) | Explicitly deregister on exit |
| --log-level | INFO | Logging level |
| --log-file | /path/file.log | Custom log file path |
| --empty-protection | true/false | Keep previous instance list when NACOS returns empty |
| --help |  | Show full help |

Environment variables may override core fields (examples):
| Env | Maps To |
|-----|---------|
| NACOS_SERVER | --nacos-server |
| NACOS_NAMESPACE | --namespace |
| NACOS_SERVICE_NAME | --service-name |
| NACOS_SERVICE_PORT | --service-port |
| NACOS_SERVICE_IP | --service-ip |

If both CLI and env present: CLI takes precedence.

---

## Service Discovery (HTTP Clients)

Adapters allow logical hostname usage:
- urllib: `from nacos.auto.discovery.ext.urllib import urlopen`
- requests: `from nacos.auto.discovery.ext import requests as nacos_requests`
- httpx: `from nacos.auto.discovery.ext.httpx import AsyncClient`
- aiohttp: `from nacos.auto.discovery.ext.aiohttp import get_session`

Fallback steps (manual):
1. List healthy instances
2. Pick one (LB strategy)
3. Compose `http://ip:port/path`

Load Balancing & Resilience:
- Strategy: round-robin or random (implementation)
- Filters: healthy + enabled
- Retry: next instance on failure
- Cache: subscription-driven updates
- Empty protection: optional guard against transient zero instance returns

---

## Configuration Field Summary (nacos.yaml)

| Section | Key | Description |
|---------|-----|-------------|
| nacos | server | Nacos server address list |
| nacos | namespace | Namespace ID |
| service | name | Logical service name |
| service | ip / port | Explicit service endpoint (auto-detected if omitted) |
| service | group | Service group (default DEFAULT_GROUP) |
| service | cluster | Cluster name |
| service | weight | Load balancing weight |
| service | metadata | Arbitrary key-value routing tags |
| registration | auto_register | Enable auto registration driver |
| registration | register_on_startup | Register immediately at startup |
| registration | register_on_request | Lazy register on first request |
| registration | retry_times / retry_interval | Retry strategy |
| discovery | empty_protection | Keep last snapshot if server returns empty |
| heartbeat | interval / timeout | Ephemeral heartbeat config |
| shutdown | graceful / timeout / deregister | Graceful exit behavior |
| logging | level / file | Logging control |

---

## Migration (Legacy SDK → This)
| Legacy | New | Change |
|--------|-----|--------|
| Sync calls | Async await | Non-blocking |
| Flat params | Data classes | Structured |
| Polling | gRPC push | Lower latency |
| Custom discovery | Built-in adapters | Less boilerplate |
| Manual heartbeat | Managed ephemeral | Simplified lifecycle |

---

## Best Practices
| Scenario | Recommendation |
|----------|---------------|
| Env isolation | Use namespaces per env |
| Canary / gray | Route via metadata.version |
| Security | Enable TLS + external credential store |
| Fallback | Cache last good instance |
| Heavy callbacks | Offload to queues / thread pools |
| Observability | Track resolution latency & errors |

---

## Troubleshooting
| Symptom | Cause | Action |
|---------|-------|--------|
| No auto registration | Trigger not used | Use CLI/import/middleware |
| 404 logical hostname | Adapter not imported | Import adapter module |
| Empty instance list | All offline or perms | Check Nacos console & creds |
| Config not updating | Listener missing | Register listener early |
| Residual instance | No graceful shutdown | Enable deregister-on-exit |

Enable debug:
```python
ClientConfigBuilder().log_level("DEBUG")
```

---

## Versioning
0.x = rapid iteration (breaking possible).  
Pin dependency: `nacos-serving-python>=0.1.0,<1.0.0`.

---

## Contributing
Fork → Branch → Code / Tests → Docs → PR (with context & rollback plan).

