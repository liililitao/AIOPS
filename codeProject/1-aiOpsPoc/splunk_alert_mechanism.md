# Splunk 告警机制与脚本输出逻辑说明

## 一、Splunk 告警的执行模型

### 核心概念

在 Splunk 内部，**一个告警 = 一个独立的调度搜索（Scheduled Search）**。当你创建一个告警规则（比如 `test-waf`）时，Splunk 把它注册为一个 saved search，并分配一个唯一的内部 ID。

### 进程隔离机制

**每个告警触发时，Splunk 为它 fork 一个独立的子进程：**

```
Splunk 调度器 (splunkd)
│
├── 时间到达 → 触发告警 A (test-waf) → fork 子进程 → 执行搜索 → 匹配到结果
│     │                                                          │
│     └── 设置环境变量: SPLUNK_ARG_4 = "test-waf"               │
│          SPLUNK_ARG_8 = "/data/splunk/var/run/.../sid_A/results.csv.gz"  │
│                                                                 │
│     └── 子进程 exec: /data/splunk/bin/scripts/alert_to_file.py │
│          (该进程的环境变量 = 告警 A 的专属信息)                   │
│                                                                 │
├── 同时 → 触发告警 B (cpu-warning) → fork 另一个子进程 → 执行搜索
│     │
│     └── 设置环境变量: SPLUNK_ARG_4 = "cpu-warning"
│          SPLUNK_ARG_8 = "/data/splunk/var/run/.../sid_B/results.csv.gz"
│     └── 子进程 exec: /data/splunk/bin/scripts/alert_script.sh
│
├── 同时 → 触发告警 C (disk-full) → fork 第三个子进程
│     ...
```

**关键结论：不同告警之间通过操作系统进程模型天然隔离。每个告警 fork 自己的子进程，子进程继承的环境变量只属于该告警，互不干扰。**

---

## 二、SPLUNK_ARG_8 搜索结果文件路径

`SPLUNK_ARG_8` 指向的路径结构示例：

```
/data/splunk/var/run/splunk/dispatch/
├── scheduler__admin__search__RMD5f1c2d3e4f5a6b7_1234567890/
│   └── results.csv.gz          ← 告警 A (test-waf) 的搜索结果
│
├── scheduler__admin__search__RMD5aabbccddee_0987654321/
│   └── results.csv.gz          ← 告警 B (cpu-warning) 的搜索结果
│
├── scheduler__admin__search__RMD5ffeeddccbbaa_2468013579/
│   └── results.csv.gz          ← 告警 C (disk-full) 的搜索结果
```

每个告警搜索都有自己独立的调度目录（由 saved search 的内部 ID + 调度时间戳决定），**SPLUNK_ARG_8 不会指向其他告警的结果**。

---

## 三、Splunk 传给告警脚本的环境变量

### A 类：通用变量（所有告警动作都会设置）

| 变量名 | 含义 | 示例 |
|--------|------|------|
| `SPLUNK_HOME` | Splunk 安装目录 | `/data/splunk` |
| `SPLUNK_DB` | 数据库目录 | `/data/splunk/var/lib/splunk` |

### B 类：SPLUNK_ARG_0 ~ 8（告警专属）

| 变量 | 含义 | 示例值 |
|------|------|--------|
| `SPLUNK_ARG_0` | 脚本文件名 | `alert_to_file.py` |
| `SPLUNK_ARG_1` | 本次搜索匹配的事件总数 | `25` |
| `SPLUNK_ARG_2` | 告警配置中的搜索条件字符串 | `index=azure category=ApplicationGatewayFirewallLog properties_action=Blocked ...` |
| `SPLUNK_ARG_3` | **完整 SPL 查询**（含所有管道命令） | `index=azure ... \| rex field=resourceId ... \| stats ... \| search count>=20` |
| `SPLUNK_ARG_4` | **告警名称**（Saved Search 名称） | `test-waf` |
| `SPLUNK_ARG_5` | 触发原因（人类可读） | `Saved Search [test-waf]: Number of events(25) >= 20` |
| `SPLUNK_ARG_6` | Splunk Web 结果直达链接 | `http://splunk:8000/app/search/search?sid=scheduler__admin__search__...` |
| `SPLUNK_ARG_7` | 已弃用（始终为空） | (空) |
| `SPLUNK_ARG_8` | **搜索结果文件绝对路径**（gzip 压缩 CSV） | `/data/splunk/var/run/splunk/dispatch/scheduler__admin__search__RMD5xxxx/results.csv.gz` |

---

## 四、告警触发完整执行链路

以下为 `alert_to_file.py` 作为告警脚本动作时的端到端流程：

```
时间线           发生的事件
──────           ──────────

[1] 日志入库
    waf_log_sim.csv 被 Splunk 监控 → 进入 azure 索引
                        │
[2] 调度器轮询
    splunkd 按告警配置的频率检查 test-waf
                        │
[3] 搜索执行
    splunkd 为本次调度创建专属执行目录:
      /data/splunk/var/run/splunk/dispatch/
        scheduler__admin__search__RMD5xxxx/
    运行 SPL，结果写入该目录下的 results.csv.gz
                        │
[4] 触发条件评估
    | search count>=20
    实际 count=25 ≥ 20 → 触发！
                        │
[5] 设置环境变量（仅本进程可见）
    splunkd 父进程设置 SPLUNK_ARG_0 ~ 8
                        │
[6] Fork 子进程
    splunkd fork() → 子进程继承环境变量
    splunkd exec() → python3 /data/splunk/bin/scripts/alert_to_file.py
                        │
[7] 脚本执行 (alert_to_file.py)
    ┌──────────────────────────────────────────┐
    │  read_env():                             │
    │    读取 SPLUNK_ARG_0 ~ 8 所有环境变量     │
    │      ↓                                   │
    │  read_results(SPLUNK_ARG_8):             │
    │    gzip.open() 解压搜索结果 CSV            │
    │    csv.DictReader 解析为 list[dict]       │
    │      ↓                                   │
    │  write_json():                           │
    │    组装告警信息 + 搜索结果                 │
    │    写入 alert_test-waf_<时间戳>.json      │
    │      ↓                                   │
    │  append_index():                         │
    │    追加一行摘要到 alert_index.txt         │
    └──────────────────────────────────────────┘
                        │
[8] 资源回收
    脚本 exit(0) → splunkd 回收子进程
    临时调度目录被清理
```

