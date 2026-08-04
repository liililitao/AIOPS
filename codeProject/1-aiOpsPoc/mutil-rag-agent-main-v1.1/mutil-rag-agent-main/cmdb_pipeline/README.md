# CMDB Pipeline — PostgreSQL → Flink CDC → Kafka → Consumer 全链路学习套件

> 面向零基础的 CMDB / PostgreSQL / Flink CDC / Kafka 学习项目。
> 所有组件使用 Docker 真实部署，代码逐行注释，配合 7 个脚本逐步理解整条链路。

---

## 先理解大图

```
生产环境架构:
==============
┌──────────┐     WAL日志      ┌──────────┐    变更事件     ┌──────────┐
│PostgreSQL│ ──────────────► │ Flink CDC│ ─────────────► │  Kafka   │
│ (CMDB)   │   (二进制格式)    │(连接器)  │   (JSON格式)    │(消息队列) │
└──────────┘                 └──────────┘                └────┬─────┘
                                                              │
                          ┌───────────────────────────────────┘
                          │ 消费变更事件
                          ▼
                    ┌──────────┐         ┌──────────────┐
                    │  Flink   │ ──────► │  OpenSearch  │ ← Agent 的 query_cmdb() 查这里
                    │(流处理)  │  写入    │  (全文搜索)   │    毫秒级, 不打 PostgreSQL
                    └──────────┘         └──────────────┘

学习环境 (本套件):
==============
┌──────────┐   触发器自动记录   ┌───────────────┐  轮询读取   ┌───────────────┐
│PostgreSQL│ ──────────────► │cmdb_change_log │ ─────────► │03_cdc_listener│
│ (真实)   │   变更到日志表    │   (模拟 WAL)    │            │   .py         │
└──────────┘                 └───────────────┘            └───────┬───────┘
                                                                   │ JSON事件
                                                                   ▼
                                                            ┌───────────────┐
                                                            │04_kafka_prod  │
                                                            │   ucer.py     │
                                                            └───────┬───────┘
                                                                    │ send()
                                                                    ▼
                        ┌───────────────────────────────────────────────────┐
                        │                    Kafka (真实)                     │
                        │              Topic: cmdb.devices.change            │
                        └───────────────────────┬───────────────────────────┘
                                                │ poll()
                                                ▼
                                        ┌───────────────┐
                                        │05_kafka_cons  │
                                        │   umer.py     │
                                        └───────┬───────┘
                                                │ 写入
                                                ▼
                                        ┌───────────────┐     ┌──────────────┐
                                        │ 本地Python缓存 │ ←── │06_query_cmdb │
                                        │  (模拟OpenSearch)│    │_from_cache.py│
                                        └───────────────┘     └──────────────┘
```

---

## 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install psycopg2-binary kafka-python

# 启动 Docker 服务 (PostgreSQL + Kafka)
docker compose -f cmdb_pipeline/docker-compose.cmdb.yml up -d

# 等待服务就绪 (约 30 秒)
docker ps --filter "name=cmdb-"
```

### 2. 按顺序运行脚本

```bash
# 终端 1: 验证数据库初始化
python cmdb_pipeline/01_init_postgres.py

# 终端 1: 执行增删改操作 + 观察变更日志
python cmdb_pipeline/02_crud_operations.py

# 终端 1: 启动 CDC 监听 (保持运行)
python cmdb_pipeline/03_cdc_listener.py

# 终端 2: 启动 Kafka Producer (保持运行)  
python cmdb_pipeline/04_kafka_producer.py

# 终端 3: 启动 Kafka Consumer (保持运行)
python cmdb_pipeline/05_kafka_consumer.py

