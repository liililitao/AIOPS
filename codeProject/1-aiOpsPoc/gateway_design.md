# Flask 认证网关 — 技术流程文档

## 1. 目标

开发一个 Flask 认证网关，复用测试机 Splunk 的用户密码数据库进行身份验证，
将同事开发的 AIOps 交互式 SPA（`frontend/` 下的三个静态文件）包裹在内，
通过认证后才可访问。

**核心原则：同事的前端代码改动量最小化，仅限 1 行 JS + 1 行 HTML 配置注入。**

---

## 2. 整体架构

```
┌──────────────────────────────────────────────────────┐
│                    浏览器                              │
│        http://测试机:5000                              │
└──────────┬───────────────────────────────┬───────────┘
           │                               │
           ▼                               ▼
    /app/*  静态页面请求           /api/v1/*  后端 API 请求
           │                               │
           ▼                               ▼
┌──────────────────────────────────────────────────────┐
│                   Flask 网关 (:5000)                   │
│                                                      │
│  ┌─────────────────┐    ┌─────────────────────────┐  │
│  │ auth.py          │    │ proxy.py                │  │
│  │ ─────────        │    │ ─────────               │  │
│  │ before_request:  │    │ /api/v1/* →             │  │
│  │  读取 cookie/JWT │    │ requests 转发到          │  │
│  │  调 Splunk 验证   │    │ 同事后端 :8001          │  │
│  │  ├─ 有效 → 放行   │    └─────────────────────────┘  │
│  │  └─ 无效 → 302    │                                │
│  └─────────────────┘                                  │
│                                                      │
│  ┌──────────────────────────────────────────────────┐ │
│  │ static 托管                                       │ │
│  │ /app/ → frontend/index.html                       │ │
│  │ /app/app.js, /app/styles.css                      │ │
│  └──────────────────────────────────────────────────┘ │
└───────────────────────┬──────────────────────────────┘
                        │ /api/v1/*
                        ▼
              ┌──────────────────┐
              │  同事的后端服务    │
              │  :8001            │
              │  (FastAPI/其他)   │
              └──────────────────┘
```

---

## 3. 认证流程

### 3.1 进入方式：Splunk Dashboard 按钮

```
Splunk Dashboard
  └── HTML 按钮 (Simple XML <html> 面板)
      href="http://测试机:5000/app/?splunk_token=$env:token$"
      target="_blank"
```

`$env:token$` 是 Splunk Simple XML 的内置变量，代表当前登录用户的 session token。

### 3.2 认证时序

```
浏览器                        Flask网关                      Splunk
  │                              │                             │
  │ GET /app/?splunk_token=xxx   │                             │
  │─────────────────────────────>│                             │
  │                              │                             │
  │                              │ POST /services/auth/        │
  │                              │   /current-context           │
  │                              │   Header: Authorization      │
  │                              │   Bearer xxx                  │
  │                              │─────────────────────────────>│
  │                              │                             │
  │                              │   200 {user, roles...}       │
  │                              │<─────────────────────────────│
  │                              │                             │
  │                              │ token 有效                   │
  │                              │ 签发 JWT 到 cookie           │
  │                              │ 302 跳转到 /app/ (URL 去token)│
  │                              │                             │
  │  GET /app/ (带 JWT cookie)   │                             │
  │<─────────────────────────────│                             │
  │                              │                             │
  │  后续请求:                    │                             │
  │  Cookie 自动带 JWT            │                             │
  │─────────────────────────────>│                             │
  │     JWT 校验通过 → 放行       │                             │
  │                              │                             │
```

### 3.3 Token 校验策略

| 环节 | 机制 |
|------|------|
| **首次验证** | 取 URL 中的 `splunk_token`，调 Splunk REST API `/services/authentication/current-context`，返回 200 表示有效 |
| **会话保持** | Flask 签发 JWT（含用户名、过期时间），通过 `Set-Cookie` 种到浏览器 |
| **后续请求** | `@login_required` 装饰器校验 cookie 中的 JWT，不再调 Splunk API |
| **JWT 过期** | JWT 过期后需重新从 Splunk Dashboard 按钮进入（重新获得新 token） |

---

## 4. 路由设计

