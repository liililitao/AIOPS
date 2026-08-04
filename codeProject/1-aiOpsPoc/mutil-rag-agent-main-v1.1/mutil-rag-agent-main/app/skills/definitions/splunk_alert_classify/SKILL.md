---
name: splunk_alert_classify
display_name: Splunk 告警分类诊断
description: 通用 SRE 告警诊断: 接收监控系统告警 → 查CMDB确定业务归属 → 查知识库匹配SOP → 综合评估风险等级(1-5)和优先级 → 输出诊断报告
triggers:
  - 告警
  - alert
  - cpu_high
  - memory_high
  - disk_full
  - service_500
  - network_timeout
  - container_down
  - CPU 高
  - 内存高
  - 磁盘满
  - 5xx 错误
  - 超时
  - 容器异常
allowed_tools:
  - search_knowledge_base
  - query_cmdb
  - get_current_time
  - get_local_system_overview
  - get_local_cpu_memory
  - get_local_disk_usage
  - list_top_processes
  - web_search
risk_level: low
---

# Splunk 告警分类诊断 Playbook

## 适用场景
- 从 Splunk / Prometheus / Alertmanager 等监控系统收到的各类告警
- 告警类型包括: CPU高、内存高、磁盘满、服务5xx、网络超时、容器异常等
- 需要快速判断影响范围、风险等级、优先级的场景

## Phase 1: 解析告警信息
从告警中提取关键字段:
- **告警类型** (alert_type): cpu_high / memory_high / disk_full / service_500 / network_timeout / container_down
- **设备 IP** (host_ip): 出问题的机器
- **严重程度** (severity): critical / high / medium / low
- **告警描述** (description): 具体现象

## Phase 2: 查 CMDB 确定业务归属 (必须)
1. 调用 `query_cmdb(ip=<host_ip>)` 获取设备信息
2. 从返回结果中提取: 应用名、负责人、环境、**业务等级**
3. 业务等级会直接影响最终的风险评估

## Phase 3: 查知识库匹配 SOP
1. 根据告警类型, 调用 `search_knowledge_base(query="<告警类型> 处理 SOP")`
2. 获取标准处理流程、常见根因、处置建议

## Phase 4: 风险评估
综合考虑以下因素, 输出 **1-5 级风险等级**:

| 因素 | 权重 | 说明 |
|------|------|------|
| 告警严重程度 | 高 | critical=5, high=4, medium=3, low=2 |
| 业务等级 | 高 | 核心=+1, 重要=+0, 一般=-1 |
| 故障域 | 中 | CPU/内存/磁盘/容器=需叠加判断 |
| SOP 建议 | 中 | 知识库 SOP 中是否有紧急处理建议 |

**风险等级映射**:
- 5 级 (紧急): 核心业务 + critical 告警 → 立即处理, 需要通知负责人
- 4 级 (高): 核心业务 + high 告警 / 重要业务 + critical 告警 → 优先处理
- 3 级 (中): 一般业务 + high 告警 / 重要业务 + medium 告警 → 正常排期
- 2 级 (低): 一般业务 + medium 告警 → 可延后
- 1 级 (可忽略): 测试环境 / 已知问题 → 标记跟踪

**优先级映射**:
- 紧急: 风险等级 5
- 高:   风险等级 4
- 中:   风险等级 3
- 低:   风险等级 1-2

## Phase 5: 输出报告
报告必须包含以下部分:
```markdown
# 告警诊断报告

**告警类型**: <alert_type>
**设备 IP**: <host_ip>
**应用名称**: <app_name> (来自 CMDB)
**业务等级**: <business_level> (来自 CMDB)
**负责人**: <owner> (来自 CMDB)

## 风险等级: <1-5> 级 · 优先级: <紧急/高/中/低>

## 一、告警概述
- 现象: ...
- 告警来源: Splunk

## 二、关联信息
- CMDB 查询结果: ...
- 知识库匹配 SOP: ...

## 三、根因分析
...

## 四、处置建议
### 紧急措施
...
### 长期优化
...

## 五、结论
...
```

## 注意事项
- **风险等级必须在报告中明确写出**, 格式为 `风险等级: X 级 · 优先级: XXX`
- CMDB 查不到的 IP 标记为 "未知设备", 风险等级默认为 3
- 不要编造工具返回中不存在的数据
- 知识库 SOP 仅作思路参考, 不能直接当作本案例证据
