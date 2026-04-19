#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""可选：终端里连 HTTP 后端聊天（非网页）。请先自行启动 evolver.server，再运行:
  python scripts/http_chat_demo.py
"""
import json
import os
import sys

if sys.platform == "win32":
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BASE_URL = "http://localhost:16888"
AUTH_TOKEN = os.environ.get("EVOLVER_SERVER_TOKEN", "evolver-secure-token-2026")


def send_request(method, params=None):
    import urllib.request

    try:
        request_params = dict(params or {})
        if AUTH_TOKEN and method != "health":
            request_params["auth_token"] = AUTH_TOKEN
        json_data = {"method": method, "params": request_params, "id": 1}
        payload = json.dumps(json_data).encode("utf-8")
        req = urllib.request.Request(
            url=f"{BASE_URL}/rpc",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": {"message": str(e)}}


def main() -> None:
    session_id = None
    agent_id = "default"

    print("=" * 50)
    print("  Evolver 终端对话（需已启动后端）")
    print("  输入 q 退出")
    print("=" * 50 + "\n")

    result = send_request("health", {})
    if "result" not in result:
        print("[错误] 无法连接后端，请先: cd 仓库根 && .venv\\Scripts\\python.exe -m evolver.server")
        input("\n按回车退出...")
        sys.exit(1)

    print("[*] 连接成功\n")

    while True:
        try:
            message = input("> ").strip()
            if not message:
                continue
            if message.lower() == "q":
                print("\n[*] 再见!\n")
                break

            if not session_id:
                result = send_request("create_session", {})
                if "result" in result:
                    session_id = result["result"]
                    print("[*] 会话已创建\n")

            print("[*] 等待回复...")
            result = send_request(
                "chat",
                {
                    "session_id": session_id,
                    "message": message,
                    "agent_id": agent_id,
                },
            )

            if "result" in result:
                response = result["result"].get("final_response", "")
                print(f"[{agent_id}] {response}\n")
            else:
                print(f"[错误] {result.get('error', {}).get('message')}\n")

        except KeyboardInterrupt:
            print("\n\n[*] 再见!\n")
            break
        except Exception as e:
            print(f"[错误] {e}\n")


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
