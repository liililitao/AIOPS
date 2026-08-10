# AIOps 应用告警权限

系统使用 Splunk 登录用户名作为用户身份；权限数据存放在网关本地 SQLite 文件。默认路径为 `gateway/data/aiops_authorization.sqlite3`，可用环境变量 `AIOPS_AUTHZ_DB` 改为共享磁盘上的绝对路径。

## 权限模型

- `applications`：7 个受管应用的标准编码。
- `alert_rule_applications`：`app_log_gen.py` 的 16 条告警名称到应用编码的映射。
- `user_roles`：`admin` 可查看所有告警；`user` 只能查看被授予的应用。
- `user_application_permissions`：用户与应用的多对多授权关系；即使当前一个人只管一个应用，也不用修改表结构。

未知告警或未授予权限的用户默认不可见。网关在告警列表、单条告警详情、证据链、Agent 运行记录、工具调用记录和删除操作上统一校验，因此不能通过手工拼接任务 ID 绕过前端列表。

## 初始化和授权

在 `gateway` 目录下执行：

```powershell
python authorization.py init
python authorization.py grant alice iwe
python authorization.py grant bob wecall
python authorization.py set-role admin admin
python authorization.py show-user alice
python authorization.py list-applications
```

初始数据库会自动创建 `admin` 管理员。下面是可授予的应用编码：`iwe`、`wecall`、`pmt`、`dspot`、`rared`、`novocare_diabetes`、`budget_tool`。

生产环境请把后端服务限制在网关所在主机的回环地址，避免用户绕过网关直接访问后端 API。
