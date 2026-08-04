import requests
import json
import time

# 模拟 Splunk 的真实 Payload 结构
mock_payload = {
    "search_name": "[AIOps-POC] 500 Error Real-time Push",
    "result": {
        "_time": str(time.time()), # 模拟当前 UNIX 时间戳
        "host_ip": "99.99.99.99",
        "api_endpoint": "/api/test_mock",
        "poc_env": "local_docker"
    }
}

url = "http://127.0.0.1:8080/api/v1/splunk/alert_receiver"

print(f"正在向 {url} 发送测试告警...")
response = requests.post(url, json=mock_payload)

print(f"HTTP 状态码: {response.status_code}")
print(f"接口返回结果: {response.text}")