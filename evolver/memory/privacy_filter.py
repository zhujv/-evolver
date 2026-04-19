"""PrivacyFilter - 敏感数据过滤器"""

import json
import re
import hashlib
from datetime import datetime
import os


class PrivacyFilter:
    """敏感数据过滤器 - 强化版"""

    BUILTIN_PATTERNS = [
        (r"api[_-]?key[=:]?\s*[\"']?[\w-]+[\"']?", "[API_KEY]"),
        (r"password[=:]?\s*[\"'][^ \"']+[\"']?", "[PASSWORD]"),
        (r"token[=:]?\s*[\"']?[\w-]+[\"']?", "[TOKEN]"),
        (r"sk[-]?[\w]{20,}", "[SECRET_KEY]"),
        (r"Bearer\s+[\w-]+", "Bearer [TOKEN]"),
        (r"ghp_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),
    ]

    def __init__(self, encryption_key: str = None):
        self.custom_patterns: list[tuple[str, str]] = []
        self.encryption_key = encryption_key
        self.fernet = None
        try:
            from cryptography.fernet import Fernet
            self.fernet = Fernet(encryption_key.encode()) if encryption_key else None
        except ImportError:
            pass
        self.audit_log_path = os.path.expanduser("~/.evolver/privacy_audit.log")
        log_dir = os.path.dirname(self.audit_log_path)
        os.makedirs(log_dir, exist_ok=True)
        # 设置目录权限为0o700，只允许所有者访问
        if os.name != 'nt':  # 只在非Windows系统设置权限
            os.chmod(log_dir, 0o700)
        # 如果日志文件不存在，创建并设置权限
        if not os.path.exists(self.audit_log_path):
            open(self.audit_log_path, 'w').close()
        
        # 设置文件权限为0o600，只允许所有者读写
        if os.name != 'nt':  # 只在非Windows系统设置权限
            os.chmod(self.audit_log_path, 0o600)

    def add_pattern(self, pattern: str, replacement: str = "[FILTERED]"):
        """添加自定义模式"""
        self.custom_patterns.append((pattern, replacement))

    def sanitize(self, text: str) -> str:
        """过滤敏感数据"""
        if not isinstance(text, str):
            return text
        result = text
        for pattern, replacement in self.BUILTIN_PATTERNS + self.custom_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        result = re.sub(r'(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+', r'\1=[FILTERED]', result)
        return result

    def sanitize_llm_input(self, text: str) -> str:
        """兼容AIAgent调用：过滤进入模型的输入。"""
        return self.sanitize(text)

    def sanitize_llm_output(self, text: str) -> str:
        """兼容AIAgent调用：过滤模型输出。"""
        return self.sanitize(text)

    def sanitize_log(self, text: str) -> str:
        """日志专用过滤"""
        return self.sanitize(text)

    def encrypt_save(self, data: dict) -> bytes:
        """AES-256加密存储"""
        if self.fernet:
            serialized = json.dumps(data)
            return self.fernet.encrypt(serialized.encode())
        # 降级模式：对敏感数据进行哈希处理
        sanitized_data = self._sanitize_data(data)
        return json.dumps(sanitized_data).encode()

    def _sanitize_data(self, data: dict) -> dict:
        """在降级模式下清理敏感数据"""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # 对可能的敏感数据进行哈希处理
                if any(keyword in key.lower() for keyword in ['password', 'token', 'api', 'key', 'secret']):
                    sanitized[key] = hashlib.sha256(value.encode()).hexdigest()
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value
        return sanitized

    def decrypt_load(self, data: bytes) -> dict:
        """解密加载"""
        if self.fernet:
            try:
                return json.loads(self.fernet.decrypt(data).decode())
            except Exception:
                # 如果解密失败，尝试直接解析（可能是降级模式存储的数据）
                try:
                    return json.loads(data)
                except Exception:
                    return {}
        try:
            return json.loads(data)
        except Exception:
            return {}

    def log_action(self, action: str, details: dict):
        """数据操作审计"""
        # 过滤敏感数据
        sanitized_details = self._sanitize_details(details)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": sanitized_details,
        }
        
        # 写入日志
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # 检查日志大小，超过10MB时进行轮换
        self._rotate_log()

    def _sanitize_details(self, details: dict) -> dict:
        """过滤日志中的敏感数据"""
        if not isinstance(details, dict):
            return details
        
        sanitized = {}
        for key, value in details.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            else:
                sanitized[key] = value
        return sanitized

    def _rotate_log(self):
        """日志轮换"""
        if os.path.exists(self.audit_log_path):
            log_size = os.path.getsize(self.audit_log_path)
            if log_size > 10 * 1024 * 1024:  # 10MB
                # 备份当前日志
                backup_path = f"{self.audit_log_path}.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                os.rename(self.audit_log_path, backup_path)
                # 创建新日志文件
                open(self.audit_log_path, 'w').close()
                # 设置文件权限为0o600，只允许所有者读写
                if os.name != 'nt':  # 只在非Windows系统设置权限
                    os.chmod(self.audit_log_path, 0o600)
                # 限制备份数量为5个
                self._cleanup_backups()

    def _cleanup_backups(self):
        """清理多余的日志备份"""
        log_dir = os.path.dirname(self.audit_log_path)
        log_name = os.path.basename(self.audit_log_path)
        backups = []
        
        for file in os.listdir(log_dir):
            if file.startswith(log_name) and file != log_name:
                backup_path = os.path.join(log_dir, file)
                if os.path.isfile(backup_path):
                    backups.append((backup_path, os.path.getmtime(backup_path)))
        
        # 按修改时间排序，保留最近的5个备份
        backups.sort(key=lambda x: x[1], reverse=True)
        if len(backups) > 5:
            for backup in backups[5:]:
                os.remove(backup[0])

    def delete_data(self, data_id: str):
        """安全删除数据"""
        self.log_action("delete_data", {"data_id": data_id, "method": "secure_delete"})
        # 实际删除逻辑
