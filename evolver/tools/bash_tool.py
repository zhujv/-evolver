"""BashTool - 命令执行工具"""

import os
import re
import subprocess
from .sandbox import DockerSandbox


class BashTool:
    """命令执行工具"""

    def __init__(self):
        self._sandbox = DockerSandbox()

    def execute(self, command: str, timeout: int = None, workdir: str = None) -> dict:
        """执行bash命令"""
        try:
            if not isinstance(command, str):
                return {"error": "命令必须是字符串"}
            command = command.strip()
            if not command:
                return {"error": "命令不能为空"}

            # 验证命令长度
            if len(command) > 1000:
                return {"error": "命令长度超过限制"}
            if '\n' in command or '\r' in command:
                return {"error": "命令不能包含换行"}
            
            # 验证命令是否包含危险字符
            dangerous_chars = [';', '&', '|', '`', '$(', '${', '<', '>', '>>', '<<']
            for char in dangerous_chars:
                if char in command:
                    return {"error": f"命令包含危险字符: {char}"}

            if workdir:
                safe_workdir = os.path.realpath(os.path.abspath(os.path.normpath(workdir)))
                current_dir = os.path.realpath(os.path.abspath(os.getcwd()))
                try:
                    if os.path.commonpath([safe_workdir, current_dir]) != current_dir:
                        return {"error": "工作目录不安全"}
                except ValueError:
                    return {"error": "工作目录不安全"}
                workdir = safe_workdir
            
            # 使用Docker沙箱执行命令
            exec_timeout = timeout if isinstance(timeout, int) and timeout > 0 else 30
            result = self._sandbox.execute(command, timeout=exec_timeout, workdir=workdir)
            
            # 限制输出长度
            if 'output' in result and isinstance(result['output'], str):
                max_output_length = 1000
                if len(result['output']) > max_output_length:
                    result['output'] = result['output'][:500] + '... [输出被截断] ...' + result['output'][-500:]
                    result['truncated'] = True
            
            return result
        except Exception as e:
            return {"error": str(e)}
