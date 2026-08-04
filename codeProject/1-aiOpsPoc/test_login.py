from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Splunk 配置
SPLUNK_HOST = "127.0.0.1"
SPLUNK_PORT = 8089

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "msg": "账号密码不能为空"}), 400

    try:
        # 转发认证请求到 Splunk 原生接口
        resp = requests.post(
            f"https://{SPLUNK_HOST}:{SPLUNK_PORT}/services/auth/login",
            data={
                "username": username,
                "password": password,
                "output_mode": "json"
            },
            verify=False  # 测试环境跳过证书校验，生产环境请关闭
        )

        if resp.status_code == 200:
            # 登录成功，可自行生成你的业务系统token
            return jsonify({
                "success": True,
                "msg": "登录成功",
                "splunk_session": resp.json().get("sessionKey")
            })
        else:
            return jsonify({"success": False, "msg": "账号或密码错误"}), 401

    except Exception as e:
        return jsonify({"success": False, "msg": f"连接Splunk失败: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)