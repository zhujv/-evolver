import http.client
import json

def test_update_api_config():
    conn = http.client.HTTPConnection("localhost", 16888)
    payload = json.dumps({
        "method": "update_api_config",
        "params": {
            "config": {
                "custom": {
                    "api_key": "sk-WyPwSK2LDm1RVFBIcdC1w6Rf9jmwhEmYkN7SaYBelP9u9jS3",
                    "model_name": "GLM-5",
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
    return res.status == 200

def test_validate_api_config():
    conn = http.client.HTTPConnection("localhost", 16888)
    payload = json.dumps({
        "method": "validate_api_config",
        "params": {
            "config": {
                "custom": {
                    "api_key": "sk-WyPwSK2LDm1RVFBIcdC1w6Rf9jmwhEmYkN7SaYBelP9u9jS3",
                    "model_name": "GLM-5",
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
    return res.status == 200

if __name__ == "__main__":
    print("Testing update_api_config...")
    success1 = test_update_api_config()
    print("\nTesting validate_api_config...")
    success2 = test_validate_api_config()

    if success1 and success2:
        print("\n✓ API配置成功！")
    else:
        print("\n✗ API配置失败！")
