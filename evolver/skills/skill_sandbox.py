"""SkillSandbox - 技能执行限制"""

import re
from typing import Tuple, Dict


class SkillSandbox:
    """技能执行限制"""

    ALLOWED_TOOLS = {
        "read_file", "write_file", "patch", "grep", "glob",
        "git_commit", "git_push", "search_files", "bash",
        "gmail_draft", "gmail_send", "gmail_search",
        "calendar_create_event", "calendar_list_events",
        "outlook_mail_draft", "outlook_mail_send", "outlook_mail_search",
        "outlook_calendar_create", "outlook_calendar_list",
        "feishu_message_send", "dingtalk_message_send",
    }

    SAFE_BASH_COMMANDS = {
        "git": ["status", "add", "commit", "push", "pull", "log", "diff", "checkout", "branch"],
        "pip": ["install", "list", "show", "uninstall", "freeze"],
        "npm": ["install", "run", "test", "start"],
        "python": ["-m", "-c", "-u", "-v"],
    }

    DENIED_PATTERNS = [
        r"rm\s+-rf", r"sudo", r"su\s", r"chmod\s+777", r"wget", r"curl",
        r"\|\s*sh", r"\|\s*bash", r">\s*/dev/", r"\&amp;\&amp;.*rm"
    ]

    def validate_skill(self, skill: Dict) -> Tuple[bool, str]:
        """校验技能安全性"""
        if "action" not in skill or "steps" not in skill["action"]:
            return False, "技能格式错误"
        
        for i, step in enumerate(skill["action"]["steps"]):
            tool = step.get("tool")
            if tool not in self.ALLOWED_TOOLS:
                return False, f"步骤{i+1}: 不允许的工具 {tool}"
            
            if tool == "bash":
                cmd = step.get("command", "")
                if not isinstance(cmd, str) or not cmd.strip():
                    return False, f"步骤{i+1}: bash命令不能为空"
                # 检查危险模式
                for pattern in self.DENIED_PATTERNS:
                    if re.search(pattern, cmd, re.IGNORECASE):
                        return False, f"步骤{i+1}: 危险命令模式 {pattern}"
                # 检查bash命令白名单
                cmd_parts = cmd.split()
                if cmd_parts:
                    base = cmd_parts[0]
                    if base not in self.SAFE_BASH_COMMANDS:
                        return False, f"步骤{i+1}: 不允许的bash命令 {base}"
                    if len(cmd_parts) > 1 and cmd_parts[1] not in self.SAFE_BASH_COMMANDS[base]:
                        return False, f"步骤{i+1}: 不允许的子命令"
        
        return True, "校验通过"

    def validate_skill_version(self, skill: Dict) -> Tuple[bool, str]:
        """校验技能版本一致性"""
        current_ver = skill.get("version", 1)
        prev_versions = skill.get("previous_versions", [])
        
        for pv in prev_versions:
            if pv.get("version", 0) >= current_ver:
                return False, f"旧版本{pv.get('version')}编号>=当前版本{current_ver}"
        
        return True, "版本校验通过"

    def execute_skill(self, skill: Dict, context: Dict) -> Dict:
        """执行技能"""
        # 验证技能
        valid, message = self.validate_skill(skill)
        if not valid:
            return {"error": message}
        
        # 执行技能步骤
        results = []
        for step in skill["action"]["steps"]:
            # 这里应该调用相应的工具执行
            # 简化实现，返回模拟结果
            results.append({"step": step, "result": "执行成功"})
        
        return {"results": results}
