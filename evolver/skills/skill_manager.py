"""SkillManager - 技能管理（集成执行引擎+审批工作流+语义匹配）"""

import logging
from typing import List, Dict, Optional
from .skill_store import SkillStore
from .skill_sandbox import SkillSandbox
from .skill_executor import SkillExecutor
from .skill_approval import SkillApproval

logger = logging.getLogger(__name__)


BUILTIN_OFFICE_SKILLS: List[Dict] = [
    {
        "id": "office_meeting_minutes",
        "name": "会议纪要整理",
        "description": "先输出可发布纪要，再附行动项闭环；字段含结论、行动项、负责人、截止时间、风险",
        "trigger": {
            "patterns": ["会议纪要", "会议总结", "行动项", "todo", "纪要"]
        },
        "scope": "office",
        "version": 1,
        "action": {
            "steps": [
                {"tool": "memory_recall", "parameters": {"query": "会议内容 讨论要点"}},
                {"tool": "memory_save", "parameters": {"key": "meeting_minutes", "value": "{{message}}"}}
            ]
        }
    },
    {
        "id": "office_email_draft",
        "name": "邮件草拟助手",
        "description": "按目标和语气直接给可发送邮件草稿，并附可选标题与待确认信息",
        "trigger": {
            "patterns": ["邮件", "回信", "抄送", "主题", "email"]
        },
        "scope": "office",
        "version": 1,
        "action": {
            "steps": [
                {"tool": "memory_recall", "parameters": {"query": "邮件模板 通讯"}}
            ]
        }
    },
    {
        "id": "office_document_summary",
        "name": "文档总结提炼",
        "description": "输出执行摘要、关键结论、风险点、建议动作，优先给落地结论",
        "trigger": {
            "patterns": ["总结", "摘要", "重点", "风险", "提炼"]
        },
        "scope": "office",
        "version": 1,
        "action": {
            "steps": [
                {"tool": "memory_recall", "parameters": {"query": "文档内容 关键信息"}}
            ]
        }
    },
    {
        "id": "office_schedule_planning",
        "name": "日程与待办规划",
        "description": "生成按优先级排序的日程与待办，含时间块、依赖项与下一步动作",
        "trigger": {
            "patterns": ["日程", "待办", "安排", "计划", "优先级"]
        },
        "scope": "office",
        "version": 1,
        "action": {
            "steps": [
                {"tool": "memory_recall", "parameters": {"query": "日程安排 待办事项"}}
            ]
        }
    },
    {
        "id": "memory_management",
        "name": "记忆管理助手",
        "description": "管理和检索记忆，包括保存重要信息、搜索历史记录和整理记忆标签",
        "trigger": {
            "patterns": ["记忆", "存储", "搜索", "标签", "管理"]
        },
        "scope": "memory",
        "version": 1,
        "action": {
            "steps": [
                {"tool": "memory_recall", "parameters": {"query": "{{message}}"}},
                {"tool": "memory_save", "parameters": {"key": "memory_management", "value": "{{message}}"}}
            ]
        }
    },
    {
        "id": "skill_management",
        "name": "技能管理助手",
        "description": "管理和执行技能，包括列出可用技能、执行指定技能和管理技能审批",
        "trigger": {
            "patterns": ["技能", "执行", "管理", "审批", "列表"]
        },
        "scope": "skill",
        "version": 1,
        "action": {
            "steps": [
                {"tool": "list_skills", "parameters": {}}
            ]
        }
    },
    {
        "id": "project_management",
        "name": "项目管理助手",
        "description": "管理项目和工作项，包括创建项目、列出项目和更新工作项状态",
        "trigger": {
            "patterns": ["项目", "管理", "工作项", "创建", "列表"]
        },
        "scope": "project",
        "version": 1,
        "action": {
            "steps": [
                {"tool": "list_projects", "parameters": {}}
            ]
        }
    },
]


