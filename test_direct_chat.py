import time
from evolver.agent.manager import AgentManager

# 直接创建AgentManager实例
manager = AgentManager()

# 创建一个会话
session_id = manager.create_session()
print(f"创建会话成功: {session_id}")

# 直接调用chat方法
print("测试直接调用chat方法...")
start_time = time.time()

for i in range(1, 3):  # 测试2次
    try:
        result = manager.chat(
            session_id=session_id,
            message=f"Hello test {i}",
            agent_id="code",
            model="GLM-5",
            project_id="default"
        )
        print(f"请求 {i} 结果: {result}")
        if 'final_response' in result:
            print(f"请求 {i} 成功，响应: {result['final_response']}")
        else:
            print(f"请求 {i} 成功，但响应格式异常")
    except Exception as e:
        print(f"请求 {i} 失败: {e}")
        import traceback
        traceback.print_exc()

end_time = time.time()
total_time = end_time - start_time
print(f"总耗时: {total_time:.2f} 秒")
