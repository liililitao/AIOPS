# WAF 告警分析报告

## 告警概要
- 告警名称：test-waf
- 触发时间：2026-07-10 16:20:10.969 +08:00（UTC：2026-07-10 08:20:10.969Z）
- 风险等级：高
- 触发原因：Saved Search [test-waf] always(2)

## 告警数据详情
- 受影响资源：
  - Azure Application Gateway（WAF）：AGW-DAP-PRD-N3-01
  - 访问主机名：purview.novonordiskchina.com.cn
  - 环境：Production
- 攻击路径（请求 URI 摘要）：
  - 环境文件探测：大量 .env/.env.*/.env_backup 等路径
  - 配置/日志探测：/app/config/parameters.yml、/storage/logs/laravel.log
  - 详情见“攻击分析”章节
- 事件计数：
  - 聚合计数：25（search 聚合字段 count）
  - 告警执行计数：2（event_count，来自调度/取样窗口；用于告警触发判定）
- WAF 动作：Blocked（拦截）
- Splunk 原始链接：
  - http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=%7Cloadjob%20rt_scheduler__adminjhgz__search__RMD55e6c7c059c57a98f_at_1783564199_1802.9%20%7C%20head%202%20%7C%20tail%201&earliest=0&latest=now
- Spl 查询（节选）：
  - index=azure category=ApplicationGatewayFirewallLog properties_action=Blocked
    properties_hostname!="novocareapp.novocare.com.cn" AND
    properties_hostname!="test-novocareapp.novocare.com.cn"
    | rex field=resourceId "/(?<id>[^/]+)$"
    | stats values(properties_action) as properties_action values(properties_requestUri) as properties_requestUri count by properties_hostname,id
    | table id,properties_hostname,properties_requestUri,properties_action,count
    | search count>=20

## CMDB 资产信息
- 资产定位方法：
  - 通过告警字段 resourceId 解析到资源名 id=AGW-DAP-PRD-N3-01，随后在 CMDB「Azure PaaS」资产表以 resource_name 精确匹配
- 资产信息结果：
  - 资源名称：AGW-DAP-PRD-N3-01
  - 资源类型：Application gateway
  - 环境：Production
  - 订阅：DAP-PRD
  - 数据来源：Azure PaaS（源表行号 283）

【证据溯源】CMDB 查询方式与结果
- 查询方式：CMDB「Azure PaaS」表，字段 resource_name="AGW-DAP-PRD-N3-01" 精确匹配（match_type=exact）
- 查询结果：
  - found=true，resource_type="Application gateway"，environment="Production"，subscription="DAP-PRD"，source_sheet="Azure PaaS"，source_row=283

## 攻击分析
- 攻击类型分类：
  - 环境文件扫描（env_scan）
  - 配置文件扫描（config_scan）
- 攻击特征：
  - 针对常见框架与部署目录进行环境变量与配置文件路径枚举（如 .env、parameters.yml、laravel 日志）
  - 请求 URI 覆盖多种目录层级与命名变体，具备自动化扫描工具特征
  - 目标主机为生产域名，若后端存在误暴露，可能直接导致凭据、密钥、数据库连接等敏感信息泄露
- 可能影响：
  - 若未被彻底阻断且后台存在可访问的敏感文件，可能造成凭据泄露、进一步横向移动、数据泄露或远程代码执行的风险
  - 当前 WAF 拦截有效，未见放行证据，但需结合后端访问日志确认无命中 200/206 等成功响应
- 已知信息缺口：
  - 源 IP、User-Agent、匹配的具体 WAF 规则 ID/名称未在快照中呈现（建议通过原始日志进一步取证）

【证据溯源】攻击分类结果
- 分类与风险：
  - env_scan（环境文件扫描）：风险=中
  - config_scan（配置文件扫描）：风险=中
- 匹配证据（节选）：
  - env_scan 命中路径：
    /.env.bak, /.env.example, /.env.old, /.env_sample, /api/shared/.env, /api/shared/config/.env, /application/.env, /conf/.env, /core/.env, /dev/.env, /development/.env, /env.backup, /laravel/core/.env, /mailer/.env, /new/.env.local, /new/.env.staging, /node/.env_example, /portal/.env, /public/.env, /site/.env
  - config_scan 命中路径：
    /app/config/parameters.yml, /storage/logs/laravel.log

