import http.client
import json

AUTH_TOKEN = "evolver-secure-token-2026"

def test_exec_shell():
    """测试执行系统命令"""
    conn = http.client.HTTPConnection("localhost", 16888)
    payload = json.dumps({
        "method": "exec_shell",
        "params": {
            "command": "echo Hello Evolver && dir"
        },
        "id": 1
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {AUTH_TOKEN}'
    }
    conn.request("POST", "/rpc", payload, headers)
    res = conn.getresponse()
    data = res.read()
    response = json.loads(data.decode('utf-8'))
    print(f"Status: {res.status}")
    if 'result' in response:
        result = response['result']
        print(f"Success: {result.get('ok')}")
        print(f"Return Code: {result.get('returncode')}")
        print(f"Output:\n{result.get('stdout', '')}")
        if result.get('stderr'):
            print(f"Errors:\n{result.get('stderr')}")
    else:
        print(f"Error: {response}")

if __name__ == "__main__":
    print("=== Testing Terminal/Shell Execution ===\n")
    test_exec_shell()