---

## 五、alert_to_file.py 脚本逻辑

### 5.1 输入

| 来源 | 内容 |
|------|------|
| `SPLUNK_ARG_0` ~ `SPLUNK_ARG_8` | 告警元信息（名称、触发原因、事件数等） |
| `SPLUNK_ARG_8` 路径指向的文件 | Splunk 原生搜索结果（gzip 压缩 CSV），内容是告警 SPL 最终 `| table ...` 或 `| stats ...` 的输出 |

### 5.2 处理流程

1. **read_env()** — 读取所有 `SPLUNK_ARG_*` 环境变量
2. **read_results()** — 解压并解析 `SPLUNK_ARG_8` 的 CSV 文件，得到原生搜索结果
3. **build_content()** — 将环境变量 + 搜索结果组装为结构化告警摘要
4. **write_json()** — 写入 JSON 文件到输出目录
5. **append_index()** — 追加一行汇总信息到索引文件

### 5.3 输出

```
/data/splunk/var/log/splunk/waf_alerts/
├── alert_test-waf_20260709_095900.json   ← 单次告警全文（JSON）
├── alert_test-waf_20260709_100500.json
├── ...
└── alert_index.txt                       ← 汇总索引（追加模式）
```

#### JSON 文件结构

```json
{
  "alert_name": "test-waf",
  "trigger_time": "2026-07-09T09:59:00.000+08:00",
  "trigger_time_utc": "2026-07-09T01:59:00.000Z",
  "event_count": 25,
  "trigger_reason": "Saved Search [test-waf]: Number of events(25) >= 20",
  "splunk_url": "http://splunk:8000/app/search/search?sid=...",
  "search_terms": "index=azure category=...",
  "full_spl": "index=azure ... | rex ... | stats ... | search count>=20",
  "results": [
    {
      "id": "AGW-NCMA-PRD-01",
      "properties_hostname": "purview.novonordiskchina.com.cn",
      "properties_requestUri": ["/api/app/shop/...", "/.env~", "..."],
      "properties_action": ["Blocked"],
      "count": "25"
    }
  ],
  "operator_notes": ""
}
```

#### 索引文件 (alert_index.txt) 格式

```
[2026-07-09 09:59:00] test-waf | 命中25条 | id=AGW-NCMA-PRD-01 hostname=purview.novonordiskchina.com.cn uri=/api/app/shop/hysOrderResultUrlParse | 详见 alert_test-waf_20260709_095900.json
[2026-07-09 10:05:30] test-waf | 命中22条 | id=AGW-NCMA-PRD-01 hostname=purview.novonordiskchina.com.cn uri=/laravel/core/.env | 详见 alert_test-waf_20260709_100530.json
```

---

## 六、关于"多告警同时触发"的问题

> 如果 5 分钟内多个告警同时触发，怎么保证 `SPLUNK_ARG_8` 拿到的就是 `test-waf` 的结果？

**答：由操作系统进程隔离机制天然保证。**

- Splunk 对每一个告警的每一次触发，都执行 `fork() + exec()` 创建一个独立的子进程
- 进程 A 只能看到告警 A 的环境变量，进程 B 只能看到告警 B 的环境变量
- 它们互不干扰，不需要脚本层面做任何额外处理
- 同一个脚本文件 `alert_to_file.py` 可以配在 10 个不同告警的 action 里，每个实例通过 `SPLUNK_ARG_4` 知道自己属于哪个告警

### 关于"Splunk 原生输出"

运维人员所说的"原生输出"，指的是 Splunk 搜索引擎直接产出的两样东西：

1. **告警元信息** — 即环境变量 `SPLUNK_ARG_*` 中的内容（告警名称、触发原因、SPL 等）
2. **搜索结果 CSV** — 即 `SPLUNK_ARG_8` 指向的 `results.csv.gz` 文件内容，是 SPL 最终 `| table ...` 管道的原样输出

脚本的作用是将这两样"原生输出"持久化到本地文件，替代邮件发送功能，**不应对搜索结果做额外的加工或过滤**。

---

## 七、相关文件

| 文件 | 用途 | 位置 |
|------|------|------|
| `waf_log_once.py` | Azure WAF 模拟日志生成器 | 项目目录 |
| `testlog/waf_log_sim.csv` | 模拟日志输出 | 项目目录 |
| `alert_to_file.py` | Splunk 告警本地持久化脚本 | 部署到 `/data/splunk/bin/scripts/` |
| `splunk_alert_mechanism.md` | 本文档 | 项目目录 |

---

## 八、环境信息

| 项目 | 值 |
|------|-----|
| Splunk 安装目录 | `/data/splunk` |
| 告警脚本目录 | `/data/splunk/bin/scripts/` |
| 告警输出目录 | `/data/splunk/var/log/splunk/waf_alerts/` |
| 告警名称 | `test-waf` |
| 目标索引 | `azure` |
| Splunk 平台 | Linux 测试机 |
