#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evolver — 浏览器一键启动

在仓库根目录执行:  python start.py

依次：后端 16888（已在跑则跳过）→ Vite 5173（已在跑则跳过）→ 打开浏览器。
依赖: .venv + pip install -r requirements.txt；frontend 下 npm install。
"""
from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import sys
import time
import webbrowser

try:
    import urllib.request
except ImportError:
    print("需要 urllib（标准库）", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from evolver.runtime_env import load_application_dotenv

load_application_dotenv(ROOT)

# 手动设置环境变量，确保API配置生效
os.environ["EVOLVER_API_BASE"] = "https://bobdong.cn"
os.environ["EVOLVER_API_KEY"] = "sk-WyPwSK2LDm1RVFBIcdC1w6Rf9jmwhEmYkN7SaYBelP9u9jS3"
os.environ["EVOLVER_MAIN_MODEL"] = "GLM-5"
os.environ["EVOLVER_PROXY_TYPE"] = "openai"
os.environ["EVOLVER_SERVER_TOKEN"] = "evolver-secure-token-2026"

FRONTEND = os.path.join(ROOT, "frontend")
BACKEND_URL = "http://127.0.0.1:16888"
FRONTEND_URL = "http://127.0.0.1:5173"
AUTH = os.environ.get("EVOLVER_SERVER_TOKEN", "evolver-secure-token-2026")

_server_proc: subprocess.Popen | None = None


def _venv_python() -> str:
    if sys.platform == "win32":
        p = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
    else:
        p = os.path.join(ROOT, ".venv", "bin", "python3")
    if os.path.isfile(p):
        return p
    for name in (".venv2", "venv", "env"):
        if sys.platform == "win32":
            p = os.path.join(ROOT, name, "Scripts", "python.exe")
        else:
            p = os.path.join(ROOT, name, "bin", "python3")
        if os.path.isfile(p):
            return p
    return sys.executable


def _rpc_health() -> bool:
    try:
        body = json.dumps({"method": "health", "params": {}, "id": 1}).encode("utf-8")
        req = urllib.request.Request(
            f"{BACKEND_URL}/rpc",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return '"result"' in raw or ('"error"' in raw and '"id"' in raw)
    except Exception:
        return False


def _http_ok(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status < 500
    except Exception:
        return False


def _start_server() -> subprocess.Popen | None:
    py = _venv_python()
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", ROOT)
    env.setdefault("EVOLVER_HTTP_HOST", "127.0.0.1")
    env.setdefault("EVOLVER_ALLOW_EXEC_SHELL", "1")
    env.setdefault("EVOLVER_SERVER_TOKEN", AUTH)
    env["EVOLVER_PYTHON_LOG"] = os.path.join(ROOT, "evolver-python.log")
    popen_kw: dict = {"cwd": ROOT, "env": env}
    if sys.platform == "win32":
        popen_kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        popen_kw["creationflags"] |= getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    try:
        proc = subprocess.Popen([py, "-m", "evolver.server"], **popen_kw)
        print(f"[*] 后端进程 PID: {proc.pid}")
        return proc
    except Exception as e:
        print(f"[错误] 无法启动后端: {e}", file=sys.stderr)
        return None


def _wait_backend(secs: int = 45) -> bool:
    deadline = time.time() + secs
    while time.time() < deadline:
        if _rpc_health():
            return True
        time.sleep(0.35)
    return False


def _start_vite() -> subprocess.Popen | None:
    from shutil import which

    env = os.environ.copy()
    kwargs: dict = {"cwd": FRONTEND, "env": env}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        try:
            return subprocess.Popen("npm run dev", shell=True, **kwargs)
        except Exception as e:
            print(f"[提示] shell 启动 Vite 失败，尝试 npm 全路径: {e}")
    npm = which("npm")
    if not npm:
        print("[提示] 未找到 npm，请手动: cd frontend && npm install && npm run dev", file=sys.stderr)
        return None
    try:
        return subprocess.Popen([npm, "run", "dev"], **kwargs)
    except Exception as e:
        print(f"[提示] 未能自动启动 Vite: {e}", file=sys.stderr)
        return None


def _cleanup():
    global _server_proc
    if _server_proc is None or _server_proc.poll() is not None:
        return
    try:
        _server_proc.terminate()
        _server_proc.wait(timeout=3)
    except Exception:
        try:
            _server_proc.kill()
        except Exception:
            pass


def _kill_existing_server() -> None:
    """强制关闭现有后端进程"""
    try:
        import subprocess
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if ':16888' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        print(f"[*] 已终止旧进程 {pid}")
                        time.sleep(1)
                    except Exception:
                        pass
    except Exception:
        pass

def main() -> int:
    global _server_proc

    print("Evolver — 浏览器启动")
    print("=" * 48)

    # 总是杀掉旧进程，确保加载新代码
    _kill_existing_server()
    time.sleep(1)
    
    print("[*] 正在启动后端 …")
    _server_proc = _start_server()
    
    if _wait_backend(secs=30):
        print("[*] 后端已就绪。")
    else:
        print("[*] 后端可能已在运行，继续…")

    # 启动前端 Vite 服务器
    print("[*] 正在启动前端 Vite 服务器 …")
    vite_proc = _start_vite()
    if vite_proc:
        print("[*] 前端 Vite 服务器已启动。")
    else:
        print("[*] 前端 Vite 服务器可能已在运行，继续…")

    def _sigint(_signum, _frame):
        _cleanup()
        if vite_proc and vite_proc.poll() is None:
            try:
                vite_proc.terminate()
                vite_proc.wait(timeout=3)
            except Exception:
                pass
        sys.exit(0)

    atexit.register(_cleanup)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _sigint)

    print(f"[*] 打开浏览器: http://localhost:5173/")
    webbrowser.open("http://localhost:5173/")
    print()
    print("Ctrl+C 退出本脚本时会尝试结束由本脚本启动的后端/Vite。")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[*] 退出…")
        _cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
