import sys
import os
from evolver.providers.router import ModelRouter

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 创建ModelRouter实例
router = ModelRouter()

# 测试消息
messages = [
    {"role": "user", "content": "Hello, how are you?"}
]

# 测试提示
prompt = "You are a helpful assistant."

# 调用chat方法
try:
    response = router.chat(messages, prompt)
    print("Response:", response)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
