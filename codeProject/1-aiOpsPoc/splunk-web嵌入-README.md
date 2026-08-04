# WAF 告警模拟 → Splunk Dashboard → Flask 认证网关 完整链路文档

## 概述

本项目在 Azure 云测试机上搭建了一套完整的 WAF 安全告警流水线：

```
模拟日志生成 → Splunk 索引 → 告警规则触发 → 告警脚本执行 → 数据持久化
                                              │
                         ┌────────────────────┘
                         ▼
              Flask 认证网关 (5000)
              复用 Splunk 用户体系
                         │
                         ▼
                Splunk Dashboard 按钮 → 跳转受保护的同事业务页面
```

**核心验证目标：** Splunk 已登录用户通过 Dashboard 按钮跳转到外部业务页面，无需二次登录。

---

## 环境信息

| 项目 | 值 |
|------|-----|
| Splunk 版本 | 10.0.2 (build e2d18b4767e9) |
| Splunk 安装目录 | `/data/splunk` |
| Splunk Web 端口 | 8000 |
| Splunk 管理端口 | 8089 |
| Flask 网关端口 | 5000 |
| 公网域名 | `spl9-tst-hfwr01.chinanorth3.cloudapp.chinacloudapi.cn` |
| 内网 IP | `10.31.75.37` |
| Azure 开放端口 | 8000, 5000 |
| 索引 | `azure`（原始日志）、`waflogalert`（告警 JSON 数据） |

---

## 项目文件清单

```
项目目录/
├── waf_log_gen.py              # 模拟 WAF 日志生成器（硬编码数据池，方案B）
├── waf_log_once.py             # 早期版本，单次生成 25 条
├── waf_log_replay.py           # 版本二：从生产 CSV 回放（依赖外部文件）
├── alert_to_file.py            # Splunk 告警动作：输出无风险等级 JSON
├── alert_to_file_risk.py       # Splunk 告警动作：输出含 risk_level 的 JSON
├── wrapper_alert.sh            # Wrapper 脚本，同时调用两个 alert 脚本
├── test_login.py               # 早期 Flask 登录验证原型
├── gateway/                    # Flask 认证网关
│   ├── gateway.py              #   主程序
│   ├── requirements.txt        #   依赖
│   ├── nginx_aiops.conf        #   Nginx 配置（备用）
│   ├── frontend/               #   前端页面（helloworld / 同事真页面）
│   │   ├── index.html
│   │   ├── app.js              #   （helloworld 版已删除）
│   │   ├── styles.css          #   （helloworld 版已删除）
│   │   └── index_helloworld.html
│   └── frontend_backup/       #   同事原始页面备份
├── waf_dashboard.xml           # Splunk Dashboard
├── testlog/                    # 测试日志数据
│   ├── waf_blocked.csv        #   生产环境真实数据（300条）
│   ├── waf_log_sim.csv        #   早期模拟日志
│   └── waf_log_replay.csv     #   回放版输出
├── alert_log/                  # 告警 JSON 输出（含 risk_level）
├── splunk_alert_mechanism.md   # Splunk 告警环境变量说明
├── gateway_design.md           # Flask 网关技术设计文档
└── README.md                   # 本文件
```

---

## 一、模拟日志生成层

### 最终版：`waf_log_gen.py`（方案 B）

**设计思路：** 从生产数据提取真实字段值，硬编码在 Python 字典池中，运行时随机抽取生成日志。

**方案 B 核心：**
- `HOSTNAME_POOLS`：按 hostname 分组，`resourceId`/`clientIp`/`requestUri` 与 hostname 强制绑定
- `SHARED`：全局共享字段（ruleId, message, engine 等）
- 生成时随机选 hostname → 从专属池取绑定字段 → 从 SHARED 取公共字段 → 刷新时间戳和 transactionId

