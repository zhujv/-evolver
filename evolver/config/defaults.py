"""默认配置"""

DEFAULT_CONFIG = {
    "model": {
        "provider": "openrouter",
        "default": "anthropic/claude-sonnet-4-20250514",
        "fallback": [
            "openai/gpt-4o"
        ]
    },
    "tools": {
        "enabled": [
            "file",
            "bash",
            "search",
            "memory",
            "mcp"
        ],
        "disabled": [],
        "permissions": {
            "read_file": "read",
            "write_file": "write",
            "patch": "write",
            "grep": "read",
            "glob": "read",
            "bash": "execute",
            "search_files": "read",
            "memory_save": "write",
            "memory_recall": "read",
            "gmail_draft": "write",
            "gmail_send": "write",
            "gmail_search": "read",
            "calendar_create_event": "write",
            "calendar_list_events": "read",
            "outlook_mail_draft": "write",
            "outlook_mail_send": "write",
            "outlook_mail_search": "read",
            "outlook_calendar_create": "write",
            "outlook_calendar_list": "read",
            "feishu_message_send": "write",
            "dingtalk_message_send": "write"
        }
    },
    "permissions": {
        "default": "read",
        "levels": {
            "read": ["read_file", "grep", "glob", "search_files", "memory_recall"],
            "write": ["write_file", "patch", "memory_save"],
            "execute": ["bash"],
            "admin": ["read_file", "write_file", "patch", "grep", "glob", "bash", "search_files", "memory_save", "memory_recall"]
        }
    },
    "memory": {
        "enabled": True,
        "auto_save": True,
        "vector_db": "~/.evolver/vector_db",
        "search_mode": "hybrid",
        "short_term_max": 50,
        "short_term_ttl": 3600,
        "long_term_ttl_days": 90
    },
    "privacy": {
        "filter_enabled": True,
        "encrypt_memories": False
    },
    "ui": {
        "theme": "default",
        "colorful": True
    },
    "evolution": {
        "enabled": True,
        "auto_learn": False,
        "auto_create_skills": False,
        "confirm_before_save": True,
        "audit_log": True,
        "max_confidence_auto_apply": 0.95,
        "skill_approval_required": True
    },
    "mcp": {
        "enabled": True,
        "servers": {},
        "auto_discover": True,
        "expose_evolver_tools": True
    },
    "project": {
        "active_project_id": "default"
    },
    "integrations": {
        "gmail": {
            "enabled": False,
            "client_id": "",
            "client_secret": "",
            "refresh_token": "",
            "from_email": "",
            "require_send_confirmation": True
        },
        "google_calendar": {
            "enabled": False,
            "client_id": "",
            "client_secret": "",
            "refresh_token": "",
            "calendar_id": "primary",
            "require_create_confirmation": True
        },
        "outlook": {
            "enabled": False,
            "tenant_id": "common",
            "client_id": "",
            "client_secret": "",
            "refresh_token": "",
            "scope": "offline_access Mail.ReadWrite Mail.Send Calendars.ReadWrite",
            "timezone": "UTC",
            "require_send_confirmation": True,
            "require_create_confirmation": True
        },
        "feishu": {
            "enabled": False,
            "app_id": "",
            "app_secret": "",
            "receive_id_type": "open_id"
        },
        "dingtalk": {
            "enabled": False,
            "webhook": "",
            "secret": ""
        }
    }
}
