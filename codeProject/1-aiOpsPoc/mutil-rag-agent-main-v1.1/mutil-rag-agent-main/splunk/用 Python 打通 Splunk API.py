import json
import os

import requests
import urllib3
"""
docker run -d --name splunk --hostname splunk 
-p 8001:8000 -p 8088:8088 -p 8089:8089 -p 9997:9997 
-e "SPLUNK_START_ARGS=--accept-license" -e "SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com" -e "SPLUNK_LICENSE_URI=Free" -e "SPLUNK_PASSWORD=<set-in-environment>" -e "TZ=Asia/Shanghai" 
-v splunk-etc:/opt/splunk/etc -v splunk-var:/opt/splunk/var 
splunk/splunk:10.4.0
"""
# 禁用自签证书的警告信息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 你的 Docker 环境配置
SPLUNK_HOST = 'localhost'
SPLUNK_PORT = 8089  # 注意：API 端口是 8089，千万别填网页的 8001
USERNAME = os.getenv("SPLUNK_USERNAME", "")
PASSWORD = os.getenv("SPLUNK_PASSWORD", "")  # 替换为你 docker run 时的 SPLUNK_PASSWORD

# 2. 刚才跑通的 SPL (注意最前面的 search 关键字)
# 这里我们加了 head 10 以免一次拉取太多，测试跑通后可以去掉
search_query = '''
search index=tutorial status=500
| rename clientip as host_ip, uri_path as api_endpoint
| eval poc_env="local_docker"
| table _time, host_ip, api_endpoint, poc_env
| head 10
'''

# 3. 构造请求参数
url = f"https://{SPLUNK_HOST}:{SPLUNK_PORT}/services/search/jobs/export"
data = {
    "search": search_query,
    "output_mode": "json",  # 核心参数：直接让 Splunk 吐出 JSON
    "earliest_time": "-7d", # 拉取过去7天的数据
    "latest_time": "now"
}

# 4. 发起 POST 请求
print("正在呼叫 Splunk API 获取数据...")
response = requests.post(
    url,
    auth=(USERNAME, PASSWORD),
    data=data,
    verify=False, # 忽略证书校验
    stream=True   # 开启流式读取，防内存撑爆
)

# 5. 解析流式 JSON 输出
if response.status_code == 200:
    for line in response.iter_lines():
        if line:
            # 每行都是一个独立的 JSON 对象
            event = json.loads(line)
            # 提取具体的业务字段 (result 字典)
            result_data = event.get("result", {})
            print(json.dumps(result_data, indent=2, ensure_ascii=False))
else:
    print(f"请求失败，状态码: {response.status_code}")
    print(response.text)
