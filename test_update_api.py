import urllib.request, json

data = json.dumps({
    'method': 'update_api_config',
    'params': {
        'config': {
            'custom': {
                'api_key': 'test-key-12345',
                'model_name': 'GML-5',
                'endpoint': 'https://bobdong.cn'
            }
        }
    }
}).encode()

req = urllib.request.Request('http://localhost:16888/rpc', data=data, headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:5173'})

resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
print('Update result:', result)

# 检查配置是否更新
data = json.dumps({'method': 'list_work_items', 'params': {}}).encode()
req = urllib.request.Request('http://localhost:16888/rpc', data=data, headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:5173'})
resp = urllib.request.urlopen(req, timeout=10)

# 读取配置文件
import os, json
config_path = os.path.expanduser('~/.evolver/config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
    print('Updated config:', json.dumps(config.get('api', {}), indent=2))
