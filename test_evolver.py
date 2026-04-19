"""测试Evolver项目"""

import os
import subprocess
import time
import json
import urllib.request
import urllib.error

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def test_server_start():
    """测试服务器启动"""
    print("测试服务器启动...")
    server_process = subprocess.Popen([
        "python", "-m", "evolver.server"
    ], cwd=_PROJECT_ROOT)
    
    # 等待服务器启动
    time.sleep(3)
    
    # 检查服务器是否运行
    try:
        json_data = {"method": "health", "params": {}, "id": 1}
        payload = json.dumps(json_data).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:16888/rpc",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")

        if body:
            print("服务器启动成功！")
            print(f"响应: {body}")
        else:
            print("服务器启动失败: 空响应")
    except Exception as e:
        print(f"服务器启动失败: {e}")
    finally:
        # 停止服务器
        server_process.terminate()
        server_process.wait()


def test_cli_start():
    """测试CLI启动"""
    print("\n测试CLI启动...")
    try:
        cli_process = subprocess.Popen([
            "python", "-m", "evolver.ui.cli"
        ], cwd=_PROJECT_ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 等待CLI启动
        time.sleep(1)
        
        # 发送exit命令
        cli_process.stdin.write("exit\n")
        cli_process.stdin.flush()
        
        # 读取输出
        output, error = cli_process.communicate(timeout=5)
        if "欢迎使用Evolver CLI" in output:
            print("CLI启动成功！")
        else:
            print(f"CLI启动失败: {error}")
    except Exception as e:
        print(f"CLI启动失败: {e}")


def test_agent_manager():
    """测试AgentManager"""
    print("\n测试AgentManager...")
    from evolver.agent.manager import AgentManager
    
    manager = AgentManager()
    session_id = manager.create_session()
    print(f"创建会话成功，会话ID: {session_id}")
    
    # 测试聊天
    result = manager.chat(session_id, "你好，我是测试用户")
    print(f"聊天测试结果: {result.get('final_response', '无响应')}")
    
    # 测试技能列表
    skills = manager.list_skills()
    print(f"技能列表: {skills}")


def test_memory_store():
    """测试记忆存储"""
    print("\n测试记忆存储...")
    from evolver.memory.sqlite_store import SQLiteMemoryStore
    
    store = SQLiteMemoryStore()
    store.add_memory("测试记忆", {"test": "value"})
    print("添加记忆成功")
    
    results = store.recall("测试")
    print(f"检索记忆结果: {results}")


def test_privacy_filter():
    """测试隐私过滤器"""
    print("\n测试隐私过滤器...")
    from evolver.memory.privacy_filter import PrivacyFilter
    
    filter = PrivacyFilter()
    test_text = "我的API密钥是 sk-1234567890abcdef，密码是 password123"
    sanitized = filter.sanitize(test_text)
    print(f"原始文本: {test_text}")
    print(f"过滤后: {sanitized}")


def test_tool_registry():
    """测试工具注册器"""
    print("\n测试工具注册器...")
    from evolver.tools.registry import ToolRegistry
    
    registry = ToolRegistry()
    # 测试读取文件
    result = registry.execute_tool("read_file", {"path": "README.md"})
    print(f"读取文件测试: {'成功' if 'content' in result else '失败'}")


def main():
    """主测试函数"""
    print("Evolver项目测试")
    print("=" * 50)
    
    test_agent_manager()
    test_memory_store()
    test_privacy_filter()
    test_tool_registry()
    test_server_start()
    test_cli_start()
    
    print("=" * 50)
    print("测试完成！")


if __name__ == "__main__":
    main()