class SkillManager:
    """技能管理 - 集成执行引擎+审批工作流+语义匹配"""

    def __init__(self):
        self._skill_store = SkillStore()
        self._skill_sandbox = SkillSandbox()
        self._skill_executor = SkillExecutor()
        self._skill_approval = SkillApproval()

    def set_tool_registry(self, registry):
        self._skill_executor.set_tool_registry(registry)

    def list_skills(self) -> List[Dict]:
        custom_skills = self._skill_store.list_skills()
        return [*BUILTIN_OFFICE_SKILLS, *custom_skills]

    def save_skill(self, skill: Dict, require_approval: bool = True) -> Dict:
        valid, message = self._skill_sandbox.validate_skill(skill)
        if not valid:
            return {"success": False, "error": message}

        if require_approval:
            approval_result = self._skill_approval.request_approval(skill, action="create")
            if not approval_result.get("approved"):
                return {
                    "success": False,
                    "status": "pending_approval",
                    "approval_id": skill.get("id", ""),
                    "confidence": approval_result.get("confidence", 0),
                    "reason": approval_result.get("reason", "需要人工审批")
                }

        saved = self._skill_store.save_skill(skill)
        return {"success": saved, "status": "approved" if saved else "error"}

    def approve_skill(self, skill_id: str) -> Dict:
        return self._skill_approval.approve(skill_id)

    def reject_skill(self, skill_id: str, reason: str = "") -> Dict:
        return self._skill_approval.reject(skill_id, reason)

    def get_pending_approvals(self) -> List[Dict]:
        return self._skill_approval.get_pending()

    def get_relevant(self, query: str, agent_focus: str = "") -> List[Dict]:
        custom_skills = self._skill_store.list_skills()
        skills = list(custom_skills)
        if agent_focus == "office_productivity":
            skills = [*BUILTIN_OFFICE_SKILLS, *skills]

        scored_skills = []
        lowered_query = (query or "").lower()

        for skill in skills:
            score = self._calculate_relevance(skill, lowered_query)
            if score > 0:
                scored_skills.append((score, skill))

        scored_skills.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored_skills]

    def execute_skill(self, skill_name: str, context: Dict, check_approval: bool = True) -> Dict:
        skill = self._skill_store.get_skill(skill_name)

        if not skill:
            for builtin in BUILTIN_OFFICE_SKILLS:
                if builtin.get("id") == skill_name or builtin.get("name") == skill_name:
                    skill = builtin
                    break

        if not skill:
            return {"error": "技能不存在"}

        valid, message = self._skill_sandbox.validate_skill(skill)
        if not valid:
            return {"error": message}

        if check_approval and not self._skill_approval.is_approved(skill.get("id", "")):
            approval_result = self._skill_approval.request_approval(skill, action="execute")
            if not approval_result.get("approved"):
                return {
                    "error": "技能未获审批",
                    "status": approval_result.get("status"),
                    "approval_id": skill.get("id", ""),
                    "confidence": approval_result.get("confidence", 0)
                }

        return self._skill_executor.execute_skill(skill, context)

    def delete_skill(self, skill_name: str) -> bool:
        return self._skill_store.delete_skill(skill_name)

    def _calculate_relevance(self, skill: Dict, lowered_query: str) -> float:
        score = 0.0
        patterns = skill.get("trigger", {}).get("patterns", [])

        for pattern in patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in lowered_query:
                score += 1.0
            elif lowered_query in pattern_lower:
                score += 0.5
            else:
                query_chars = set(lowered_query)
                pattern_chars = set(pattern_lower)
                overlap = len(query_chars & pattern_chars)
                total = len(query_chars | pattern_chars)
                if total > 0:
                    jaccard = overlap / total
                    if jaccard > 0.3:
                        score += jaccard * 0.3

        description = skill.get("description", "").lower()
        if description:
            desc_words = set(description.split())
            query_words = set(lowered_query.split())
            overlap = len(desc_words & query_words)
            if overlap > 0:
                score += overlap * 0.2

        name = skill.get("name", "").lower()
        if name and any(w in name for w in lowered_query.split()):
            score += 0.5

        return score
