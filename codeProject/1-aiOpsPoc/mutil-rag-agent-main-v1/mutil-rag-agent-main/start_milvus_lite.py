#!/usr/bin/env python3
"""启动 milvus-lite + 注入端口到环境变量，然后启动 FastAPI 后端"""
import os, sys, time

# 1. 启动 milvus-lite
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from milvus_lite import server_manager_instance

server_manager_instance.release_all()
uri = server_manager_instance.start_and_get_uri('./milvus_data')
port = uri.split(':')[-1]
print(f"[milvus-lite] started at {uri} (port={port})")

# 2. 设置环境变量（覆盖 .env 中的 MILVUS_PORT）
os.environ['MILVUS_PORT'] = port
os.environ['MILVUS_HOST'] = '127.0.0.1'

print(f"[gateway] Starting FastAPI on port 9900...")
print(f"[gateway] MILVUS_HOST=127.0.0.1 MILVUS_PORT={port}")

# 3. 启动 FastAPI
import uvicorn
uvicorn.run("app.main:app", host="0.0.0.0", port=9900, reload=False)
