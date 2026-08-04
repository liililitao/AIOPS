#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 认证网关 — Splunk 认证 + 静态文件托管 + 后端 API 代理
===========================================================
用途: 复用 Splunk 用户认证，为同事的 AIOps 前端页面提供认证壳，
     同时代理 /api/v1/* 请求到同事的后端服务。

部署: 见 gateway_deploy.md，或直接 python gateway.py 启动
"""

import os
import time
import uuid

import jwt
import requests
from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_from_directory,
)

# ==================== 配置 (环境变量) ====================
SPLUNK_HOST = os.environ.get("SPLUNK_HOST", "127.0.0.1")
SPLUNK_PORT = os.environ.get("SPLUNK_PORT", "8089")          # Splunk 管理端口
SPLUNK_WEB_URL = os.environ.get("SPLUNK_WEB_URL",
                                "http://127.0.0.1:8000")     # Splunk Web 登录页 (认证失败时跳转)

BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8001")        # 同事后端服务端口

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_EXP_HOURS = int(os.environ.get("JWT_EXP_HOURS", "8"))    # JWT 有效期，对齐 Splunk session 超时

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
# ==========================================================

app = Flask(__name__)

# 禁用 SSL 证书校验 (测试机自签证书)
requests.packages.urllib3.disable_warnings()


# ==================== JWT 工具 ====================

def create_jwt(username, roles):
    """根据 Splunk 用户信息签发 JWT"""
    now = int(time.time())
    payload = {
        "sub": username,
        "roles": roles,
        "iat": now,
        "exp": now + JWT_EXP_HOURS * 3600,
        "jti": uuid.uuid4().hex[:12],
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt(token):
    """验证 JWT，成功返回 payload，失败返回 None"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ==================== Splunk 认证 ====================

def validate_splunk_token(splunk_token):
    """
    向 Splunk REST API 验证 session token 是否有效
    有效 → 返回 {"username": ..., "roles": [...]}
    无效 → 返回 None
    """
    url = f"https://{SPLUNK_HOST}:{SPLUNK_PORT}/services/authentication/current-context"
    headers = {"Authorization": f"Splunk {splunk_token}"}
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        if resp.status_code == 200:
            # Splunk 返回 XML，从 <entry> 中提取关键字段
            body = resp.text
            username = _extract_xml(body, "username")
            roles_raw = _extract_xml(body, "roles")
            roles = [r.strip() for r in roles_raw.split(",") if r.strip()] if roles_raw else []
            return {"username": username or "unknown", "roles": roles}
        else:
            print(f"[!] Splunk 认证拒绝: HTTP {resp.status_code}")
            return None
    except requests.RequestException as e:
        print(f"[!] 连接 Splunk 失败: {e}")
        return None


def _extract_xml(text, key):
    """从 Splunk REST API 返回的 XML 中提取 <s:key>value</s:key>"""
    import re
    match = re.search(rf"<s:{key}>(.*?)</s:{key}>", text)
    return match.group(1) if match else None


# ==================== 认证中间件 ====================

@app.before_request
def check_auth():
    """
    所有请求前置认证:
    1. 跳过健康检查和静态资源(首次访问可能无 cookie)
    2. 检查 URL 中的 splunk_token → 首次进入, 验证后种 JWT cookie
    3. 检查 JWT cookie → 已认证用户放行
    4. 都不满足 → 302 跳转到 Splunk 登录页
    """
    path = request.path

    # 跳过健康检查
    if path == "/health":
        return

    # ---- 方式 1: Splunk Dashboard 按钮用 $env:user$ 传用户名 ----
    # 信任 Splunk 已登录页面, 直接按用户名签发 JWT
    user_param = request.args.get("splunk_user")
    if user_param:
        jwt_token = create_jwt(user_param, [])
        print(f"[+] Splunk 用户认证: {user_param} (来自 Dashboard 按钮)")

        clean_url = path  # 去掉 query string
        resp = redirect(clean_url)
        resp.set_cookie(
            "auth_token", jwt_token,
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=JWT_EXP_HOURS * 3600,
        )
        return resp

    # ---- 方式 2: URL 中携带 splunk_token (测试用) ----
    query_token = request.args.get("splunk_token")
    if query_token:
        user_info = validate_splunk_token(query_token)
        if user_info:
            jwt_token = create_jwt(user_info["username"], user_info["roles"])
            print(f"[+] Splunk token 认证成功: {user_info['username']}")

            clean_url = path
            resp = redirect(clean_url)
            resp.set_cookie(
                "auth_token", jwt_token,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=JWT_EXP_HOURS * 3600,
            )
            return resp
        else:
            print(f"[!] Splunk token 验证失败")
            return jsonify({"success": False, "msg": "Splunk 认证失败，请重新登录"}), 401

    # ---- 后续请求: 检查 JWT cookie ----
    jwt_token = request.cookies.get("auth_token")
    if jwt_token:
        payload = verify_jwt(jwt_token)
        if payload:
            g.current_user = payload["sub"]
            g.current_roles = payload.get("roles", [])
            return  # 放行
        else:
            # JWT 过期
            resp = redirect(SPLUNK_WEB_URL)
            resp.delete_cookie("auth_token")
            return resp

    # ---- 无 token 无 cookie → 踢回 Splunk 登录 ----
    return redirect(SPLUNK_WEB_URL)


# ==================== 路由: 静态文件 ====================

INDEX_TEMPLATE = None


def _get_index_html():
    """读取 index.html 并注入 APP_CONFIG，缓存结果"""
    global INDEX_TEMPLATE
    if INDEX_TEMPLATE is None:
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        # 在 </head> 前注入 APP_CONFIG
        inject_script = (
            '<script>window.APP_CONFIG={API_BASE:"/api/v1"};</script>\n</head>'
        )
        html = html.replace("</head>", inject_script)

        # 修复 CSS 路径: /styles.css → /app/styles.css
        html = html.replace('href="/styles.css"', 'href="/app/styles.css"')

        INDEX_TEMPLATE = html
    return INDEX_TEMPLATE


@app.route("/app/")
@app.route("/app")
def serve_index():
    """返回 index.html (注入 APP_CONFIG 后)"""
    return render_template_string(_get_index_html())


@app.route("/app/<path:filename>")
def serve_static(filename):
    """返回 frontend/ 下的 JS/CSS/图片等静态文件"""
    return send_from_directory(FRONTEND_DIR, filename)


# ==================== 路由: API 代理 ====================

BACKEND_BASE = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

PROXY_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]


@app.route("/api/v1/", defaults={"path": ""}, methods=PROXY_METHODS)
@app.route("/api/v1/<path:path>", methods=PROXY_METHODS)
def proxy_api(path):
    """反向代理 /api/v1/* 到同事的后端服务"""
    target_url = f"{BACKEND_BASE}/api/v1/{path}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"

    # 转发请求头 (排除 hop-by-hop 头)
    headers = {}
    for key, value in request.headers:
        if key.lower() not in ("host", "connection", "transfer-encoding"):
            headers[key] = value

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            params=request.args,
            stream=True,
            timeout=30,
        )
    except requests.ConnectionError:
        return jsonify({"success": False, "msg": "后端服务不可达"}), 502
    except requests.Timeout:
        return jsonify({"success": False, "msg": "后端服务响应超时"}), 504

    # 返回代理响应 (排除 hop-by-hop 响应头)
    excluded_headers = ("connection", "transfer-encoding", "content-encoding")
    proxy_headers = [
        (k, v) for k, v in resp.raw.headers.items()
        if k.lower() not in excluded_headers
    ]
    return resp.content, resp.status_code, proxy_headers


# ==================== 路由: 健康检查 ====================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Flask Auth Gateway",
        "splunk_host": SPLUNK_HOST,
        "backend": f"{BACKEND_HOST}:{BACKEND_PORT}",
    })


# ==================== 启动 ====================

if __name__ == "__main__":
    print("=" * 55)
    print("  Flask 认证网关")
    print(f"  Splunk 认证:    {SPLUNK_HOST}:{SPLUNK_PORT}")
    print(f"  后端服务:       {BACKEND_HOST}:{BACKEND_PORT}")
    print(f"  Splunk Web:     {SPLUNK_WEB_URL}")
    print(f"  JWT 有效期:     {JWT_EXP_HOURS} 小时")
    print(f"  静态文件目录:   {FRONTEND_DIR}")
    print("=" * 55)
    app.run(host="127.0.0.1", port=5000, debug=True)
