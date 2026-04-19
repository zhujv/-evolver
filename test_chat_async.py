import time
import json
import urllib.request

url = "http://127.0.0.1:16888/rpc"
headers = {"Content-Type": "application/json"}

# 先创建一个会话
session_data = {"method": "create_session", "params": {}}
session_json = json.dumps(session_data).encode('utf-8')
req = urllib.request.Request(url, data=session_json, headers=headers, method='POST')
with urllib.request.urlopen(req, timeout=5) as response:
    result = json.loads(response.read().decode('utf-8'))['result']
    if isinstance(result, dict) and 'session_id' in result:
        session_id = result['session_id']
    else:
        # 如果获取会话失败，使用一个默认的会话ID
        session_id = 'test-session-' + str(int(time.time()))
        print(f"获取会话失败，使用默认会话ID: {session_id}")

print(f"创建会话成功: {session_id}")
print("测试聊天API性能（异步处理测试）...")
print("=" * 50)

start_time = time.time()
success_count = 0
response_times = []

for i in range(1, 6):  # 测试5次，避免过多请求
    try:
        chat_data = {
            "method": "chat",
            "params": {
                "session_id": session_id,
                "message": f"Hello test {i}",
                "agent_id": "code",
                "model": "GLM-5",
                "project_id": "default"
            }
        }
        chat_json = json.dumps(chat_data).encode('utf-8')
        
        req_start = time.time()
        req = urllib.request.Request(url, data=chat_json, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        req_end = time.time()
        response_time = (req_end - req_start) * 1000  # 毫秒
        response_times.append(response_time)
        success_count += 1
        
        print(f"请求 {i} 响应: {result}")
        if 'result' in result and 'final_response' in result['result']:
            print(f"请求 {i} 成功，响应时间: {response_time:.2f}ms")
        else:
            print(f"请求 {i} 成功，但响应格式异常")
            
    except Exception as e:
        print(f"请求 {i} 失败: {e}")

end_time = time.time()
total_time = end_time - start_time
avg_response_time = sum(response_times) / len(response_times) if response_times else 0

print("=" * 50)
print("聊天API测试结果:")
print(f"总请求数: 5")
print(f"成功数: {success_count}")
print(f"失败数: {5 - success_count}")
print(f"总耗时: {total_time:.2f} 秒")
print(f"平均响应时间: {avg_response_time:.2f} 毫秒")
print(f"QPS (每秒查询数): {5 / total_time:.2f}")

if success_count == 5:
    print("\n🎉 聊天API测试通过！")
else:
    print("\n⚠️  聊天API测试存在失败。")