**配置项：**
```python
OUTPUT_COUNT = 60    # 每次运行的日志条数
TARGET_HOSTNAMES = {"purview.novonordiskchina.com.cn", "api-obesity.novocare.com.cn"}
```

**输出字段（23 个）：** 与 Azure WAF 原始日志完全对齐，包括 `properties.details.*` 等子字段。

**运行：**
```bash
python3 waf_log_gen.py
# 输出: test_log/waf_log_gen.csv
```

### 生产数据（参考）

`testlog/waf_blocked.csv`：300 条真实 WAF Blocked 日志，15 个 hostname，9 个 Application Gateway。
其中 `purview.novonordiskchina.com.cn` (63 条) 和 `api-obesity.novocare.com.cn` (45 条) 会触发告警（count >= 20）。

### Splunk 接入

通过 Web UI：Settings → Data inputs → Files & directories → 监控 CSV 目录，指定 `index=azure`, `sourcetype=csv`。

**注意：** CSV 文件的字段名中 `.` 会被 Splunk 转为 `_`（`properties.action` → `properties_action`）。告警 SPL 需要相应调整。

---

## 二、告警规则层

### 告警 SPL

```spl
index=azure category=ApplicationGatewayFirewallLog properties_action=Blocked
properties_hostname!="novocareapp.novocare.com.cn" AND
properties_hostname!="test-novocareapp.novocare.com.cn"
| rex field=resourceId "\/(?<id>[^\/]+)$"
| stats values(properties_action) as properties_action
        values(properties_requestUri) as properties_requestUri
        count by properties_hostname,id
| table id,properties_hostname,properties_requestUri,properties_action,count
| search count>=20
```

### 告警逻辑说明

1. 筛选 Blocked 事件，排除两个已知正常域名
2. `rex` 从 resourceId 提取 Application Gateway ID
3. `stats count by (hostname, gateway_id)` 分组统计
4. 任何一组 count >= 20 即触发

### 告警动作

| 脚本 | 输出目录 | 输出内容 |
|------|---------|---------|
| `alert_to_file.py` | `/data/splunk/var/log/splunk/waf_alerts/` | JSON（无 risk_level） |
| `alert_to_file_risk.py` | `/data/splunk/var/log/splunk/waflogalert/` | JSON（有 risk_level: 高/中/低） |

**因为 Splunk 每种动作类型只能有一个实例**，所以用 `wrapper_alert.sh` 作为入口：

```bash
#!/bin/bash
python3 /data/splunk/bin/scripts/alert_to_file.py
python3 /data/splunk/bin/scripts/alert_to_file_risk.py
```

告警配置中只填 `wrapper_alert.sh`。

### 告警环境变量（核心原理）

Splunk 通过 OS 进程隔离机制保证不同告警不串数据。每次告警触发时 fork 子进程，设置专属环境变量：

| 变量 | 含义 |
|------|------|
| `SPLUNK_ARG_0` | 脚本名 |
| `SPLUNK_ARG_1` | 匹配事件数 |
| `SPLUNK_ARG_2` | 搜索条件 |
| `SPLUNK_ARG_3` | 完整 SPL |
| `SPLUNK_ARG_4` | 告警名称 |
| `SPLUNK_ARG_5` | 触发原因 |
| `SPLUNK_ARG_6` | 结果链接 |
| `SPLUNK_ARG_8` | **搜索结果 gzip CSV 文件路径**（最重要的变量） |

详见 `splunk_alert_mechanism.md`。

---

## 三、Flask 认证网关层

### 设计原理

```
Splunk Dashboard 按钮
  │  带 ?splunk_user=$env:user$
  ▼
Flask :5000 before_request
  │
  ├─ 有 ?splunk_user 参数 → 信任（Splunk 已认证用户的页面渲染此 URL）
  │     → 签发 JWT → 302 重定向去参数 → Set-Cookie
  │
  ├─ 有 auth_token cookie → 验证 JWT → 放行
  │
  └─ 都没有 → 302 踢回 Splunk 登录页
```

