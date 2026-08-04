@echo off
chcp 65001 >nul
echo ========================================
echo  AIOps Splunk PoC — 服务重启脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 启动 MCP 服务器...
start "mcp-system" /B .venv\Scripts\python.exe mcp_servers\system_server.py
start "mcp-websearch" /B .venv\Scripts\python.exe mcp_servers\websearch_server.py
start "mcp-winlog" /B .venv\Scripts\python.exe mcp_servers\winlog_server.py
start "mcp-network" /B .venv\Scripts\python.exe mcp_servers\network_server.py
start "mcp-docker" /B .venv\Scripts\python.exe mcp_servers\docker_server.py

echo [2/3] 等待 MCP 就绪 (6s)...
timeout /t 6 /nobreak >nul

echo [3/3] 启动 FastAPI 主服务 (端口 9900)...
start "fastapi-aiops" /B .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 9900

timeout /t 6 /nobreak >nul

echo.
echo ========================================
echo  服务已启动
echo  Web UI:    http://localhost:9900
echo  Splunk:    http://localhost:8001
echo  Dashboard: http://localhost:8001/en-US/app/search/aiops_overview
echo ========================================
echo.
echo 运行模拟器: .venv\Scripts\python.exe splunk\alert_simulator.py --count 3
echo.
pause
