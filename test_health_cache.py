import time
import json
import urllib.request

url = "http://127.0.0.1:16888/rpc"
headers = {"Content-Type": "application/json"}
data = {"method": "health", "params": {}}
json_data = json.dumps(data).encode('utf-8')

print("测试健康检查API性能（缓存测试）...")
print("=" * 50)

start_time = time.time()
success_count = 0
response_times = []

for i in range(1, 21):
    try:
        req_start = time.time()
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
        req_end = time.time()
        response_time = (req_end - req_start) * 1000  # 毫秒
        response_times.append(response_time)
        success_count += 1
        if i % 5 == 0:
            print(f"已完成 {i}/20 请求")
    except Exception as e:
        print(f"请求 {i} 失败: {e}")

end_time = time.time()
total_time = end_time - start_time
avg_response_time = sum(response_times) / len(response_times) if response_times else 0

print("=" * 50)
print("健康检查API测试结果:")
print(f"总请求数: 20")
print(f"成功数: {success_count}")
print(f"失败数: {20 - success_count}")
print(f"总耗时: {total_time:.2f} 秒")
print(f"平均响应时间: {avg_response_time:.2f} 毫秒")
print(f"QPS (每秒查询数): {20 / total_time:.2f}")

if success_count == 20:
    print("\n🎉 健康检查API测试通过！")
else:
    print("\n⚠️  健康检查API测试存在失败。")
