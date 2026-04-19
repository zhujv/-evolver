"""AIAgent - AI代理核心类"""

import logging
from typing import List, Dict, Optional
import os
from ..providers.router import ModelRouter

logger = logging.getLogger(__name__)
from ..tools.registry import ToolRegistry

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover
    psutil = None


class ChatResult:
    def __init__(self, final_response: str, messages: List[Dict], iterations: int = 0):
        self.final_response = final_response
        self.messages = messages
        self.iterations = iterations


class AIAgent:
    def __init__(self, model: str):
        self.model = model
        self.messages: List[Dict] = []
        self.context: Dict = {}
        self.iteration_count: int = 0
        self.max_iterations = 5
        self.max_same_file_operations = 3
        self.max_same_command_executions = 2
        self.operation_history = []
        self.running_processes = []
        self._interrupted = False
        self._model_router = ModelRouter()
        self._tool_registry = ToolRegistry()
        self.max_context_size = 10
        self.token_usage = 0
        # 内存使用限制
        self.max_memory_usage = 512  # 最大内存使用限制（MB）
        self.current_memory_usage = 0  # 当前内存使用情况（MB）

    def run_conversation(self, message: str, context: Dict = None, skills: List = None) -> Dict:
        # 每次对话前重载 API 配置，避免 UI 已保存但会话内仍用旧 ModelRouter（原先最多等 60s 才 reload）
        self._model_router.reload_config()
        # 检查内存使用情况
        if not self._check_memory_usage():
            return {"final_response": "内存使用超过限制，已清理部分数据，请重试", "messages": self.messages, "token_usage": self.token_usage}
        
        self.messages.append({"role": "user", "content": message})
        self.compress_context()
        
        logger.info(f"开始处理对话，消息: {message}")
        logger.info(f"上下文: {context}")
        logger.info(f"技能: {skills}")

        common_responses = {
            "你好": "你好！我是Evolver，你的AI编程助手。有什么我可以帮助你的吗？",
            "帮助": "我可以帮助你编写代码、调试程序、解答技术问题等。你可以直接问我具体的问题。",
            "再见": "再见！如果你有任何问题，随时可以回来找我。",
        }
        
        if message.strip() in common_responses:
            logger.info(
                "使用内置快捷回复（未调用模型）: %r",
                message.strip()[:32],
            )
            return {"final_response": common_responses[message.strip()], "messages": self.messages, "iterations": 0, "token_usage": self.token_usage}

        while self.iteration_count < self.max_iterations:
            # 检查内存使用情况
            if not self._check_memory_usage():
                return {"final_response": "内存使用超过限制，已清理部分数据，请重试", "messages": self.messages, "token_usage": self.token_usage}
            
            if self._interrupted:
                return {"final_response": "操作已被用户中断", "messages": self.messages, "token_usage": self.token_usage}
            
            duplicate_check = self._check_duplicate_operations()
            if duplicate_check:
                return {"final_response": f"检测到重复操作：{duplicate_check}，已自动终止", "messages": self.messages, "token_usage": self.token_usage}
            
            try:
                response = self._call_llm(context, skills)
            except Exception as e:
                # 处理模型调用错误
                error_message = f"模型调用失败：{str(e)}"
                return {
                    "final_response": error_message,
                    "messages": self.messages,
                    "iterations": self.iteration_count,
                    "token_usage": self.token_usage
                }

            if response.get("tool_calls"):
                tool_results = []
                user_permission = self.context.get('user_permission', 'read')
                for tool_call in response.get("tool_calls", []):
                    try:
                        self.operation_history.append(tool_call)
                        result = self._execute_tool(tool_call, user_permission)
                        tool_results.append(result)
                        if result.get("error"):
                            error_message = f"工具执行失败：{result.get('error')}"
                            self.messages.append({"role": "assistant", "tool_result": result})
                            return {"final_response": error_message, "messages": self.messages, "iterations": self.iteration_count, "token_usage": self.token_usage}
                    except Exception as e:
                        # 处理工具执行错误
                        error_message = f"工具执行异常：{str(e)}"
                        return {
                            "final_response": error_message,
                            "messages": self.messages,
                            "iterations": self.iteration_count,
                            "token_usage": self.token_usage
                        }
                
                for result in tool_results:
                    self.messages.append({"role": "assistant", "tool_result": result})
            else:
                return {
                    "final_response": response.get("content", ""),
                    "messages": self.messages,
                    "iterations": self.iteration_count,
                    "token_usage": self.token_usage,
                    "last_token_usage": response.get("token_usage", {})
                }

            self.iteration_count += 1

        return {"final_response": f"已达到最大迭代次数({self.max_iterations})", "messages": self.messages, "token_usage": self.token_usage}

    def _check_duplicate_operations(self) -> Optional[str]:
        file_operations = {}
        for op in self.operation_history:
            file = op.get("parameters", {}).get("path", "unknown")
            file_operations[file] = file_operations.get(file, 0) + 1
            if file_operations[file] >= self.max_same_file_operations:
                return f"文件 {file} 操作次数过多"
        
        command_executions = {}
        for op in self.operation_history:
            cmd = op.get("name", "unknown")
            command_executions[cmd] = command_executions.get(cmd, 0) + 1
            if command_executions[cmd] >= self.max_same_command_executions:
                return f"命令 {cmd} 执行次数过多"
        
        return None

    def interrupt(self, message: str = None):
        self._interrupted = True
        for proc in self.running_processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        self.running_processes = []

    def _call_llm(self, context: Dict, skills: List) -> Dict:
        prompt = self._build_prompt(context, skills)
        
        user_message = None
        for msg in reversed(self.messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        tools = self._tool_registry.get_tool_definitions(relevant_only=True, query=user_message)
        
        if self.model:
            self._model_router.main_model = self.model
        response = self._model_router.chat(self.messages, prompt, tools=tools)
        logger.info(
            "模型调用返回: has_tool_calls=%s content_len=%s",
            bool(response.get("tool_calls")),
            len((response.get("content") or "") or ""),
        )
        
        token_usage = response.get('token_usage')
        if token_usage:
            self.token_usage += token_usage.get('total_tokens', 0)
        
        return response

    def _build_prompt(self, context: Dict, skills: List) -> str:
        prompt = "你是一个可进化的AI编程助手，能主动完成复杂任务。"
        active_focus = ""
        
        if context and isinstance(context, dict):
            context_info = []
            if context.get('active_agent'):
                active_agent = context['active_agent']
                active_focus = active_agent.get('focus', '')
                context_info.append(
                    f"当前智能体: {active_agent.get('name')} | 侧重点: {active_agent.get('focus')} | 指导: {active_agent.get('system_hint')}"
                )
            if context.get('relevant_skills'):
                context_info.append(f"相关技能: {context['relevant_skills']}")
            if context.get('recent_memories'):
                context_info.append(f"最近记忆: {context['recent_memories']}")
            if context_info:
                prompt += "\n\n" + " | ".join(context_info)
        
        if skills and isinstance(skills, list):
            limited_skills = skills[:3]
            skills_str = " | ".join([skill.get('name', '未知') for skill in limited_skills])
            prompt += f"\n\n可用技能：{skills_str}"

        if active_focus == "office_productivity":
            prompt += (
                "\n\n办公输出规范："
                "\n1) 结果优先：先给可直接使用的成品内容（邮件正文/纪要/计划表）。"
                "\n2) 结构化输出：优先使用固定字段，如【结论】【行动项】【负责人】【截止时间】【风险】。"
                "\n3) 低打扰确认：仅在高风险动作时请求确认（如批量写入、外发、执行命令）。"
                "\n4) 闭环交付：末尾补充“下一步建议”与“待确认事项（如有）”。"
            )
        
        prompt += "\n\n请简洁明了地回答用户问题，避免不必要的解释。"
        
        return prompt

    def _execute_tool(self, tool_call: Dict, user_permission: str = None) -> Dict:
        tool_name = tool_call.get("name")
        parameters = tool_call.get("parameters", {})
        
        result = self._tool_registry.execute_tool(tool_name, parameters, user_permission)
        
        if isinstance(result, dict):
            if 'output' in result and isinstance(result['output'], str):
                output = result['output']
                max_output_length = 1000
                if len(output) > max_output_length:
                    result['output'] = output[:500] + '... [输出被截断] ...' + output[-500:]
                    result['truncated'] = True
            
            if 'content' in result and isinstance(result['content'], str):
                content = result['content']
                max_content_length = 1000
                if len(content) > max_content_length:
                    result['content'] = content[:500] + '... [内容被截断] ...' + content[-500:]
                    result['truncated'] = True
        
        return result

    def compress_context(self):
        if len(self.messages) > self.max_context_size:
            system_messages = [msg for msg in self.messages if msg.get('role') == 'system']
            recent_messages = self.messages[-self.max_context_size + len(system_messages):]
            self.messages = system_messages + recent_messages

    def _check_memory_usage(self) -> bool:
        """检查内存使用情况"""
        try:
            if psutil is None:
                # psutil为可选依赖，缺失时跳过内存统计与限制，保证核心功能可用。
                return True

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            self.current_memory_usage = memory_info.rss / 1024 / 1024  # 转换为MB
            
            if self.current_memory_usage > self.max_memory_usage:
                # 内存使用超过限制，清理上下文
                self.compress_context()
                # 清理操作历史
                if len(self.operation_history) > 10:
                    self.operation_history = self.operation_history[-10:]
                # 清理运行进程
                self.running_processes = []
                return False
            return True
        except Exception:
                # 如果无法获取内存使用情况，默认返回True
                return True