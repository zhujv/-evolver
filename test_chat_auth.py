import http.client
import json

def test_chat():
    conn = http.client.HTTPConnection("localhost", 16888)
    payload = json.dumps({
        "method": "chat",
        "params": {
            "session_id": "test-session-123",
            "message": "你好",
            "agent_id": "default",
            "model": "glm-4",
            "project_id": "default",
            "auth_token": "evolver-secure-token-2026"
        },
        "id": 1
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer evolver-secure-token-2026'
    }
    conn.request("POST", "/rpc", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(f"Status: {res.status} {res.reason}")
    print(f"Response: {data.decode('utf-8')}")

if __name__ == "__main__":
    print("Testing chat with auth token...")
    test_chat()
