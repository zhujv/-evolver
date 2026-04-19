import sys
import json
import os
import urllib.request
import urllib.error

def send_request(method, params=None):
    base_url = "http://localhost:16888"
    auth_token = "evolver-secure-token-2026"
    
    try:
        request_params = dict(params or {})
        if auth_token and method != "health":
            request_params["auth_token"] = auth_token

        json_data = {"method": method, "params": request_params, "id": 1}
        payload = json.dumps(json_data).encode("utf-8")
        req = urllib.request.Request(
            url=f"{base_url}/rpc",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)
    except Exception as e:
        return {"error": {"message": str(e)}}

# 创建会话
result = send_request("create_session", {})
print("创建会话:", result)

if "result" in result:
    session_id = result["result"]
    
    # 聊天
    result = send_request("chat", {
        "session_id": session_id,
        "message": "你好",
        "agent_id": "default",
    })
    print("聊天:", result)