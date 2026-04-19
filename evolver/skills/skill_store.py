"""SkillStore - 技能存储"""

import os
import json
import uuid
import re
from typing import List, Dict


class SkillStore:
    """技能存储"""

    def __init__(self, skills_dir: str = "~/.evolver/skills"):
        self.skills_dir = os.path.expanduser(skills_dir)
        os.makedirs(self.skills_dir, exist_ok=True)
        # 设置目录权限为0o700，只允许所有者访问
        if os.name != 'nt':  # 只在非Windows系统设置权限
            os.chmod(self.skills_dir, 0o700)

    def list_skills(self) -> List[Dict]:
        """列出所有技能"""
        skills = []
        if not os.path.exists(self.skills_dir):
            return skills
        for file in os.listdir(self.skills_dir):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(self.skills_dir, file), 'r', encoding='utf-8') as f:
                        skill = json.load(f)
                        skills.append(skill)
                except (json.JSONDecodeError, IOError):
                    continue
        return skills

    def save_skill(self, skill: Dict) -> bool:
        """保存技能"""
        try:
            # 生成技能ID
            if "id" not in skill:
                skill["id"] = str(uuid.uuid4())
            safe_name = self._sanitize_skill_name(skill.get("name", ""))
            if not safe_name:
                return False
            
            # 保存技能
            skill_path = self._build_skill_path(safe_name)
            if not skill_path:
                return False
            with open(skill_path, 'w', encoding='utf-8') as f:
                json.dump(skill, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            return False

    def get_skill(self, skill_name: str) -> Dict:
        """获取技能"""
        safe_name = self._sanitize_skill_name(skill_name)
        if not safe_name:
            return None
        skill_path = self._build_skill_path(safe_name)
        if not skill_path:
            return None
        if not os.path.exists(skill_path):
            return None
        
        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def delete_skill(self, skill_name: str) -> bool:
        """删除技能"""
        safe_name = self._sanitize_skill_name(skill_name)
        if not safe_name:
            return False
        skill_path = self._build_skill_path(safe_name)
        if not skill_path:
            return False
        if not os.path.exists(skill_path):
            return False
        
        try:
            os.remove(skill_path)
            return True
        except OSError:
            return False

    def _sanitize_skill_name(self, skill_name: str) -> str:
        """仅允许安全字符作为技能名，避免路径穿越。"""
        if not isinstance(skill_name, str):
            return ""
        name = skill_name.strip()
        if not name or len(name) > 100:
            return ""
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            return ""
        if name.startswith("."):
            return ""
        return name

    def _build_skill_path(self, safe_name: str) -> str:
        candidate = os.path.abspath(os.path.join(self.skills_dir, f"{safe_name}.json"))
        root = os.path.abspath(self.skills_dir)
        try:
            if os.path.commonpath([candidate, root]) != root:
                return ""
        except ValueError:
            return ""
        return candidate
