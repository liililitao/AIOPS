import json, os, sys, traceback
from http import HTTPStatus
import requests
import splunk

FLASK_BASE = "http://127.0.0.1:5000"

class GatewayProxyHandler:
    def __init__(self, command_line="", command_arg=""):
        pass

    def handle(self, request_json_string):
        try:
            request = json.loads(request_json_string)
            method = request.get("method", "GET")
            path_info = request.get("path_info", "/")
            query = request.get("query", [])
            headers = request.get("headers", [])
            body = request.get("body", "")

            # 构建目标 URL
            target = FLASK_BASE + path_info
            if query:
                target += "?" + "&".join(query)

            # 转发头
            fwd_headers = {}
            for h in headers:
                name = h[0].lower()
                if name not in ("host", "connection", "content-length"):
                    fwd_headers[h[0]] = h[1]

            resp = requests.request(
                method=method, url=target, headers=fwd_headers,
                data=body, timeout=30,
            )

            resp_headers = []
            for k, v in resp.headers.items():
                if k.lower() not in ("connection", "transfer-encoding", "content-encoding"):
                    resp_headers.append([k, v])

            return {
                "status": resp.status_code,
                "headers": resp_headers,
                "body": resp.content.decode("utf-8", errors="replace"),
            }
        except Exception as e:
            traceback.print_exc()
            return {
                "status": 502,
                "headers": [["Content-Type", "text/plain"]],
                "body": f"Gateway error: {e}",
            }