| 路由 | 方法 | 认证? | 说明 |
|------|------|:---:|------|
| `/app/` | GET | JWT | 返回 `index.html`，注入 `APP_CONFIG` 脚本 |
| `/app/<path>` | GET | JWT | 返回 `frontend/` 下的静态文件（JS/CSS/图片等） |
| `/api/v1/*` | ALL | JWT | 反向代理到 `http://127.0.0.1:8001` |
| `/health` | GET | 否 | 网关自身健康检查 |

### 4.1 静态文件映射

| URL 路径 | 磁盘路径 |
|---------|---------|
| `/app/` | `frontend/index.html` |
| `/app/app.js` | `frontend/app.js` |
| `/app/styles.css` | `frontend/styles.css` |
| `/app/<任意文件>` | `frontend/<任意文件>` |

---

## 5. 同事前端需要的改动（仅 2 处）

### 改动 1：`app.js` 第 5 行

```javascript
// 改前:
const API = "/api/v1";

// 改后:
const API = (window.APP_CONFIG && window.APP_CONFIG.API_BASE) || "/api/v1";
```

**影响**：同事本地开发时 `APP_CONFIG` 不存在，回退到 `/api/v1`，行为不变。

### 改动 2：`index.html` `<head>` 内加一行

```html
<!-- 由 Flask 网关在运行时注入，同事本地开发时可删除或留空 -->
<script>
  window.APP_CONFIG = {
    API_BASE: "/api/v1"
  };
</script>
```

**说明**：Flask 渲染 `index.html` 时会替换这行的值为实际的 API 代理地址（如 `http://测试机:5000/api/v1`），同事实例本地开发时直接用 `/api/v1` 访问自己的后端即可。

> 如果不想改 `index.html`，Flask 端也可以直接在 HTML 响应 `</head>` 前注入这段脚本，做到同事零改动。

---

## 6. 文件结构

```
项目目录/
  gateway.py              ← Flask 网关主入口
  frontend/               ← 同事的三个文件（原封不动拷入）
    index.html
    app.js                ← 改 1 行 (API base URL 可配置化)
    styles.css
```

---

## 7. 部署步骤

### 7.1 测试机准备

```bash
# 1. 安装依赖 (JWT 需要 PyJWT)
pip install flask requests pyjwt

# 2. 创建部署目录
sudo mkdir -p /opt/aiops-gateway/frontend
sudo chown -R $(whoami) /opt/aiops-gateway

# 3. 拷贝文件
# gateway.py → /opt/aiops-gateway/
# frontend/* → /opt/aiops-gateway/frontend/
```

### 7.2 启动

```bash
# 开发调试
export SPLUNK_HOST="127.0.0.1"
export SPLUNK_PORT="8089"
export BACKEND_HOST="127.0.0.1"
export BACKEND_PORT="8001"
export JWT_SECRET="生成一个随机字符串"

cd /opt/aiops-gateway
python gateway.py

# 生产运行 (gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 gateway:app
```

### 7.3 Splunk Dashboard 按钮配置

在 `waf_dashboard.xml` 中新增一行：

```xml
<row>
  <panel>
    <html>
      <a href="http://测试机:5000/app/?splunk_token=$env:token$"
         target="_blank"
         style="display:inline-block;padding:8px 20px;
                background-color:#1e93c6;color:white;
                text-decoration:none;border-radius:4px;">
        进入 AIOps 诊断平台
      </a>
    </html>
  </panel>
</row>
```

---

## 8. 安全边界

| 层面 | 措施 |
|------|------|
| 传输 | token 仅在首次 URL 参数中传递，之后通过 HttpOnly cookie 的 JWT 通信 |
| 存储 | Splunk session key 不存储到文件/数据库 |
| 过期 | JWT 有效期默认 8 小时，与 Splunk 默认 session 超时对齐 |
| 代理 | API 代理仅转发到本地 `127.0.0.1:8001`，不开放外部目标 |
| 生产 | `SPLUNK_VERIFY_SSL=true`（测试机自签证书设 `false`） |

---

## 9. 错误处理

| 场景 | 网关行为 |
|------|---------|
| 无 token，无 cookie | 302 重定向到 Splunk 登录页 |
| token 无效/过期 | 返回 401 + "请从 Splunk Dashboard 重新进入" |
| JWT 过期 | 清除 cookie，302 重定向到 Splunk 登录页 |
| 后端 API 不可达 | 返回 502 + "后端服务不可用" |
| 后端 API 超时 (30s) | 返回 504 + "后端服务响应超时" |
