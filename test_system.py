import time
import json
import urllib.request

url = "http://127.0.0.1:16888/rpc"
headers = {"Content-Type": "application/json"}

def test_api(method, params, timeout=5):
    """测试单个API"""
    data = {"method": method, "params": params}
    json_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
        return True, result
    except Exception as e:
        return False, str(e)

print("=== 开始系统测试 ===")
print("=" * 60)

# 1. 健康检查
print("\n1. 健康检查")
success, result = test_api("health", {})
if success:
    print(f"   ✅ 成功: {result['result'].get('status', 'healthy')}")
    print(f"   📊 请求数: {result['result'].get('request_count', 0)}")
else:
    print(f"   ❌ 失败: {result}")

# 2. 创建会话
print("\n2. 创建会话")
success, result = test_api("create_session", {})
session_id = None
if success:
    session_id = result['result']
    print(f"   ✅ 成功: {session_id}")
else:
    print(f"   ❌ 失败: {result}")

# 3. 聊天测试
if session_id:
    print("\n3. 聊天测试")
    success, result = test_api("chat", {
        "session_id": session_id,
        "message": "Hello, how are you?",
        "agent_id": "code",
        "model": "GLM-5",
        "project_id": "default"
    }, timeout=30)
    if success:
        print(f"   ✅ 成功: 收到响应")
        if 'result' in result and 'final_response' in result['result']:
            response = result['result']['final_response'][:100] + "..." if len(result['result']['final_response']) > 100 else result['result']['final_response']
            print(f"   💬 响应: {response}")
    else:
        print(f"   ❌ 失败: {result}")

# 4. 项目列表
print("\n4. 项目列表")
success, result = test_api("list_projects", {})
if success:
    projects = result['result']
    print(f"   ✅ 成功: {len(projects)} 个项目")
    for proj in projects:
        print(f"     - {proj['name']} ({proj['project_id']})")
else:
    print(f"   ❌ 失败: {result}")

# 5. 技能列表
print("\n5. 技能列表")
success, result = test_api("get_skills", {})
if success:
    skills = result['result']
    print(f"   ✅ 成功: {len(skills)} 个技能")
    for skill in skills[:3]:  # 只显示前3个
        print(f"     - {skill['name']} ({skill['id']})")
    if len(skills) > 3:
        print(f"     ... 等{len(skills) - 3}个技能")
else:
    print(f"   ❌ 失败: {result}")

# 6. 自我进化
print("\n6. 自我进化")
success, result = test_api("self_evolve", {
    "goal": "优化系统",
    "signals": {"agent_id": "code", "model": "GLM-5"},
    "scope_id": "default"
}, timeout=30)
if success:
    print(f"   ✅ 成功: 生成优化建议")
    if 'result' in result and 'recommendations' in result['result']:
        recs = result['result']['recommendations']
        print(f"     生成了 {len(recs)} 个建议")
else:
    print(f"   ❌ 失败: {result}")

print("\n" + "=" * 60)
print("=== 测试完成 ===")
