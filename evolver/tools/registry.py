"""ToolRegistry - 工具注册和执行"""

from typing import Dict, Any
from .file_tools import FileTools
from .bash_tool import BashTool
from .search_tools import SearchTools
from .memory_tools import MemoryTools
from .office_tools import OfficeTools
from .computer_tool import ComputerTool


class ToolRegistry:
    """工具注册和执行"""

    def __init__(self):
        self._tools = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "patch": self._patch,
            "grep": self._grep,
            "glob": self._glob,
            "bash": self._bash,
            "search_files": self._search_files,
            "memory_save": self._memory_save,
            "memory_recall": self._memory_recall,
            "gmail_draft": self._gmail_draft,
            "gmail_send": self._gmail_send,
            "gmail_search": self._gmail_search,
            "calendar_create_event": self._calendar_create_event,
            "calendar_list_events": self._calendar_list_events,
            "outlook_mail_draft": self._outlook_mail_draft,
            "outlook_mail_send": self._outlook_mail_send,
            "outlook_mail_search": self._outlook_mail_search,
            "outlook_calendar_create": self._outlook_calendar_create,
            "outlook_calendar_list": self._outlook_calendar_list,
            "feishu_message_send": self._feishu_message_send,
            "dingtalk_message_send": self._dingtalk_message_send,
            "open_url": self._open_url,
            "open_browser": self._open_browser,
            "open_file": self._open_file,
            "open_folder": self._open_folder,
            "open_app": self._open_app,
            "get_system_info": self._get_system_info,
            "list_browsers": self._list_browsers,
            "search_web": self._search_web,
            "get_clipboard": self._get_clipboard,
            "set_clipboard": self._set_clipboard,
        }
        self._file_tools = FileTools()
        self._bash_tool = BashTool()
        self._search_tools = SearchTools()
        self._memory_tools = MemoryTools()
        self._office_tools = OfficeTools()
        self._computer_tool = ComputerTool()
        
        # 加载权限配置
        from ..config.loader import ConfigLoader
        config = ConfigLoader().load()
        self._permissions = config.get('tools', {}).get('permissions', {})
        self._permission_levels = config.get('permissions', {}).get('levels', {})
        self._default_permission = config.get('permissions', {}).get('default', 'read')

    def execute_tool(self, tool_name: str, parameters: Dict, user_permission: str = None) -> Dict:
        """执行工具"""
        if tool_name not in self._tools:
            return {"error": f"工具不存在: {tool_name}"}
        
        # 检查权限
        if not self._check_permission(tool_name, user_permission):
            return {"error": f"没有执行工具 {tool_name} 的权限"}

        # 高风险动作强制要求显式确认，防止仅依赖模型提示
        confirm_required = {"gmail_send", "calendar_create_event", "outlook_mail_send", "outlook_calendar_create"}
        if tool_name in confirm_required and not parameters.get("confirm", False):
            return {"error": f"{tool_name} 属于高风险动作，请显式传入 confirm=true 后重试"}
        
        try:
            return self._tools[tool_name](**parameters)
        except Exception as e:
            return {"error": str(e)}

    def _check_permission(self, tool_name: str, user_permission: str = None) -> bool:
        """检查权限"""
        # 如果没有指定用户权限，使用默认权限
        if not user_permission:
            user_permission = self._default_permission
        
        # 检查工具是否需要权限
        required_permission = self._permissions.get(tool_name, 'read')
        
        # 检查用户权限级别是否足够
        # 权限级别从低到高：read < write < execute < admin
        permission_levels = {
            'read': 1,
            'write': 2,
            'execute': 3,
            'admin': 4
        }
        
        # 获取用户权限级别和所需权限级别的数值
        user_level = permission_levels.get(user_permission, 1)
        required_level = permission_levels.get(required_permission, 1)
        
        # 如果用户权限级别大于等于所需权限级别，则允许执行
        if user_level >= required_level:
            return True
        
        return False

    def _read_file(self, path: str, offset: int = None, limit: int = None) -> Dict:
        """读取文件"""
        return self._file_tools.read_file(path, offset, limit)

    def _write_file(self, path: str, content: str) -> Dict:
        """写入文件"""
        return self._file_tools.write_file(path, content)

    def _patch(self, path: str, oldString: str, newString: str) -> Dict:
        """补丁文件"""
        return self._file_tools.patch(path, oldString, newString)

    def _grep(self, pattern: str, path: str = None, include: str = None) -> Dict:
        """搜索文件"""
        return self._file_tools.grep(pattern, path, include)

    def _glob(self, pattern: str) -> Dict:
        """文件匹配"""
        return self._file_tools.glob(pattern)

    def _bash(self, command: str, timeout: int = None, workdir: str = None) -> Dict:
        """执行bash命令"""
        return self._bash_tool.execute(command, timeout, workdir)

    def _search_files(self, pattern: str, root_path: str = None) -> Dict:
        """搜索文件"""
        return self._search_tools.search_files(pattern, root_path)

    def _memory_save(self, key: str, value: Any) -> Dict:
        """保存记忆"""
        return self._memory_tools.save(key, value)

    def _memory_recall(self, query: str) -> Dict:
        """检索记忆"""
        return self._memory_tools.recall(query)

    def _gmail_draft(self, to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> Dict:
        """创建Gmail草稿"""
        return self._office_tools.gmail_draft(to=to, subject=subject, body=body, cc=cc, bcc=bcc)

    def _gmail_send(self, to: str, subject: str, body: str, cc: str = "", bcc: str = "", confirm: bool = False) -> Dict:
        """发送Gmail邮件"""
        return self._office_tools.gmail_send(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            confirm=confirm,
        )

    def _gmail_search(self, query: str, max_results: int = 10) -> Dict:
        """搜索Gmail"""
        return self._office_tools.gmail_search(query=query, max_results=max_results)

    def _calendar_create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: str = "",
        confirm: bool = False,
    ) -> Dict:
        """创建Google日历事件"""
        return self._office_tools.calendar_create_event(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            attendees=attendees,
            confirm=confirm,
        )

    def _calendar_list_events(self, start_time: str = "", end_time: str = "", max_results: int = 10) -> Dict:
        """列出Google日历事件"""
        return self._office_tools.calendar_list_events(
            start_time=start_time,
            end_time=end_time,
            max_results=max_results,
        )

    def _outlook_mail_draft(self, to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> Dict:
        """创建Outlook草稿"""
        return self._office_tools.outlook_mail_draft(to=to, subject=subject, body=body, cc=cc, bcc=bcc)

    def _outlook_mail_send(self, to: str, subject: str, body: str, cc: str = "", bcc: str = "", confirm: bool = False) -> Dict:
        """发送Outlook邮件"""
        return self._office_tools.outlook_mail_send(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            confirm=confirm,
        )

    def _outlook_mail_search(self, query: str, max_results: int = 10) -> Dict:
        """搜索Outlook邮件"""
        return self._office_tools.outlook_mail_search(query=query, max_results=max_results)

    def _outlook_calendar_create(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: str = "",
        confirm: bool = False,
    ) -> Dict:
        """创建Outlook日历事件"""
        return self._office_tools.outlook_calendar_create(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            attendees=attendees,
            confirm=confirm,
        )

    def _outlook_calendar_list(self, start_time: str = "", end_time: str = "", max_results: int = 10) -> Dict:
        """列出Outlook日历事件"""
        return self._office_tools.outlook_calendar_list(
            start_time=start_time,
            end_time=end_time,
            max_results=max_results,
        )

    def _feishu_message_send(self, receive_id: str, content: str, msg_type: str = "text") -> Dict:
        """发送飞书消息"""
        return self._office_tools.feishu_message_send(receive_id=receive_id, content=content, msg_type=msg_type)

    def _dingtalk_message_send(self, text: str, title: str = "") -> Dict:
        """发送钉钉消息"""
        return self._office_tools.dingtalk_message_send(text=text, title=title)

    def _open_url(self, url: str, browser: str = None) -> Dict:
        """打开URL"""
        return self._computer_tool.open_url(url, browser)

    def _open_browser(self, url: str = None, browser: str = "default") -> Dict:
        """打开浏览器"""
        return self._computer_tool.open_browser(url, browser)

    def _open_file(self, path: str) -> Dict:
        """打开文件"""
        return self._computer_tool.open_file(path)

    def _open_folder(self, path: str = None) -> Dict:
        """打开文件夹"""
        return self._computer_tool.open_folder(path)

    def _open_app(self, app_name: str) -> Dict:
        """打开应用程序"""
        return self._computer_tool.open_app(app_name)

    def _get_system_info(self) -> Dict:
        """获取系统信息"""
        return self._computer_tool.get_system_info()

    def _list_browsers(self) -> Dict:
        """列出可用浏览器"""
        return self._computer_tool.list_browsers()

    def _search_web(self, query: str, engine: str = "google") -> Dict:
        """网页搜索"""
        return self._computer_tool.search_web(query, engine)

    def _get_clipboard(self) -> Dict:
        """获取剪贴板"""
        return self._computer_tool.get_clipboard()

    def _set_clipboard(self, content: str) -> Dict:
        """设置剪贴板"""
        return self._computer_tool.set_clipboard(content)

    def get_tool_definitions(self, relevant_only: bool = False, query: str = None) -> list:
        """获取工具定义，优化格式以减少token消耗"""
        tool_definitions = []
        
        # 工具定义，更简洁的格式
        tool_info = {
            "read_file": {
                "name": "read_file",
                "description": "读取文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "offset": {"type": "integer", "description": "起始行"},
                        "limit": {"type": "integer", "description": "行数限制"}
                    },
                    "required": ["path"]
                }
            },
            "write_file": {
                "name": "write_file",
                "description": "写入文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "文件内容"}
                    },
                    "required": ["path", "content"]
                }
            },
            "patch": {
                "name": "patch",
                "description": "修改文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "oldString": {"type": "string", "description": "旧内容"},
                        "newString": {"type": "string", "description": "新内容"}
                    },
                    "required": ["path", "oldString", "newString"]
                }
            },
            "grep": {
                "name": "grep",
                "description": "正则搜索文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "正则表达式"},
                        "path": {"type": "string", "description": "搜索路径"},
                        "include": {"type": "string", "description": "文件后缀过滤"}
                    },
                    "required": ["pattern"]
                }
            },
            "glob": {
                "name": "glob",
                "description": "文件路径模式匹配",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "glob模式，如**/*.py"}
                    },
                    "required": ["pattern"]
                }
            },
            "bash": {
                "name": "bash",
                "description": "执行bash命令",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "命令"},
                        "timeout": {"type": "integer", "description": "超时时间"},
                        "workdir": {"type": "string", "description": "工作目录"}
                    },
                    "required": ["command"]
                }
            },
            "search_files": {
                "name": "search_files",
                "description": "搜索文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "搜索模式"},
                        "root_path": {"type": "string", "description": "根路径"}
                    },
                    "required": ["pattern"]
                }
            },
            "memory_save": {
                "name": "memory_save",
                "description": "保存记忆",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "记忆键"},
                        "value": {"type": "string", "description": "记忆值"}
                    },
                    "required": ["key", "value"]
                }
            },
            "memory_recall": {
                "name": "memory_recall",
                "description": "检索记忆",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "检索关键词"}
                    },
                    "required": ["query"]
                }
            },
            "gmail_draft": {
                "name": "gmail_draft",
                "description": "创建Gmail邮件草稿",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "收件人"},
                        "subject": {"type": "string", "description": "主题"},
                        "body": {"type": "string", "description": "正文"},
                        "cc": {"type": "string", "description": "抄送，逗号分隔"},
                        "bcc": {"type": "string", "description": "密送，逗号分隔"}
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            "gmail_send": {
                "name": "gmail_send",
                "description": "发送Gmail邮件（默认需要confirm）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "收件人"},
                        "subject": {"type": "string", "description": "主题"},
                        "body": {"type": "string", "description": "正文"},
                        "cc": {"type": "string", "description": "抄送，逗号分隔"},
                        "bcc": {"type": "string", "description": "密送，逗号分隔"},
                        "confirm": {"type": "boolean", "description": "高风险确认"}
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            "gmail_search": {
                "name": "gmail_search",
                "description": "搜索Gmail邮件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索语句"},
                        "max_results": {"type": "integer", "description": "最大返回条数"}
                    },
                    "required": ["query"]
                }
            },
            "calendar_create_event": {
                "name": "calendar_create_event",
                "description": "创建Google日历事件（默认需要confirm）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "日程标题"},
                        "start_time": {"type": "string", "description": "开始时间，建议ISO8601"},
                        "end_time": {"type": "string", "description": "结束时间，建议ISO8601"},
                        "description": {"type": "string", "description": "描述"},
                        "attendees": {"type": "string", "description": "参会人邮箱，逗号分隔"},
                        "confirm": {"type": "boolean", "description": "高风险确认"}
                    },
                    "required": ["title", "start_time", "end_time"]
                }
            },
            "calendar_list_events": {
                "name": "calendar_list_events",
                "description": "查询Google日历事件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_time": {"type": "string", "description": "开始时间过滤"},
                        "end_time": {"type": "string", "description": "结束时间过滤"},
                        "max_results": {"type": "integer", "description": "最大返回条数"}
                    },
                    "required": []
                }
            },
            "outlook_mail_draft": {
                "name": "outlook_mail_draft",
                "description": "创建Outlook邮件草稿",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "收件人"},
                        "subject": {"type": "string", "description": "主题"},
                        "body": {"type": "string", "description": "正文"},
                        "cc": {"type": "string", "description": "抄送，逗号分隔"},
                        "bcc": {"type": "string", "description": "密送，逗号分隔"}
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            "outlook_mail_send": {
                "name": "outlook_mail_send",
                "description": "发送Outlook邮件（默认需要confirm）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "收件人"},
                        "subject": {"type": "string", "description": "主题"},
                        "body": {"type": "string", "description": "正文"},
                        "cc": {"type": "string", "description": "抄送，逗号分隔"},
                        "bcc": {"type": "string", "description": "密送，逗号分隔"},
                        "confirm": {"type": "boolean", "description": "高风险确认"}
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            "outlook_mail_search": {
                "name": "outlook_mail_search",
                "description": "搜索Outlook邮件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索语句"},
                        "max_results": {"type": "integer", "description": "最大返回条数"}
                    },
                    "required": ["query"]
                }
            },
            "outlook_calendar_create": {
                "name": "outlook_calendar_create",
                "description": "创建Outlook日历事件（默认需要confirm）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "日程标题"},
                        "start_time": {"type": "string", "description": "开始时间"},
                        "end_time": {"type": "string", "description": "结束时间"},
                        "description": {"type": "string", "description": "描述"},
                        "attendees": {"type": "string", "description": "参会人邮箱，逗号分隔"},
                        "confirm": {"type": "boolean", "description": "高风险确认"}
                    },
                    "required": ["title", "start_time", "end_time"]
                }
            },
            "outlook_calendar_list": {
                "name": "outlook_calendar_list",
                "description": "查询Outlook日历事件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_time": {"type": "string", "description": "开始时间过滤"},
                        "end_time": {"type": "string", "description": "结束时间过滤"},
                        "max_results": {"type": "integer", "description": "最大返回条数"}
                    },
                    "required": []
                }
            },
            "feishu_message_send": {
                "name": "feishu_message_send",
                "description": "发送飞书消息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "receive_id": {"type": "string", "description": "接收人标识"},
                        "content": {"type": "string", "description": "消息正文"},
                        "msg_type": {"type": "string", "description": "消息类型，默认text"}
                    },
                    "required": ["receive_id", "content"]
                }
            },
            "dingtalk_message_send": {
                "name": "dingtalk_message_send",
                "description": "发送钉钉机器人消息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "消息正文"},
                        "title": {"type": "string", "description": "Markdown标题，可选"}
                    },
                    "required": ["text"]
                }
            },
            "open_url": {
                "name": "open_url",
                "description": "打开URL链接（可指定浏览器）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "网址URL"},
                        "browser": {"type": "string", "description": "浏览器名称(chrome/edge/firefox)"}
                    },
                    "required": ["url"]
                }
            },
            "open_browser": {
                "name": "open_browser",
                "description": "打开浏览器访问网址",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "网址，默认google.com"},
                        "browser": {"type": "string", "description": "浏览器名称"}
                    },
                    "required": []
                }
            },
            "open_file": {
                "name": "open_file",
                "description": "使用默认应用打开文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"]
                }
            },
            "open_folder": {
                "name": "open_folder",
                "description": "打开文件夹窗口",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件夹路径，默认当前目录"}
                    },
                    "required": []
                }
            },
            "open_app": {
                "name": "open_app",
                "description": "启动应用程序",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "应用名称或路径"}
                    },
                    "required": ["app_name"]
                }
            },
            "get_system_info": {
                "name": "get_system_info",
                "description": "获取电脑系统信息",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            "list_browsers": {
                "name": "list_browsers",
                "description": "列出电脑上可用的浏览器",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            "search_web": {
                "name": "search_web",
                "description": "使用搜索引擎搜索网页",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "engine": {"type": "string", "description": "搜索引擎(google/bing/baidu)"}
                    },
                    "required": ["query"]
                }
            },
            "get_clipboard": {
                "name": "get_clipboard",
                "description": "读取剪贴板内容",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            "set_clipboard": {
                "name": "set_clipboard",
                "description": "写入剪贴板内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "要复制的内容"}
                    },
                    "required": ["content"]
                }
            }
        }
        
        # 只返回相关工具，减少发送的工具数量
        if relevant_only and query:
            # 根据查询内容选择相关工具
            query_lower = query.lower()
            relevant_tools = []
            
            if any(keyword in query_lower for keyword in ["read", "file", "content"]):
                relevant_tools.append("read_file")
            if any(keyword in query_lower for keyword in ["write", "create", "save"]):
                relevant_tools.append("write_file")
            if any(keyword in query_lower for keyword in ["modify", "update", "change"]):
                relevant_tools.append("patch")
            if any(keyword in query_lower for keyword in ["grep", "regex", "正则"]):
                relevant_tools.append("grep")
            if any(keyword in query_lower for keyword in ["glob", "pattern", "通配"]):
                relevant_tools.append("glob")
            if any(keyword in query_lower for keyword in ["run", "execute", "command"]):
                relevant_tools.append("bash")
            if any(keyword in query_lower for keyword in ["search", "find", "locate"]):
                relevant_tools.append("search_files")
            if any(keyword in query_lower for keyword in ["memory", "remember", "recall", "记忆"]):
                relevant_tools.extend(["memory_save", "memory_recall"])
            if any(keyword in query_lower for keyword in ["mail", "gmail", "邮件", "回信", "发信"]):
                relevant_tools.extend(["gmail_draft", "gmail_search", "gmail_send"])
            if any(keyword in query_lower for keyword in ["calendar", "schedule", "meeting", "日程", "会议", "安排"]):
                relevant_tools.extend(["calendar_list_events", "calendar_create_event"])
            if any(keyword in query_lower for keyword in ["outlook", "microsoft", "graph"]):
                relevant_tools.extend([
                    "outlook_mail_draft",
                    "outlook_mail_search",
                    "outlook_mail_send",
                    "outlook_calendar_list",
                    "outlook_calendar_create",
                ])
            if any(keyword in query_lower for keyword in ["飞书", "feishu", "lark"]):
                relevant_tools.append("feishu_message_send")
            if any(keyword in query_lower for keyword in ["钉钉", "dingtalk"]):
                relevant_tools.append("dingtalk_message_send")
            if any(keyword in query_lower for keyword in ["open", "browser", "打开", "浏览器", "url", "网站", "网页"]):
                relevant_tools.extend(["open_url", "open_browser", "list_browsers", "search_web"])
            if any(keyword in query_lower for keyword in ["file", "文件夹", "app", "应用", "程序", "打开文件"]):
                relevant_tools.extend(["open_file", "open_folder", "open_app"])
            if any(keyword in query_lower for keyword in ["system", "系统", "info", "信息", "电脑"]):
                relevant_tools.append("get_system_info")
            if any(keyword in query_lower for keyword in ["clipboard", "剪贴板", "复制", "粘贴"]):
                relevant_tools.extend(["get_clipboard", "set_clipboard"])
            
            # 确保至少有一个工具
            if not relevant_tools:
                relevant_tools = list(tool_info.keys())[:3]  # 最多返回3个工具
            
            for tool_name in relevant_tools:
                if tool_name in tool_info:
                    tool_definitions.append(tool_info[tool_name])
        else:
            # 返回所有工具定义
            tool_definitions = list(tool_info.values())
        
        return tool_definitions
