"""Server smoke test for Evolver JSON-RPC."""

import json
import os
import subprocess
import sys
import time
import urllib.request


def rpc_call(payload: dict, token: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        "http://127.0.0.1:16888/rpc",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def wait_server_ready(timeout_s: int = 15) -> bool:
    started = time.time()
    while time.time() - started < timeout_s:
        try:
            result = rpc_call({"method": "health", "params": {}, "id": 1})
            if "result" in result:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    missing = []
    for dep in ("psutil", "msgpack", "httpx"):
        try:
            __import__(dep)
        except Exception:
            missing.append(dep)
    if missing:
        print(f"[SKIP] missing dependencies: {', '.join(missing)}")
        print("Install dependencies first, e.g. pip install -e .")
        return 2

    token = os.environ.get("EVOLVER_SERVER_TOKEN", "").strip()
    restart_token = os.environ.get("EVOLVER_RESTART_TOKEN", "").strip() or "smoke-restart-token"

    env = os.environ.copy()
    if not token:
        token = "smoke-server-token"
        env["EVOLVER_SERVER_TOKEN"] = token
    if "EVOLVER_RESTART_TOKEN" not in env:
        env["EVOLVER_RESTART_TOKEN"] = restart_token

    proc = subprocess.Popen([sys.executable, "-m", "evolver.server"], env=env)
    try:
        if not wait_server_ready():
            print("[FAIL] server not ready")
            return 1

        health = rpc_call({"method": "health", "params": {}, "id": 2})
        print("[OK] health:", "result" in health)

        session = rpc_call({"method": "create_session", "params": {}, "id": 3}, token=token)
        if "result" not in session:
            print("[FAIL] create_session:", session)
            return 1
        session_id = session["result"]
        print("[OK] create_session:", session_id)

        chat = rpc_call(
            {"method": "chat", "params": {"session_id": session_id, "message": "你好"}, "id": 4},
            token=token,
        )
        print("[OK] chat:", "result" in chat)
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
