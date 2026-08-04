from flask import Flask
app = Flask(__name__)

@app.route('/api/v1/<path:p>', methods=['GET','POST','PUT','DELETE'])
def echo(p):
    return {"mock": True, "path": f"/api/v1/{p}", "msg": "同事后端模拟响应"}

app.run(host="127.0.0.1", port=8001)