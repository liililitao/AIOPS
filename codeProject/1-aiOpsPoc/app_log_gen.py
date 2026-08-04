#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用告警日志生成器 — 基于 Splunk 告警规则 SPL 倒推生成模拟日志
=============================================================
数据来源: 应用告警信息列表.xlsx (16 条告警规则)
设计思路:
  - 从每条规则的 SPL 语句中反向推导出「会触发该告警的日志长什么样」
  - 为每条规则建立数据池 (字段值池 + 条件约束)
  - 交互式选择规则 + 输入生成条数 → 输出 CSV

用法:
  python app_log_gen.py          # 交互模式
  python app_log_gen.py --list   # 只列出所有规则
"""

import csv
import os
import random
import sys
from datetime import datetime, timezone, timedelta

# ==================== 配置区 ====================
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_log_app")
# ================================================


# ============================================================
# 16 条告警规则的日志生成配置
# 每条规则定义:
#   - meta_fields:    固定元数据 (index/sourcetype/source 等)
#   - condition_fields: 必须等于某值的字段 (触发告警的必要条件)
#   - negative_fields:  必须不等于某值的字段
#   - output_fields:   CSV 列名列表 (从 SPL stats 子句提取)
#   - data_pools:      各字段的随机值池
#   - eval_rules:      需要运行时动态计算的字段 (如 old_light!=now_light)
# ============================================================

RULE_CONFIGS = [
    # ===== Rule 1: iWE Login Failed =====
    {
        "id": 1,
        "sn": "10069",
        "system": "iWE",
        "alert_name": "app_alert_iwe_Login_Failed",
        "raw_spl": 'index=app_s_6month sourcetype=iwe source=iwe_log_action result="failed"\n|stats count by _time,initial,query,result',
        "meta_fields": {
            "target_index": "app_s_6month",
            "sourcetype": "iwe",
            "source": "iwe_log_action",
        },
        "condition_fields": {
            "result": "failed",
        },
        "negative_fields": {},
        "output_fields": ["_time", "initial", "query", "result"],
        "data_pools": {
            "initial": [
                "zhangsan", "lisi", "wangwu", "zhaoliu", "chenqi",
                "liuxing", "sunyue", "zhouhao", "wuming", "huangfei",
            ],
            "query": [
                "SELECT * FROM users WHERE id=?",
                "UPDATE users SET password=? WHERE id=?",
                "INSERT INTO logs (user,action) VALUES (?,?)",
                "DELETE FROM sessions WHERE expired=?",
                "SELECT COUNT(*) FROM orders WHERE status=?",
            ],
            "result": ["failed"],
        },
    },

    # ===== Rule 2: iWE Data Docking Failure =====
    {
        "id": 2,
        "sn": "10069",
        "system": "iWE",
        "alert_name": "app_alert_iwe_Data_Docking_Failure",
        "raw_spl": 'index=app_s_6month sourcetype=iwe source=iwe_iwe2022service_log status="failed"\n|stats count by _time,url,status',
        "meta_fields": {
            "target_index": "app_s_6month",
            "sourcetype": "iwe",
            "source": "iwe_iwe2022service_log",
        },
        "condition_fields": {
            "status": "failed",
        },
        "negative_fields": {},
        "output_fields": ["_time", "url", "status"],
        "data_pools": {
            "url": [
                "/api/v1/data/sync/order",
                "/api/v1/data/sync/user",
                "/api/v1/data/sync/product",
                "/api/v1/data/import/sales",
                "/api/v1/data/export/report",
                "/api/v1/external/wechat/callback",
                "/api/v2/integration/sap/material",
            ],
            "status": ["failed"],
        },
    },

    # ===== Rule 3: WeCall Password Verification Failed =====
    {
        "id": 3,
        "sn": "12722",
        "system": "WeCall",
        "alert_name": "app_alert_wecall_Password_Verification_Failed",
        "raw_spl": 'index=app_s_12month sourcetype=wecall source=sys_log_action query="s=console/public/checkpwd.html" status=0 \n| stats count by _time,createip,admin,action,query,status',
        "meta_fields": {
            "target_index": "app_s_12month",
            "sourcetype": "wecall",
            "source": "sys_log_action",
        },
        "condition_fields": {
            "query": "s=console/public/checkpwd.html",
            "status": 0,
        },
        "negative_fields": {},
        "output_fields": ["_time", "createip", "admin", "action", "query", "status"],
        "data_pools": {
            "createip": [
                "192.168.1.100", "192.168.1.101", "10.0.0.55",
                "10.0.0.88", "172.16.3.20", "172.16.3.25",
            ],
            "admin": [
                "admin_zhang", "admin_li", "admin_wang",
                "operator_chen", "operator_zhao",
            ],
            "action": [
                "console_login", "password_verify", "check_pwd",
            ],
            "query": ["s=console/public/checkpwd.html"],
            "status": [0],
        },
    },

    # ===== Rule 4: PMT Different Light Status =====
    {
        "id": 4,
        "sn": "13263",
        "system": "PMT for S&D",
        "alert_name": "app_alert_pmt_Dif_Light",
        "raw_spl": 'index=app_s_12month sourcetype=pmt source=sd_validation_log action_user=cld \n|eval res=if(old_light==now_light,1,0)\n|search res=0\n|stats count by _time,action_user,old_light,now_light',
        "meta_fields": {
            "target_index": "app_s_12month",
            "sourcetype": "pmt",
            "source": "sd_validation_log",
        },
        "condition_fields": {
            "action_user": "cld",
        },
        "negative_fields": {},
        "output_fields": ["_time", "action_user", "old_light", "now_light"],
        "data_pools": {
            "action_user": ["cld"],
        },
        # eval: res=if(old_light==now_light,1,0) | search res=0 → old_light != now_light
        "eval_rules": {
            "old_light": {
                "pool": ["red", "yellow", "green", "off"],
            },
            "now_light": {
                "pool": ["red", "yellow", "green", "off"],
                "must_differ_from": "old_light",
            },
        },
    },

    # ===== Rule 5: PMT Login Failed =====
    {
        "id": 5,
        "sn": "13263",
        "system": "PMT for S&D",
        "alert_name": "app_alert_pmt_Login_Failed",
        "raw_spl": 'index=app_s_12month sourcetype=pmt source=sd_log_action detail=登录失败 \n| stats values(_time) as time values(action) as action values(query) as query values(detail) as detail count by module \n| eval time=strftime(time,"%Y/%m/%d %H:%M:%S") \n| table time,',
        "meta_fields": {
            "target_index": "app_s_12month",
            "sourcetype": "pmt",
            "source": "sd_log_action",
        },
        "condition_fields": {
            "detail": "登录失败",
        },
        "negative_fields": {},
        "output_fields": ["_time", "module", "action", "query", "detail"],
        "data_pools": {
            "module": [
                "SD_ORDER", "SD_PRICE", "SD_CONTRACT", "SD_CUSTOMER",
                "SD_INVENTORY", "SD_SHIPPING",
            ],
            "action": [
                "LOGIN", "AUTH", "VERIFY",
            ],
            "query": [
                "/pmt/login/check",
                "/pmt/sd/authenticate",
                "/pmt/api/v1/login",
            ],
            "detail": ["登录失败"],
        },
    },

    # ===== Rule 6: PMT Token Invalid =====
    {
        "id": 6,
        "sn": "14563",
        "system": "D.Spot",
        "alert_name": "app_alert_pmt_Token_Invalid",
        "raw_spl": 'index=app_s_12month sourcetype=pmt source=sd_api_log "token invalid" \n| stats count by _time,vendor,param,msg',
        "meta_fields": {
            "target_index": "app_s_12month",
            "sourcetype": "pmt",
            "source": "sd_api_log",
        },
        "condition_fields": {
            # SPL 用 "token invalid" 模糊搜索 → msg 字段包含该字符串
        },
        "negative_fields": {},
        "output_fields": ["_time", "vendor", "param", "msg"],
        "data_pools": {
            "vendor": [
                "IQVIA", "Veeva", "ZS_Associates", "SAS_Institute",
                "Oracle_Health", "MediData",
            ],
            "param": [
                '{"token":"expired_token_abc123"}',
                '{"token":"invalid_signature_xyz"}',
                '{"auth":"Bearer invalid_token_789"}',
                '{"access_token":"revoked_key_456"}',
            ],
            "msg": [
                "token invalid: signature verification failed",
                "token invalid: expired at 2026-07-01T00:00:00Z",
                "token invalid: revoked by admin",
                "token invalid: issuer mismatch",
                "token invalid: audience not allowed",
            ],
        },
    },

    # ===== Rule 7: D.Spot Login Failed =====
    {
        "id": 7,
        "sn": "14563",
        "system": "D.Spot",
        "alert_name": "app_alert_dspot_Login_Failed",
        "raw_spl": 'index=app_s_12month sourcetype=dspot* Operations=*Login* Result=Fail\n| eval useraccount=coalesce(UserAccount,userAccount) \n| eval msg=coalesce(customField,content) \n| stats values(_time) as time values(msg) as msg count by useraccount',
        "meta_fields": {
            "target_index": "app_s_12month",
            "sourcetype": "dspot_prod",
        },
        "condition_fields": {
            "Operations": "UserLogin",
            "Result": "Fail",
        },
        "negative_fields": {},
        "output_fields": ["_time", "UserAccount", "Operations", "Result",
                          "customField"],
        "data_pools": {
            "UserAccount": [
                "user001@example.com", "user002@example.com",
                "user003@example.com", "user004@example.com",
                "john.smith@partner.com", "jane.doe@agency.com",
            ],
            "Operations": [
                "UserLogin", "SSOLogin", "OAuthLogin", "ExternalLogin",
            ],
            "Result": ["Fail"],
            "customField": [
                "密码错误", "账号不存在", "账号已被锁定",
                "IP不在白名单", "验证码错误", "多次尝试后锁定",
                "密码已过期", "双因素认证失败",
            ],
        },
    },

    # ===== Rule 8: D.Spot Export Failed =====
    {
        "id": 8,
        "sn": "12611",
        "system": "RareD NovoCare",
        "alert_name": "app_alert_dspot_Export_Failed",
        "raw_spl": 'index=app_s_12month sourcetype=dspot* operations="export data" fail\n| eval useraccount=coalesce(UserAccount,userAccount) \n| eval msg=coalesce(customField,content) \n| eval result=coalesce(result,Result)\n| stats count by _time,useraccount,msg,result',
        "meta_fields": {
            "target_index": "app_s_12month",
            "sourcetype": "dspot_prod",
        },
        "condition_fields": {
            "operations": "export data",
        },
        "negative_fields": {},
        "output_fields": ["_time", "UserAccount", "operations", "Result",
                          "customField"],
        "data_pools": {
            "UserAccount": [
                "user005@example.com",
                "user006@example.com",
                "doctor.wang@hospital.cn",
                "researcher.chen@university.edu",
            ],
            "operations": ["export data"],
            "Result": [
                "fail", "fail_timeout", "fail_permission_denied",
                "fail_quota_exceeded", "fail_data_too_large",
            ],
            "customField": [
                "导出超时: 数据量超过100万行",
                "权限不足: 用户无导出全量数据权限",
                "格式转换失败: PDF生成异常",
                "存储空间不足: 临时文件写入失败",
            ],
        },
    },

    # ===== Rule 9: RareD Add Role =====
    {
        "id": 9,
        "sn": "12611",
        "system": "RareD NovoCare",
        "alert_name": "app_alert_rared_Add_Role",
        "raw_spl": 'index=app_s_6month sourcetype=rared OperateType=1009\n|stats count by OperateTime,OperateWorkerName,OperateDescription',
        "meta_fields": {
            "target_index": "app_s_6month",
            "sourcetype": "rared",
        },
        "condition_fields": {
            "OperateType": 1009,
        },
        "negative_fields": {},
        "output_fields": ["OperateTime", "OperateWorkerName",
                          "OperateDescription", "OperateType"],
        "data_pools": {
            "OperateWorkerName": [
                "sysadmin_zhang", "sysadmin_li", "sysadmin_wang",
                "it_manager_chen", "it_admin_zhao",
            ],
            "OperateDescription": [
                "新增角色: 数据管理员",
                "新增角色: 报告查看者",
                "新增角色: 系统配置管理员",
                "新增角色: 审计日志查看者",
                "新增角色: 用户管理权限组",
            ],
            "OperateType": [1009],
        },
    },

    # ===== Rule 10: RareD Edit Points =====
    {
        "id": 10,
        "sn": "12611",
        "system": "RareD NovoCare",
        "alert_name": "app_alert_rared_Edit_Points",
        "raw_spl": 'index=app_s_6month sourcetype=rared OperateType=1059\n|stats count by OperateTime,OperateWorkerName,OperateDescription',
        "meta_fields": {
            "target_index": "app_s_6month",
            "sourcetype": "rared",
        },
        "condition_fields": {
            "OperateType": 1059,
        },
        "negative_fields": {},
        "output_fields": ["OperateTime", "OperateWorkerName",
                          "OperateDescription", "OperateType"],
        "data_pools": {
            "OperateWorkerName": [
                "doctor_zhang", "doctor_li", "nurse_wang",
                "pharmacist_chen", "coordinator_zhao",
            ],
            "OperateDescription": [
                "修改积分规则: 处方录入积分+5",
                "修改积分规则: 患者教育积分+3",
                "编辑积分兑换比例: 100分=50元",
                "修改积分有效期: 从12个月改为6个月",
                "编辑积分获取上限: 每日上限100分",
            ],
            "OperateType": [1059],
        },
    },

    # ===== Rule 11: RareD PII Export =====
    {
        "id": 11,
        "sn": "13695",
        "system": "NovoCare Diabetes",
        "alert_name": "app_alert_rared_PII_export",
        "raw_spl": 'index=app_s_6month sourcetype=rared OperateType=1039 OperateWorkerName!="梁凯诚"\n|stats count by OperateTime,OperateWorkerName,OperateDescription',
        "meta_fields": {
            "target_index": "app_s_6month",
            "sourcetype": "rared",
        },
        "condition_fields": {
            "OperateType": 1039,
        },
        "negative_fields": {
            "OperateWorkerName": ["梁凯诚"],
        },
        "output_fields": ["OperateTime", "OperateWorkerName",
                          "OperateDescription", "OperateType"],
        "data_pools": {
            "OperateWorkerName": [
                "wang.xiaoming", "li.dahua", "zhang.sanfeng",
                "chen.xiaodong", "zhao.mei", "sun.liang",
                "zhou.jie", "wu.gang", "huang.he", "liu.xing",
            ],
            "OperateDescription": [
                "导出患者个人信息: 姓名+身份证号+手机号",
                "导出医生处方数据: 含患者姓名+诊断信息",
                "导出护士随访记录: 含患者联系方式",
                "导出药品配送信息: 含患者地址+电话",
                "导出医保结算数据: 含身份证号",
            ],
            "OperateType": [1039],
        },
    },

    # ===== Rule 12: NovoCare Diabetes Change Role Privileges =====
    {
        "id": 12,
        "sn": "12478",
        "system": "NNRC Diabetes.com",
        "alert_name": "app_alert_novocare_diabetes_Change_of_Role_Privileges",
        "raw_spl": 'index=app_s_6month sourcetype=novocare_diabetes title="权限、菜单按钮绑定"\n| stats count by _time,title,operator_user,operator_url',
        "meta_fields": {
            "target_index": "app_s_6month",
            "sourcetype": "novocare_diabetes",
        },
        "condition_fields": {
            "title": "权限、菜单按钮绑定",
        },
        "negative_fields": {},
        "output_fields": ["_time", "title", "operator_user", "operator_url"],
        "data_pools": {
            "title": ["权限、菜单按钮绑定"],
            "operator_user": [
                "admin_sys", "manager_li", "supervisor_wang",
                "developer_chen", "tester_zhao",
            ],
            "operator_url": [
                "/admin/role/bind_menu",
                "/admin/role/update_privilege",
                "/admin/permission/grant",
                "/system/role/edit_menu_bind",
            ],
        },
    },

    # ===== Rule 13: NovoCare Diabetes Modify User =====
    {
        "id": 13,
        "sn": "12478",
        "system": "NNRC Diabetes.com",
        "alert_name": "app_alert_novocare_diabetes_Modify_User",
        "raw_spl": 'index=app_s_6month sourcetype=novocare_diabetes title="用户管理添加/编辑操作日志"\n| stats count by _time,title,operator_user,operator_url',
        "meta_fields": {
            "target_index": "app_s_6month",
            "sourcetype": "novocare_diabetes",
        },
        "condition_fields": {
            "title": "用户管理添加/编辑操作日志",
        },
        "negative_fields": {},
        "output_fields": ["_time", "title", "operator_user", "operator_url"],
        "data_pools": {
            "title": ["用户管理添加/编辑操作日志"],
            "operator_user": [
                "hr_admin_zhang", "hr_admin_li", "dept_manager_wang",
                "system_admin_chen",
            ],
            "operator_url": [
                "/admin/user/add",
                "/admin/user/edit/1001",
                "/user/management/create",
                "/system/user/update_profile/2035",
            ],
        },
    },

    # ===== Rule 14: NovoCare Diabetes User Data Export =====
    {
        "id": 14,
        "sn": "12478",
        "system": "NNRC Diabetes.com",
        "alert_name": "app_alert_novocare_diabetes_User_Data_Export",
        "raw_spl": 'index=app_s_6month sourcetype=NCDiabetes source=np_user_operate_log TKey=Export host="app.Diabetes.com.cn" UserAccount!=richardxiu@hbraas.com UserAccount!=julixue@hbraas.com\n| stats count by _time,UserAccount,TKey,operate_info,OperateResult',
        "meta_fields": {
            "target_index": "app_s_6month",
            "sourcetype": "NCDiabetes",
            "source": "np_user_operate_log",
            "host": "app.Diabetes.com.cn",
        },
        "condition_fields": {
            "TKey": "Export",
        },
        "negative_fields": {
            "UserAccount": ["richardxiu@hbraas.com", "julixue@hbraas.com"],
        },
        "output_fields": ["_time", "UserAccount", "TKey", "operate_info",
                          "OperateResult"],
        "data_pools": {
            "UserAccount": [
                "user007@example.com",
                "doctor.li@hospital.cn",
                "user008@example.com",
                "researcher.chen@agency.com",
                "coordinator.zhao@partner.org",
            ],
            "TKey": ["Export"],
            "operate_info": [
                "导出患者列表 (3,562条)",
                "导出医生处方统计 (1,280条)",
                "导出随访记录 (8,901条)",
                "导出血糖监测数据 (15,230条)",
                "导出患者教育完成率报表",
            ],
            "OperateResult": [
                "Success", "Success_Partial", "Success_Async",
            ],
        },
    },

    # ===== Rule 15: Budget Tool Login Failed =====
    {
        "id": 15,
        "sn": "11780",
        "system": "NNRC Budget Tool",
        "alert_name": "app_alert_budget_tool_Login_Failed",
        "raw_spl": 'index=app_s_2year sourcetype=budgettool Level=ERROR Operations="登录" \n| stats values(_time) as time values(Result) as Result count by UserAccount,Operations',
        "meta_fields": {
            "target_index": "app_s_2year",
            "sourcetype": "budgettool",
        },
        "condition_fields": {
            "Level": "ERROR",
            "Operations": "登录",
        },
        "negative_fields": {},
        "output_fields": ["_time", "UserAccount", "Operations", "Result",
                          "Level"],
        "data_pools": {
            "UserAccount": [
                "user009@example.com",
                "user010@example.com",
                "user011@example.com",
                "user012@example.com",
            ],
            "Operations": ["登录"],
            "Level": ["ERROR"],
            "Result": [
                "密码错误", "账号被禁用", "验证码错误",
                "IP地址未授权", "登录超时", "Session过期",
            ],
        },
    },

    # ===== Rule 16: Budget Tool System Error =====
    {
        "id": 16,
        "sn": "11780",
        "system": "NNRC Budget Tool",
        "alert_name": "app_alert_budget_tool_System_Error",
        "raw_spl": 'index=app_s_2year sourcetype=budgettool Level=ERROR Operations!=登录 \n| stats count by _time,UserAccount,Operations,Result',
        "meta_fields": {
            "target_index": "app_s_2year",
            "sourcetype": "budgettool",
        },
        "condition_fields": {
            "Level": "ERROR",
        },
        "negative_fields": {
            "Operations": ["登录"],
        },
        "output_fields": ["_time", "UserAccount", "Operations", "Result",
                          "Level"],
        "data_pools": {
            "UserAccount": [
                "system_auto", "scheduler_batch",
                "user013@example.com",
                "user014@example.com",
            ],
            "Operations": [
                "数据导入", "报表生成", "预算计算", "数据同步",
                "数据库查询", "文件导出", "邮件发送", "定时任务",
            ],
            "Level": ["ERROR"],
            "Result": [
                "数据库连接超时", "SQL执行异常: ORA-00001",
                "文件读写失败: 权限不足",
                "外部API调用失败: HTTP 503",
                "内存溢出: OutOfMemoryError",
                "死锁检测: 事务回滚",
                "数据校验失败: 格式不符",
            ],
        },
    },
]

# ============================================================
# 日志生成核心
# ============================================================


def generate_one(config: dict) -> dict:
    """根据规则配置生成一条满足告警条件的日志"""
    log = {}

    # 1. 元数据字段 (固定值)
    for field, value in config.get("meta_fields", {}).items():
        log[field] = value

    # 2. 条件字段 (必须等于的值)
    for field, value in config.get("condition_fields", {}).items():
        log[field] = value

    # 3. 输出字段 (从数据池随机取)
    for field, pool in config.get("data_pools", {}).items():
        log[field] = random.choice(pool)

    # 4. 负面条件字段 (排除特定值)
    for field, excludes in config.get("negative_fields", {}).items():
        # 如果该字段还没值，从数据池里给一个（排除禁止的值）
        if field not in log:
            pool = config.get("data_pools", {}).get(field, ["unknown"])
            allowed = [v for v in pool if v not in excludes]
            log[field] = random.choice(allowed) if allowed else "generated_value"
        else:
            # 字段已有值（来自 condition_fields 或 data_pools），
            # 确保不在排除列表中
            if log[field] in excludes:
                pool = config.get("data_pools", {}).get(field, ["unknown"])
                allowed = [v for v in pool if v not in excludes]
                if allowed:
                    log[field] = random.choice(allowed)

    # 5. 动态求值规则 (如 old_light != now_light)
    eval_rules = config.get("eval_rules", {})
    if eval_rules:
        for field, rule in eval_rules.items():
            if "must_differ_from" in rule:
                # 保证该字段值与指定字段不同
                target_field = rule["must_differ_from"]
                target_value = log.get(target_field, "")
                pool = [v for v in rule["pool"] if v != target_value]
                log[field] = random.choice(pool)
            else:
                log[field] = random.choice(rule["pool"])

    # 6. 生成时间戳 (_time / OperateTime)
    now = datetime.now(timezone(timedelta(hours=8)))
    ts_str = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"

    if "_time" in config["output_fields"]:
        log["_time"] = ts_str
    if "OperateTime" in config["output_fields"]:
        log["OperateTime"] = ts_str

    return log


def get_output_filename(config: dict) -> str:
    """固定文件名: {alert_name}.csv — 每次追加写入同一文件"""
    return f"{config['alert_name']}.csv"


def run_generation(rule_index: int, count: int) -> str:
    """执行生成，返回输出文件路径（按 target_index 分流到子目录）"""
    config = RULE_CONFIGS[rule_index]  # 0-based

    # 按 sourcetype 分流: test_log_app/iwe/ 等
    sourcetype = config["meta_fields"].get("sourcetype", "unknown")
    sub_dir = os.path.join(OUTPUT_DIR, sourcetype)
    os.makedirs(sub_dir, exist_ok=True)

    fname = get_output_filename(config)
    fpath = os.path.join(sub_dir, fname)
    file_exists = os.path.isfile(fpath)

    # 追加模式写入（和 waf_log_gen.py 一样）
    fieldnames = config["output_fields"]

    with open(fpath, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for i in range(count):
            log = generate_one(config)
            # 只输出 output_fields 中定义的列
            row = {k: log.get(k, "") for k in fieldnames}
            writer.writerow(row)

        f.flush()

    return fpath


# ============================================================
# 交互式 CLI
# ============================================================


def list_rules():
    """列出所有告警规则"""
    print("-" * 90)
    print(f"{'#':<3} {'SN':<8} {'System':<22} {'Alert Name':<45}")
    print("-" * 90)
    for cfg in RULE_CONFIGS:
        print(f"{cfg['id']:<3} {cfg['sn']:<8} {cfg['system']:<22} "
              f"{cfg['alert_name']:<45}")
    print("-" * 90)


def show_rule_detail(rule_index: int):
    """显示单条规则的详细信息"""
    cfg = RULE_CONFIGS[rule_index]
    print("=" * 70)
    print(f"  Rule #{cfg['id']}  |  SN: {cfg['sn']}  |  {cfg['system']}")
    print(f"  Alert: {cfg['alert_name']}")
    print("=" * 70)
    print()

    # SPL 原文
    raw = _get_raw_spl(rule_index)
    print(f"  [SPL 原文]")
    print(f"  {raw}")
    print()

    print(f"  [倒推的日志结构]")
    print(f"  元数据字段:")
    for k, v in cfg["meta_fields"].items():
        print(f"    {k} = {v}")
    print(f"  条件字段 (必须等于):")
    for k, v in cfg.get("condition_fields", {}).items():
        print(f"    {k} = {v}")
    negatives = cfg.get("negative_fields", {})
    if negatives:
        print(f"  排除字段 (必须不等于):")
        for k, v in negatives.items():
            print(f"    {k} != {v}")
    eval_rules = cfg.get("eval_rules", {})
    if eval_rules:
        print(f"  动态规则:")
        for k, r in eval_rules.items():
            if "must_differ_from" in r:
                print(f"    {k} != {r['must_differ_from']} (从 {r['pool']} 中随机)")
            else:
                print(f"    {k} ∈ {r['pool']}")
    print(f"  CSV 输出字段: {', '.join(cfg['output_fields'])}")
    print(f"  数据池字段数: {len(cfg['data_pools'])}")
    print()


def _get_raw_spl(rule_index: int) -> str:
    """从硬编码配置中获取原始 SPL"""
    return RULE_CONFIGS[rule_index].get("raw_spl", "(SPL 未配置)")


def interactive_mode():
    """交互模式主循环"""
    print()
    print("=" * 50)
    print("  应用告警日志生成器 — App Log Generator")
    print("  数据源: 应用告警信息列表.xlsx (16条规则)")
    print("=" * 50)

    while True:
        print()
        list_rules()
        print()
        print("  操作:")
        print("    输入 1-16  选择告警规则")
        print("    输入 L     列出所有规则")
        print("    输入 D<N>  查看规则详情 (如 D4)")
        print("    输入 Q     退出")
        print()

        choice = input("  > ").strip()

        if choice.upper() == "Q":
            print("  已退出.")
            break

        if choice.upper() == "L":
            list_rules()
            continue

        if choice.upper().startswith("D"):
            try:
                idx = int(choice[1:]) - 1
                if 0 <= idx < 16:
                    show_rule_detail(idx)
                else:
                    print(f"  [!] 规则编号需在 1-16 之间")
            except ValueError:
                print(f"  [!] 格式错误，示例: D4")
            continue

        try:
            rule_num = int(choice)
            if rule_num < 1 or rule_num > 16:
                print(f"  [!] 规则编号需在 1-16 之间")
                continue

            rule_index = rule_num - 1
            show_rule_detail(rule_index)

            # 输入条数
            count_str = input(f"  请输入生成条数 (默认100): ").strip()
            if not count_str:
                count = 100
            else:
                try:
                    count = int(count_str)
                    if count < 1:
                        print("  [!] 条数必须大于0")
                        continue
                except ValueError:
                    print("  [!] 请输入有效数字")
                    continue

            # 确认
            cfg = RULE_CONFIGS[rule_index]
            print()
            print(f"  即将生成 {count} 条日志 → 规则 #{cfg['id']} ({cfg['alert_name']})")
            confirm = input(f"  确认? (Y/n): ").strip().upper()
            if confirm and confirm != "Y":
                print("  已取消.")
                continue

            # 生成
            print(f"  生成中...")
            fpath = run_generation(rule_index, count)
            print(f"  [✓] 已生成 {count} 条日志 → {fpath}")
            print()

        except ValueError:
            print(f"  [!] 无效输入，请输入数字 1-16 或命令")
            continue


# ============================================================
# Main
# ============================================================

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_rules()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
