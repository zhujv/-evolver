import urllib.request, json

# Test health check
data = json.dumps({'method': 'health', 'params': {}}).encode()
req = urllib.request.Request('http://localhost:16888/rpc', data=data, headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:5173'})
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
print('Health check:', result)

# Test list_work_items
data = json.dumps({'method': 'list_work_items', 'params': {}}).encode()
req = urllib.request.Request('http://localhost:16888/rpc', data=data, headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:5173'})
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
print('List work items:', result)

# Test create_session
data = json.dumps({'method': 'create_session', 'params': {}}).encode()
req = urllib.request.Request('http://localhost:16888/rpc', data=data, headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:5173'})
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
session_id = result['result']
print('Create session:', session_id)

# Test chat
data = json.dumps({'method': 'chat', 'params': {'session_id': session_id, 'message': '你好', 'model': 'GML-5'}}).encode()
req = urllib.request.Request('http://localhost:16888/rpc', data=data, headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:5173'})
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read().decode())
print('Chat response:', result)
