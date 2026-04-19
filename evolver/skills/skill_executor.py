"""SkillExecutor - 技能执行引擎（真正调用ToolRegistry执行步骤）"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SkillExecutor:
    """技能执行引擎 - 将技能步骤翻译为ToolRegistry调用"""

    def __init__(self, tool_registry=None):
        self._tool_registry = tool_registry

    def set_tool_registry(self, registry):
        self._tool_registry = registry

    def execute_skill(self, skill: Dict, context: Dict) -> Dict:
        if not self._tool_registry:
            return {"error": "工具注册表未初始化"}

        action = skill.get("action", {})
        steps = action.get("steps", [])
        if not steps:
            return {"error": "技能无执行步骤"}

        results = []
        step_outputs = {}

        for i, step in enumerate(steps):
            tool_name = step.get("tool")
            if not tool_name:
                results.append({"step": i + 1, "error": "缺少工具名称"})
                break

            parameters = self._render_parameters(step, context, step_outputs)

            try:
                result = self._tool_registry.execute_tool(tool_name, parameters)
                step_outputs[f"step_{i + 1}"] = result
                results.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "result": result
                })

                if isinstance(result, dict) and result.get("error"):
                    should_continue = step.get("on_error", "stop") == "continue"
                    if not should_continue:
                        break
            except Exception as e:
                logger.error(f"Skill step {i + 1} failed: {e}")
                results.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "error": str(e)
                })
                should_continue = step.get("on_error", "stop") == "continue"
                if not should_continue:
                    break

        return {
            "skill_id": skill.get("id", ""),
            "skill_name": skill.get("name", ""),
            "results": results,
            "success": all(
                not (isinstance(r.get("result", {}), dict) and r["result"].get("error"))
                for r in results
            )
        }

    def _render_parameters(self, step: Dict, context: Dict, step_outputs: Dict) -> Dict:
        parameters = dict(step.get("parameters", {}))

        if not parameters:
            tool = step.get("tool", "")
            if tool == "bash":
                cmd = step.get("command", "")
                if cmd:
                    cmd = self._render_template(cmd, context, step_outputs)
                    parameters = {"command": cmd}
            elif tool == "write_file":
                content = step.get("content", "")
                path = step.get("path", "")
                if content:
                    content = self._render_template(content, context, step_outputs)
                parameters = {"path": path, "content": content}
            elif tool == "read_file":
                path = step.get("path", "")
                parameters = {"path": path}
            elif tool == "patch":
                parameters = {
                    "path": step.get("path", ""),
                    "oldString": step.get("old_string", ""),
                    "newString": step.get("new_string", "")
                }
            elif tool == "grep":
                parameters = {
                    "pattern": step.get("pattern", ""),
                    "path": step.get("path"),
                    "include": step.get("include")
                }
            elif tool == "glob":
                parameters = {"pattern": step.get("pattern", "")}
            elif tool == "memory_save":
                parameters = {
                    "key": step.get("key", ""),
                    "value": self._render_template(step.get("value", ""), context, step_outputs)
                }
            elif tool == "memory_recall":
                parameters = {"query": step.get("query", "")}

        for key, value in parameters.items():
            if isinstance(value, str):
                parameters[key] = self._render_template(value, context, step_outputs)

        return parameters

    def _render_template(self, template: str, context: Dict, step_outputs: Dict) -> str:
        if not isinstance(template, str):
            return template

        def replace_var(match):
            var_name = match.group(1)
            if var_name in context:
                return str(context[var_name])
            if var_name in step_outputs:
                val = step_outputs[var_name]
                if isinstance(val, dict):
                    return val.get("content", val.get("output", str(val)))
                return str(val)
            return match.group(0)

        result = re.sub(r'\{\{(\w+)\}\}', replace_var, template)

        def replace_dotted(match):
            path = match.group(1)
            parts = path.split(".")
            obj = context
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj.get(part)
                else:
                    return match.group(0)
                if obj is None:
                    return match.group(0)
            return str(obj)

        result = re.sub(r'\{\{([\w.]+)\}\}', replace_dotted, result)

        return result