# 终端 4: 执行 CRUD → 观察三个终端实时联动
python cmdb_pipeline/02_crud_operations.py
```

### 3. 一键端到端测试

```bash
python cmdb_pipeline/07_full_pipeline_test.py
```

---

## 脚本说明

| 脚本 | 作用 | 生产环境对应 |
|------|------|-------------|
| `01_init_postgres.py` | 验证 PostgreSQL 连接 + 展示初始数据 | (相同) |
| `02_crud_operations.py` | 模拟运维人员增删改 CMDB 数据 | (相同) |
| `03_cdc_listener.py` | 轮询 cmdb_change_log, 转成 JSON 事件 | **Flink CDC** 读 PostgreSQL WAL |
| `04_kafka_producer.py` | 把变更事件发到 Kafka | **Flink CDC** 写 Kafka |
| `05_kafka_consumer.py` | 从 Kafka 消费 → 更新本地缓存 | **Flink 作业** 消费 Kafka → 写 OpenSearch |
| `06_query_cmdb_from_cache.py` | Agent 的 query_cmdb() 查询函数 | Agent 查 OpenSearch |
| `07_full_pipeline_test.py` | 一键验证 6 个步骤全链路 | CI/CD 集成测试 |

---

## 每个组件解释

### PostgreSQL — CMDB 主数据库

**是什么：** 关系型数据库，用 SQL 增删改查数据。

**在这个项目中：**
- 存放所有 IT 设备信息 (IP、主机名、应用名、负责人、业务等级...)
- 表 `cmdb_devices` 是核心数据表
- 表 `cmdb_change_log` 由触发器自动维护，记录每次变更

**Flink CDC 怎么感知变更：**
- PostgreSQL 每次写操作都会产生 WAL (Write-Ahead Log) 日志
- Flink CDC 连接器直接读 WAL，不需要触发器
- 我们的学习脚本 03_cdc_listener.py 用触发器 + 轮询来模拟这个过程

### Kafka — 消息中间件

**是什么：** 高吞吐的分布式消息队列。生产者往 Topic 里写消息，消费者从 Topic 里读消息。

**为什么需要它：**
- **解耦：** PostgreSQL 不需要知道谁在消费变更
- **削峰：** 1000 条变更加入来，消费者可以慢慢处理，不被冲垮
- **持久化：** Kafka 把消息存磁盘，消费者挂了重连后可以继续从上次的位置读

**在这个项目中：**
- Topic 名: `cmdb.devices.change`
- Producer: 04_kafka_producer.py (发送变更事件)
- Consumer: 05_kafka_consumer.py (消费变更事件)

### Flink CDC（学习环境中用脚本模拟）

**是什么：** 一个连接器，能把数据库的变更实时"翻译"成 Kafka 消息。

**为什么不用触发器而读 WAL：**
- 触发器会拖慢数据库 (每次写操作多一次 INSERT)
- WAL 是 PostgreSQL 本来就写的东西，Flink CDC 只是"偷看"它
- 对数据库性能零影响

### Flink（流处理引擎）

**是什么：** 实时处理数据流的引擎。从 Kafka 消费 → 加工/清洗/聚合 → 写入下游。

**在这个项目中的作用：**
- 从 Kafka 消费 CMDB 变更事件
- 把变更应用到 OpenSearch 索引 (增/改/删)
- 保证 OpenSearch 里的 CMDB 数据和 PostgreSQL 一致

**Agent 为什么不需要感知：**
- Agent 只从 OpenSearch 查数据
- OpenSearch 里已经有最新数据了 (Flink 同步的)
- PostgreSQL → Flink CDC → Kafka → Flink → OpenSearch 这条链对 Agent 完全透明

---

## CMDB 数据模型

```sql
cmdb_devices 表:
┌────┬──────────────┬──────────────┬──────────────┬───────┬──────┬──────────┐
│ id │ ip           │ hostname     │ app_name     │ owner │ env  │business_ │
│    │              │              │              │       │      │level     │
├────┼──────────────┼──────────────┼──────────────┼───────┼──────┼──────────┤
│ 1  │ 10.0.1.101   │ pay-gw-01    │ 支付网关服务  │ 张三  │ PROD │ 核心     │
│ 2  │ 10.0.1.102   │ pay-gw-02    │ 支付网关服务  │ 张三  │ PROD │ 核心     │
│ 3  │ 10.0.1.103   │ user-svc-01  │ 用户中心      │ 李四  │ PROD │ 重要     │
│ ...│ ...          │ ...          │ ...          │ ...   │ ...  │ ...      │
└────┴──────────────┴──────────────┴──────────────┴───────┴──────┴──────────┘
```

与 `alert_simulator.py` 的 HOST_POOL 完全对齐，确保模拟告警的 IP 能命中 CMDB。

---

## Kafka 消息格式

```json
{
  "payload": {
    "before": {"id": 5, "ip": "192.168.1.51", "business_level": "一般", ...},
    "after":  {"id": 5, "ip": "192.168.1.51", "business_level": "核心", ...},
    "op": "u",
    "device_id": "5",
    "ts_ms": 1717425600000,
    "source": {
      "db": "cmdb",
      "table": "cmdb_devices",
      "connector": "flink-cdc-postgres"
    }
  }
}
```
- `op`: c=create(插入), u=update(更新), d=delete(删除)
- `before`: 变更前的数据 (DELETE/UPDATE 时有用)
- `after`: 变更后的数据 (INSERT/UPDATE 时有用)

---

## 清理

```bash
# 停止所有服务
docker compose -f cmdb_pipeline/docker-compose.cmdb.yml down -v
```

---

> 学习目标: 理解 PostgreSQL → Flink CDC → Kafka → Flink → OpenSearch 这条链路中
> 每个组件干什么、为什么需要它、Agent 代码为什么不需要感知它。
>
> 关键认知: Flink+Kafka 是 **基础设施层**，Agent 只从 OpenSearch 查数据。
> 对 Agent 代码来说，从 Mock dict 变成 OpenSearch 查询，改动 ~30 行。
