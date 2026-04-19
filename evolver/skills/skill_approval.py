"""SkillApproval - 技能审批工作流"""

import json
import os
import time
import hashlib
import logging
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)


class SkillApproval:
    """技能审批工作流 - 管理技能的创建、修改、执行审批"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"

    def __init__(self, approval_dir: str = "~/.evolver/approvals"):
        self.approval_dir = os.path.expanduser(approval_dir)
        os.makedirs(self.approval_dir, exist_ok=True)
        self._auto_apply_threshold = 0.95

    def request_approval(self, skill: Dict, action: str = "create") -> Dict:
        skill_id = skill.get("id", "")
        skill_name = skill.get("name", "")
        skill_hash = self._compute_hash(skill)

        existing = self._get_approval(skill_id)
        if existing and existing.get("hash") == skill_hash:
            if existing.get("status") == self.APPROVED:
                return {
                    "approved": True,
                    "status": self.APPROVED,
                    "reason": "技能未变更，沿用上次审批"
                }

        confidence = self._calculate_confidence(skill)

        if confidence >= self._auto_apply_threshold and action != "execute":
            approval = {
                "skill_id": skill_id,
                "skill_name": skill_name,
                "action": action,
                "status": self.AUTO_APPROVED,
                "confidence": confidence,
                "hash": skill_hash,
                "timestamp": int(time.time()),
                "auto_approved": True
            }
            self._save_approval(approval)
            return {
                "approved": True,
                "status": self.AUTO_APPROVED,
                "confidence": confidence,
                "reason": f"置信度 {confidence:.2f} >= {self._auto_apply_threshold}，自动审批通过"
            }

        approval = {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "action": action,
            "status": self.PENDING,
            "confidence": confidence,
            "hash": skill_hash,
            "timestamp": int(time.time()),
            "details": {
                "description": skill.get("description", ""),
                "steps_count": len(skill.get("action", {}).get("steps", [])),
                "tools_used": [s.get("tool") for s in skill.get("action", {}).get("steps", [])],
                "scope": skill.get("scope", "general")
            }
        }
        self._save_approval(approval)
        return {
            "approved": False,
            "status": self.PENDING,
            "confidence": confidence,
            "approval_id": skill_id,
            "reason": "需要人工审批",
            "details": approval.get("details", {})
        }

    def approve(self, skill_id: str, approver: str = "user") -> Dict:
        approval = self._get_approval(skill_id)
        if not approval:
            return {"error": "审批记录不存在"}

        if approval.get("status") != self.PENDING:
            return {"error": f"当前状态为 {approval.get('status')}，无法审批"}

        approval["status"] = self.APPROVED
        approval["approver"] = approver
        approval["approved_at"] = int(time.time())
        self._save_approval(approval)

        return {
            "approved": True,
            "status": self.APPROVED,
            "skill_id": skill_id
        }

    def reject(self, skill_id: str, reason: str = "") -> Dict:
        approval = self._get_approval(skill_id)
        if not approval:
            return {"error": "审批记录不存在"}

        approval["status"] = self.REJECTED
        approval["reject_reason"] = reason
        approval["rejected_at"] = int(time.time())
        self._save_approval(approval)

        return {
            "approved": False,
            "status": self.REJECTED,
            "skill_id": skill_id,
            "reason": reason
        }

    def get_pending(self) -> List[Dict]:
        pending = []
        if not os.path.exists(self.approval_dir):
            return pending
        for f in os.listdir(self.approval_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.approval_dir, f), "r", encoding="utf-8") as fh:
                        approval = json.load(fh)
                        if approval.get("status") == self.PENDING:
                            pending.append(approval)
                except (json.JSONDecodeError, IOError):
                    continue
        return pending

    def is_approved(self, skill_id: str) -> bool:
        approval = self._get_approval(skill_id)
        if not approval:
            return False
        return approval.get("status") in (self.APPROVED, self.AUTO_APPROVED)

    def _calculate_confidence(self, skill: Dict) -> float:
        confidence = 0.5

        if skill.get("description"):
            confidence += 0.05
        if skill.get("scope") in ("office", "general"):
            confidence += 0.05
        if skill.get("trigger", {}).get("patterns"):
            confidence += 0.05

        steps = skill.get("action", {}).get("steps", [])
        if steps:
            confidence += min(len(steps) * 0.02, 0.1)

        safe_tools = {"read_file", "grep", "glob", "search_files", "memory_recall", "memory_save"}
        for step in steps:
            tool = step.get("tool", "")
            if tool in safe_tools:
                confidence += 0.02
            elif tool == "bash":
                confidence -= 0.1
            elif tool in ("write_file", "patch"):
                confidence -= 0.03

        if skill.get("version", 1) > 1:
            confidence += 0.05

        return max(0.0, min(1.0, confidence))

    def _compute_hash(self, skill: Dict) -> str:
        skill_copy = {k: v for k, v in skill.items() if k not in ("id", "created_at")}
        content = json.dumps(skill_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_approval(self, skill_id: str) -> Optional[Dict]:
        path = os.path.join(self.approval_dir, f"{skill_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_approval(self, approval: Dict):
        skill_id = approval.get("skill_id", "unknown")
        path = os.path.join(self.approval_dir, f"{skill_id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(approval, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save approval: {e}")
