import http.client
import json

# 测试更新API配置
def test_update_api_config():
    conn = http.client.HTTPConnection("localhost", 16888)
    payload = json.dumps({
        "method": "update_api_config",
        "params": {
            "config": {
                "custom": {
                    "api_key": "test_api_key",
                    "model_name": "GML-5",
                    "endpoint": "https://bobdong.cn/"
                }
            }
        },
        "id": 1
    })
    headers = {
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/rpc", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(f"Status: {res.status} {res.reason}")
    print(f"Response: {data.decode('utf-8')}")

# 测试验证API配置
def test_validate_api_config():
    conn = http.client.HTTPConnection("localhost", 16888)
    payload = json.dumps({
        "method": "validate_api_config",
        "params": {
            "config": {
                "custom": {
                    "api_key": "test_api_key",
                    "model_name": "GML-5",
                    "endpoint": "https://bobdong.cn/"
                }
            }
        },
        "id": 1
    })
    headers = {
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/rpc", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(f"Status: {res.status} {res.reason}")
    print(f"Response: {data.decode('utf-8')}")

if __name__ == "__main__":
    print("Testing update_api_config...")
    test_update_api_config()
    print("\nTesting validate_api_config...")
    test_validate_api_config()
