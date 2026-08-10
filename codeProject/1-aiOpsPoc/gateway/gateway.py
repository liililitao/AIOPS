#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 认证网关 — Splunk 认证 + 静态文件托管 + 后端 API 代理
===========================================================
用途: 复用 Splunk 用户认证，为同事的 AIOps 前端页面提供认证壳，
     同时代理 /api/v1/* 请求到同事的后端服务。

部署: 见 gateway_deploy.md，或直接 python gateway.py 启动
"""

import json
import os
import tempfile
import time
import uuid
from urllib.parse import quote

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

from handoff_auth import (
    HandoffVerificationError,
    SQLiteNonceStore,
    verify_handoff,
)
from authorization import AuthorizationStore, default_database_path


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_secret_value(value_name, file_name):
    value = os.environ.get(value_name, "").strip()
    secret_file = os.environ.get(file_name, "").strip()
    if not value and secret_file:
        with open(secret_file, "r", encoding="utf-8") as secret_handle:
            value = secret_handle.read().strip()
    return value


def _env_csv(name):
    return {
        item.strip()
        for item in os.environ.get(name, "").split(",")
        if item.strip()
    }

# ==================== 配置 (环境变量) ====================
SPLUNK_HOST = os.environ.get("SPLUNK_HOST", "127.0.0.1")
SPLUNK_PORT = os.environ.get("SPLUNK_PORT", "8089")          # Splunk 管理端口
SPLUNK_WEB_URL = os.environ.get("SPLUNK_WEB_URL",
                                "http://127.0.0.1:8000")     # Splunk Web 登录页 (认证失败时跳转)

BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8001")        # 同事后端服务端口

JWT_SECRET = _load_secret_value("JWT_SECRET", "JWT_SECRET_FILE")
JWT_EXP_HOURS = int(os.environ.get("JWT_EXP_HOURS", "8"))    # JWT 有效期，对齐 Splunk session 超时

AIOPS_HANDOFF_SECRET = _load_secret_value(
    "AIOPS_HANDOFF_SECRET", "AIOPS_HANDOFF_SECRET_FILE"
)
AIOPS_HANDOFF_MAX_TTL_SECONDS = int(
    os.environ.get("AIOPS_HANDOFF_MAX_TTL_SECONDS", "120")
)
AIOPS_HANDOFF_CLOCK_SKEW_SECONDS = int(
    os.environ.get("AIOPS_HANDOFF_CLOCK_SKEW_SECONDS", "5")
)
AIOPS_HANDOFF_NONCE_DB = os.environ.get(
    "AIOPS_HANDOFF_NONCE_DB",
    os.path.join(tempfile.gettempdir(), "aiops_handoff_nonces.sqlite3"),
)
AUTH_COOKIE_SECURE = _env_bool("AUTH_COOKIE_SECURE", default=False)
FLASK_DEBUG = _env_bool("FLASK_DEBUG", default=False)
ALLOW_LEGACY_SPLUNK_USER = _env_bool("ALLOW_LEGACY_SPLUNK_USER", default=False)
ALLOW_SPLUNK_TOKEN_QUERY = _env_bool("ALLOW_SPLUNK_TOKEN_QUERY", default=False)
AIOPS_ALLOWED_ROLES = _env_csv("AIOPS_ALLOWED_ROLES")
AIOPS_AUTHZ_DB = os.environ.get("AIOPS_AUTHZ_DB", default_database_path())

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
# ==========================================================

app = Flask(__name__)
HANDOFF_NONCE_STORE = SQLiteNonceStore(AIOPS_HANDOFF_NONCE_DB)
AUTHORIZATION_STORE = None

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

def _auth_redirect(username, roles, clean_url="/app/"):
    """Create the internal session and remove handoff credentials from the URL."""
    if len(JWT_SECRET.encode("utf-8")) < 32:
        response = jsonify({
            "success": False,
            "msg": "安全登录服务暂不可用，请联系管理员",
            "code": "jwt_configuration",
        })
        response.status_code = 503
        return response
    jwt_token = create_jwt(username, list(roles))
    response = redirect(clean_url)
    response.set_cookie(
        "auth_token",
        jwt_token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="Lax",
        max_age=JWT_EXP_HOURS * 3600,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def _handoff_error(error):
    if error.code in {"configuration", "nonce_store"}:
        status = 503
        message = "安全登录服务暂不可用，请联系管理员"
    elif error.code == "expired":
        status = 401
        message = "安全链接已失效，请返回 Splunk 重新进入"
    elif error.code == "replay":
        status = 401
        message = "安全链接已使用，请返回 Splunk 重新进入"
    else:
        status = 401
        message = "安全链接校验失败"
    print(f"[!] HMAC handoff rejected: {error.code}: {error}")
    response = jsonify({"success": False, "msg": message, "code": error.code})
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response


def _roles_allowed(roles):
    """An empty allow-list permits every authenticated Splunk role."""
    return not AIOPS_ALLOWED_ROLES or bool(AIOPS_ALLOWED_ROLES.intersection(roles))


def get_authorization_store():
    """Initialize the local authorization database only when an API uses it."""
    global AUTHORIZATION_STORE
    if AUTHORIZATION_STORE is None:
        AUTHORIZATION_STORE = AuthorizationStore(AIOPS_AUTHZ_DB)
    return AUTHORIZATION_STORE

@app.before_request
def check_auth():
    """
    所有请求前置认证:
    1. 跳过健康检查和静态资源(首次访问可能无 cookie)
    2. 验证 Splunk 服务端生成的 HMAC 签名链接并种 JWT cookie
    3. 检查 JWT cookie → 已认证用户放行
    4. 都不满足 → 302 跳转到 Splunk 登录页
    """
    path = request.path

    # 跳过健康检查
    if path == "/health":
        return

    # ---- 方式 1: Splunk 服务端签发的短时 HMAC URL ----
    signed_keys = {"v", "user", "exp", "nonce", "sig"}
    if path in {"/app", "/app/"} and signed_keys.intersection(request.args):
        missing = [key for key in signed_keys if not request.args.get(key)]
        if missing:
            return jsonify({
                "success": False,
                "msg": "安全链接参数不完整",
                "code": "missing",
            }), 400
        if not AIOPS_HANDOFF_SECRET:
            return _handoff_error(HandoffVerificationError(
                "configuration", "AIOPS_HANDOFF_SECRET is not configured"
            ))

        try:
            verified = verify_handoff(
                secret=AIOPS_HANDOFF_SECRET,
                version=request.args.get("v", ""),
                user=request.args.get("user", ""),
                exp=request.args.get("exp", ""),
                nonce=request.args.get("nonce", ""),
                signature=request.args.get("sig", ""),
                roles=request.args.get("roles", ""),
                now=int(time.time()),
                max_ttl_seconds=AIOPS_HANDOFF_MAX_TTL_SECONDS,
                clock_skew_seconds=AIOPS_HANDOFF_CLOCK_SKEW_SECONDS,
                nonce_store=HANDOFF_NONCE_STORE,
            )
        except HandoffVerificationError as error:
            return _handoff_error(error)

        print(
            f"[+] Splunk HMAC authentication succeeded: {verified.user} "
            f"(roles={','.join(verified.roles) or '-'})"
        )
        if not _roles_allowed(verified.roles):
            return jsonify({
                "success": False,
                "msg": "当前 Splunk 用户没有访问 AIOps 的权限",
                "code": "forbidden_role",
            }), 403
        return _auth_redirect(verified.user, verified.roles)

    # 旧版用户名参数默认禁用，仅用于短期回滚。
    user_param = request.args.get("splunk_user")
    if user_param:
        if not ALLOW_LEGACY_SPLUNK_USER:
            return jsonify({
                "success": False,
                "msg": "旧版用户名登录已禁用，请从新版 Splunk Dashboard 进入",
                "code": "legacy_disabled",
            }), 401
        print(f"[!] 使用旧版不安全登录参数: {user_param}")
        return _auth_redirect(user_param, [])

    # ---- 方式 2: URL 中携带 splunk_token (仅兼容测试，默认禁用) ----
    query_token = request.args.get("splunk_token")
    if query_token:
        if not ALLOW_SPLUNK_TOKEN_QUERY:
            return jsonify({
                "success": False,
                "msg": "URL token 登录已禁用",
                "code": "token_query_disabled",
            }), 401
        user_info = validate_splunk_token(query_token)
        if user_info:
            print(f"[+] Splunk token 认证成功: {user_info['username']}")
            return _auth_redirect(user_info["username"], user_info["roles"])
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
            if not _roles_allowed(g.current_roles):
                return jsonify({
                    "success": False,
                    "msg": "当前用户没有访问 AIOps 的权限",
                    "code": "forbidden_role",
                }), 403
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


def _backend_url(path):
    target_url = f"{BACKEND_BASE}/api/v1/{path}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"
    return target_url


def _backend_headers():
    blocked_headers = {
        "host",
        "connection",
        "transfer-encoding",
        "x-aiops-authenticated-user",
        "x-aiops-authenticated-roles",
    }
    headers = {
        key: value
        for key, value in request.headers
        if key.lower() not in blocked_headers
    }
    headers["X-AIOPS-Authenticated-User"] = g.current_user
    headers["X-AIOPS-Authenticated-Roles"] = ",".join(g.current_roles)
    return headers


def _proxy_headers(response, rewriting_body=False):
    excluded_headers = {"connection", "transfer-encoding", "content-encoding"}
    if rewriting_body:
        excluded_headers.update({"content-length", "content-type"})
    return [
        (key, value)
        for key, value in response.raw.headers.items()
        if key.lower() not in excluded_headers
    ]


def _upstream_response(response):
    return response.content, response.status_code, _proxy_headers(response)


def _task_not_visible_response():
    return jsonify({
        "success": False,
        "msg": "告警不存在或当前用户无权访问",
        "code": "alert_not_found",
    }), 404


def _task_check_unavailable_response():
    return jsonify({
        "success": False,
        "msg": "告警权限校验服务暂不可用，请稍后重试",
        "code": "authorization_unavailable",
    }), 502


def _task_id_from_path(path):
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[:2] != ["incidents", "tasks"]:
        return None
    if parts[2] == "bulk-delete":
        return None
    return parts[2]


def _load_authorized_task(task_id, headers, authorization_store):
    target_url = f"{BACKEND_BASE}/api/v1/incidents/tasks/{quote(task_id, safe='')}"
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
    except (requests.ConnectionError, requests.Timeout, requests.RequestException):
        return None, _task_check_unavailable_response()

    if response.status_code == 404:
        return None, _task_not_visible_response()
    if response.status_code != 200:
        return None, _upstream_response(response)
    try:
        task = response.json()
    except ValueError:
        return None, _task_check_unavailable_response()
    if not isinstance(task, dict) or not authorization_store.can_access_task(
        g.current_user, task
    ):
        return None, _task_not_visible_response()
    return response, None


def _filter_task_list(response, authorization_store):
    if response.status_code != 200:
        return _upstream_response(response)
    try:
        body = response.json()
    except ValueError:
        return _upstream_response(response)
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        return _upstream_response(response)

    body["items"] = [
        task
        for task in body["items"]
        if isinstance(task, dict)
        and authorization_store.can_access_task(g.current_user, task)
    ]
    body["count"] = len(body["items"])
    filtered_response = app.response_class(
        response=json.dumps(body, ensure_ascii=False),
        status=response.status_code,
        mimetype="application/json",
    )
    filtered_response.headers.extend(_proxy_headers(response, rewriting_body=True))
    return filtered_response


def _authorize_bulk_delete(headers, authorization_store):
    payload = request.get_json(silent=True)
    task_ids = payload.get("task_ids") if isinstance(payload, dict) else None
    if not isinstance(task_ids, list):
        return None
    for task_id in task_ids:
        if not isinstance(task_id, str) or not task_id:
            return _task_not_visible_response()
        _, rejection = _load_authorized_task(task_id, headers, authorization_store)
        if rejection is not None:
            return rejection
    return None


@app.route("/api/v1/", defaults={"path": ""}, methods=PROXY_METHODS)
@app.route("/api/v1/<path:path>", methods=PROXY_METHODS)
def proxy_api(path):
    """反向代理 /api/v1/* 到同事的后端服务"""
    target_url = _backend_url(path)
    headers = _backend_headers()
    authorization_store = get_authorization_store()

    task_id = _task_id_from_path(path)
    if task_id:
        checked_response, rejection = _load_authorized_task(
            task_id, headers, authorization_store
        )
        if rejection is not None:
            return rejection
        if request.method == "GET" and path.strip("/") == f"incidents/tasks/{task_id}":
            return _upstream_response(checked_response)

    if path.strip("/") == "incidents/tasks/bulk-delete" and request.method == "POST":
        rejection = _authorize_bulk_delete(headers, authorization_store)
        if rejection is not None:
            return rejection

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            stream=True,
            timeout=30,
        )
    except requests.ConnectionError:
        return jsonify({"success": False, "msg": "后端服务不可达"}), 502
    except requests.Timeout:
        return jsonify({"success": False, "msg": "后端服务响应超时"}), 504

    if path.strip("/") == "incidents/tasks" and request.method == "GET":
        return _filter_task_list(resp, authorization_store)
    return _upstream_response(resp)


# ==================== 路由: 健康检查 ====================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Flask Auth Gateway",
        "splunk_host": SPLUNK_HOST,
        "backend": f"{BACKEND_HOST}:{BACKEND_PORT}",
        "hmac_handoff": "configured" if AIOPS_HANDOFF_SECRET else "missing_secret",
        "jwt_signing": (
            "configured" if len(JWT_SECRET.encode("utf-8")) >= 32
            else "missing_secret"
        ),
        "role_filter": sorted(AIOPS_ALLOWED_ROLES),
        "alert_authorization": "sqlite",
    })


# ==================== 启动 ====================

if __name__ == "__main__":
    print("=" * 55)
    print("  Flask 认证网关")
    print(f"  Splunk 认证:    {SPLUNK_HOST}:{SPLUNK_PORT}")
    print(f"  后端服务:       {BACKEND_HOST}:{BACKEND_PORT}")
    print(f"  Splunk Web:     {SPLUNK_WEB_URL}")
    print(f"  JWT 有效期:     {JWT_EXP_HOURS} 小时")
    print(f"  JWT 签名密钥:   {'已配置' if len(JWT_SECRET.encode('utf-8')) >= 32 else '未配置'}")
    print(f"  HMAC 交接认证:  {'已配置' if AIOPS_HANDOFF_SECRET else '未配置'}")
    print(f"  允许角色:       {','.join(sorted(AIOPS_ALLOWED_ROLES)) or '全部已认证用户'}")
    print(f"  Nonce 数据库:   {AIOPS_HANDOFF_NONCE_DB}")
    print(f"  告警权限库:     {AIOPS_AUTHZ_DB}")
    print(f"  静态文件目录:   {FRONTEND_DIR}")
    print("=" * 55)
    app.run(host="127.0.0.1", port=5000, debug=FLASK_DEBUG)
