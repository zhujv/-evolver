#!/usr/bin/env python3
"""简化的服务器启动脚本"""
import sys
import os

# 添加当前目录到路径
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

print('[run_server] Starting...')

# 尝试导入
try:
    print('[run_server] Importing runtime_env...')
    from evolver.runtime_env import effective_http_host, load_application_dotenv
    print('[run_server] runtime_env OK')
except Exception as e:
    print(f'[run_server] FAILED: {e}')
    sys.exit(1)

try:
    print('[run_server] Importing agent.manager...')
    from evolver.agent.manager import AgentManager, _exec_shell_enabled
    print('[run_server] agent.manager OK')
except Exception as e:
    print(f'[run_server] FAILED: {e}')
    sys.exit(1)

print('[run_server] All imports OK, starting server...')

# 启动服务器
if __name__ == '__main__':
    load_application_dotenv(ROOT)
    from evolver.server import AgentServer
    server = AgentServer()
    server.start_http()