### JWT 机制

- **签发：** `jwt.encode({username, roles, exp, jti}, JWT_SECRET, "HS256")`
- **验证：** `jwt.decode(token, JWT_SECRET, ["HS256"])`
- **有效期：** 默认 8 小时，与 Splunk session 对齐
- **密钥：** 环境变量 `JWT_SECRET`，默认值 `"change-me-in-production"`

### 路由设计

| 路由 | 功能 |
|------|------|
| `/app/` | 返回前端 index.html，注入 `APP_CONFIG` |
| `/app/<path>` | 返回静态文件 |
| `/api/v1/<path>` | 反向代理到同事后端服务（默认 `127.0.0.1:8001`） |
| `/health` | 健康检查 |

### 启动方式

```bash
cd /opt/aiops-gateway
export SPLUNK_WEB_URL="http://域名:8000"   # 必须改成公网地址，否则 302 跳转会指向 127.0.0.1
nohup python3 gateway.py > gateway.log 2>&1 &
```

### 同事前端改动

仅需 1 行：

```javascript
// app.js 第 5 行：API base URL 改为从配置读取
const API = (window.APP_CONFIG && window.APP_CONFIG.API_BASE) || "/api/v1";
```

Flask 在返回 `index.html` 时自动注入：
```html
<script>window.APP_CONFIG={API_BASE:"/api/v1"};</script>
```

### helloworld 验证页面

替换过程：
```bash
# 备份真页面
cp -r /opt/aiops-gateway/frontend /opt/aiops-gateway/frontend_backup

# 替换为 helloworld
echo '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Test</title>
</head><body style="display:flex;justify-content:center;align-items:center;
height:100vh;font-family:Arial;"><h1>helloworld</h1></body></html>' \
> /opt/aiops-gateway/frontend/index.html

# 恢复
cp /opt/aiops-gateway/frontend_backup/* /opt/aiops-gateway/frontend/
```

---

## 四、Splunk Dashboard 层

### WAF 告警监控面板

部署到 `/data/splunk/etc/apps/search/local/data/ui/views/waf_dashboard.xml`。

**面板组成（11 个面板，6 行）：**

| 区域 | 面板 | 数据源 |
|------|------|--------|
| 告警摘要 | 总告警数/高/中/低风险计数 | `index=waflogalert` |
| | 告警触发趋势（面积图） | `index=waflogalert` |
| | 风险分布（饼图）+ 最近告警（表格） | `index=waflogalert` |
| 原始日志 | Blocked 趋势 | `index=azure` |
| | 被攻击 Hostname/IP Top N | `index=azure` |
| | 被攻击 URI Top 20 | `index=azure` |

### JSON 数据接入 Dashboard

1. Web UI 创建 `waflogalert` 索引
2. Settings → Data inputs → Files & directories → 监控 `/data/splunk/var/log/splunk/waflogalert/`
3. sourcetype 选 `_json`
4. Splunk 自动解析 JSON 顶层 key 为字段（`risk_level`, `alert_name`, `event_count` 等）

### 按钮配置

```xml
<a href="http://域名:5000/app/?splunk_user=$env:user$"
   target="_blank" ...>
  进入 AIOps 诊断平台
</a>
```

`$env:user$` 是 Splunk Simple XML 内置变量，代表当前登录用户名。**不需要额外声明 token。**

---

## 五、关键踩坑记录

### 1. Splunk 10.x 不开放自定义 HTTP 端点
- 尝试了 `[expose:]` + `controllers/` → ❌
- 尝试了 `[endpoint:]` + `controllers/` → ❌
- 尝试了 `restmap.conf` + Python handler → ❌
- **结论：** Splunk 10.x 不支持通过 App 方式挂载 CherryPy 反向代理

