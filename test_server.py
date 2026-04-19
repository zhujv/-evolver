import http.client
import json

# 测试健康检查端点
try:
    conn = http.client.HTTPConnection('127.0.0.1', 16888, timeout=5)
    headers = {'Content-Type': 'application/json'}
    body = json.dumps({'method': 'health', 'id': 1})
    conn.request('POST', '/rpc', body, headers)
    response = conn.getresponse()
    print(f'Response status: {response.status}')
    print(f'Response data: {response.read().decode()}')
    conn.close()
except Exception as e:
    print(f'Error: {e}')

# 测试根路径
try:
    conn = http.client.HTTPConnection('127.0.0.1', 16888, timeout=5)
    conn.request('GET', '/')
    response = conn.getresponse()
    print(f'\nRoot path response status: {response.status}')
    print(f'Root path response data: {response.read().decode()}')
    conn.close()
except Exception as e:
    print(f'Error accessing root path: {e}')