## 综合风险评估（三维度判定详情）
- 环境维度：高
  - 依据：CMDB 显示资源属于 Production 环境；受影响主机名为生产域名
- 数量维度：低（count=25）
  - 依据：本次聚合计数为 25，规模不大但超过告警阈值（>=20）；可能是短时探测而非大规模 DDoS 式爬扫
- 攻击类型维度：中
  - 依据：以信息探测/目录探测为主，若命中成功危害可高，但当前被 WAF 阻断
- 总体评定：高
  - 依据：生产环境暴露 + 探测目标直指敏感配置/环境文件；即使规模有限，潜在影响面大。需进行后端确认与加固

## 相关运维参考
- 处置结论
  - 当前 WAF 已拦截该类扫描请求；无直接入侵证据
  - 鉴于目标为敏感文件路径，建议视为高风险探测事件，需完成后端核查和预防加固

- 立即核查清单（生产环境）
  - 后端取证
    - 检查对应 Application Gateway 的 Access Log/Backend Health 与后端 Web 服务器访问日志，确认是否存在对上述路径返回 200/206/301/302 等非 4xx/5xx 的响应
    - 在 Splunk 中按客户端 IP、User-Agent、ruleId 分布分析，确认是否存在外溢放行事件或规则绕过
  - 资源与配置
    - 确认生产代码仓库与部署产物中不存在 .env、*.example、*.bak、*.old 等敏感文件
    - 确保 /storage/logs/laravel.log 等日志不对外暴露，必要时通过 Web 服务器/容器层禁止访问敏感路径（返回 403/404）
    - 对所有静态资源目录配置显式拒绝规则（如 Nginx/Apache Location/Directory deny）
  - 凭据与密钥
    - 若任何敏感文件曾可能暴露，立即轮换应用密钥、数据库密码、第三方 API Key，并核查审计日志

- WAF 与监控加固
  - WAF
    - 保持当前阻断策略，新增自定义规则直接拦截包含 “/.env”、“/parameters.yml”、“/laravel.log” 等关键字的请求
    - 启用/加强 Bot 防护与速率限制，对扫描型请求源实施临时封禁（IP/ASN/地理位置维度）
  - 告警优化
    - 将关联搜索补充 sourceIP、User-Agent、ruleId、details 字段入表，便于溯源与封禁
    - 对生产域名的同类扫描阈值适度下调（例如 count>=10）并增加连续时间窗检测
  - 可参考的 Splunk 查询（示例）
    - 按源 IP 统计：
      index=azure category=ApplicationGatewayFirewallLog properties_action=Blocked properties_hostname="purview.novonordiskchina.com.cn"
      | stats count by clientIp_s
    - 查看规则命中：
      index=azure category=ApplicationGatewayFirewallLog properties_action=Blocked properties_hostname="purview.novonordiskchina.com.cn"
      | stats count by msg_s ruleId_s
    - 排查是否有成功响应：
      index=azure category=ApplicationGatewayAccessLog hostname="purview.novonordiskchina.com.cn"
      (requestUri="/*.env*" OR requestUri="*/parameters.yml" OR requestUri="*/laravel.log")
      | stats values(httpStatus) as status,count by clientIp,requestUri

- 长期治理建议
  - 研发与发布流程
    - 在 CI/CD 中加入敏感文件扫描与阻断（.env、*.example、*.bak、*.log 等）
    - 将运行时配置迁移至密钥管理（如 Azure Key Vault），避免平面文件配置
  - 基线与合规
    - 制定 Web 目录访问基线，默认拒绝敏感路径；定期进行黑箱扫描验证
    - 定期轮换密钥与凭据，确保泄露面可控
  - 攻击面监控
    - 将生产域名纳入持续的外部攻击面监控，定期检测弱点与暴露资产

- 备注
  - 本次告警的聚合 count=25 已超过搜索阈值（>=20），虽 event_count=2 来源于调度窗口取样，但足以证明在所监控时间窗内存在持续探测活动
  - 建议在 24–72 小时内持续观察同类扫描趋势，并对重复的来源进行策略化处置（封禁/挑战）

---
*🤖 AI 生成 (openai_gpt5) · 2026-07-27 11:11:46*