### 2. Azure NSG 端口限制
- Azure 默认只开 8000 端口
- 5000 端口需要联系云管理员在 NSG 添加入站规则
- 测试机出口 IP 查看：`curl -s ifconfig.me`

### 3. SSH 跳板机限制
- 测试机通过 `143.64.163.205:51822` 跳板机连接
- 跳板机禁用了 TCP 端口转发，SSH 隧道不可用

### 4. CSV sourcetype 字段名问题
- Splunk 通过 `sourcetype=csv` 索引时，`.` 自动转 `_`
- 告警 SPL 需要写 `properties_action` 而不是 `properties.action`

### 5. Splunk REST API 登录失败
- 测试机管理端口是 8089
- 密码中有 `@` 等特殊字符时，shell curl 容易出问题
- 解决方法：写 Python 脚本代替 curl

### 6. JWT SECRET 和 SPUNK_WEB_URL 配置
- `JWT_SECRET` 测试阶段可用默认值
- `SPLUNK_WEB_URL` **必须设为公网地址**，否则未认证用户的 302 跳转会指向 `127.0.0.1:8000`

### 7. Splunk 告警动作限制
- 每种动作类型只能添加一个实例
- 需要同时执行多个脚本时，用 wrapper shell 脚本包装

---

## 六、部署到新机器的快速清单

```bash
# 1. 安装 Python 依赖
pip install flask requests pyjwt

# 2. 部署 Flask 网关
sudo mkdir -p /opt/aiops-gateway/frontend
# 拷入 gateway.py, frontend/*
sudo chown -R $(whoami) /opt/aiops-gateway

# 3. 配置环境变量 + 启动网关
export SPLUNK_WEB_URL="http://域名:8000"
export JWT_SECRET="生成一个随机字符串"
cd /opt/aiops-gateway
nohup python3 gateway.py > gateway.log 2>&1 &

# 4. 部署 Splunk 告警脚本
sudo cp alert_to_file.py /data/splunk/bin/scripts/
sudo cp alert_to_file_risk.py /data/splunk/bin/scripts/
sudo cp wrapper_alert.sh /data/splunk/bin/scripts/
sudo chown splunk:splunk /data/splunk/bin/scripts/alert_to_file*.py
sudo chown splunk:splunk /data/splunk/bin/scripts/wrapper_alert.sh
sudo chmod 755 /data/splunk/bin/scripts/alert_to_file*.py
sudo chmod 755 /data/splunk/bin/scripts/wrapper_alert.sh

# 5. 创建输出目录
sudo mkdir -p /data/splunk/var/log/splunk/waf_alerts
sudo mkdir -p /data/splunk/var/log/splunk/waflogalert
sudo chown splunk:splunk /data/splunk/var/log/splunk/waf_alerts
sudo chown splunk:splunk /data/splunk/var/log/splunk/waflogalert

# 6. Splunk Web UI 操作
#   - 创建索引 waflogalert
#   - Data inputs → monitor waf_alerts/ 和 waflogalert/ 目录
#   - 导入告警 SPL → 配置 action 脚本为 wrapper_alert.sh
#   - 导入 Dashboard XML

# 7. 启动模拟日志生成
python3 waf_log_gen.py

# 8. 完成
```

---

## 七、验证检查点

| # | 操作 | 预期结果 |
|:---:|------|------|
| 1 | `curl 域名:5000/health` | `{"status":"ok"}` |
| 2 | 浏览器访问 `域名:5000/app/`（无 cookie） | 302 → Splunk 登录页 |
| 3 | 浏览器访问 `域名:5000/app/?splunk_user=test` | 302 → **helloworld** |
| 4 | Splunk Dashboard 点按钮 | 新标签页 → **helloworld** |
| 5 | 搜索 `index=azure` | 能看到 WAF 日志 |
| 6 | 搜索 `index=waflogalert` | 能看到告警 JSON（含 risk_level） |
| 7 | 告警规则手动测试 | 返回 count>=20 的结果 |
