from fastapi import FastAPI, Request
from datetime import datetime
import uvicorn

app = FastAPI()

# 模拟一个极简的 CMDB 本地缓存 (实体关联映射)
MOCK_CMDB = {
    "99.99.99.99": {"app_name": "支付网关服务", "owner": "张三", "env": "PROD"},
    "192.168.1.1": {"app_name": "用户中心", "owner": "李四", "env": "UAT"}
}


@app.post("/api/v1/splunk/alert_receiver")
async def receive_splunk_alert(request: Request):
    # 1. 接收 Splunk 推送的 JSON
    payload = await request.json()

    # 2. 提取核心告警内容
    alert_name = payload.get("search_name", "Unknown Alert")
    result_data = payload.get("result", {})

    # 3. 数据清洗：统一时间格式为 ISO 8601
    raw_time = float(result_data.get("_time", 0))
    iso_time = datetime.fromtimestamp(raw_time).isoformat()

    # 4. 提取实体
    host_ip = result_data.get("host_ip", "Unknown IP")

    # 5. 数据关联映射：拿着告警的 IP 去查 CMDB
    cmdb_info = MOCK_CMDB.get(host_ip, {"app_name": "未知应用", "owner": "未知"})

    # 构建送入下游（知识库或大模型）的最终标准上下文
    enriched_event = {
        "event_time": iso_time,
        "alert_type": alert_name,
        "trigger_ip": host_ip,
        "impacted_app": cmdb_info["app_name"],
        "responsible_person": cmdb_info["owner"],
        "raw_endpoint": result_data.get("api_endpoint")
    }

    print(f"\n[AI Agent 捕获告警] {enriched_event['impacted_app']} 发生异常！")
    print(f"标准上下文已生成: {enriched_event}")
    print("-" * 40)

    return {"status": "success", "message": "Alert received and enriched"}


if __name__ == "__main__":
    # 启动本地服务，运行在 8080 端口
    uvicorn.run(app, host="0.0.0.0", port=8080)