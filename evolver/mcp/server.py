"""MCPServer - MCP服务器（将Evolver工具暴露为MCP资源）"""

import json
import logging
import sys
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP服务器 - 将Evolver工具暴露给外部MCP客户端"""

    def __init__(self, tool_registry=None):
        self._tool_registry = tool_registry
        self._server_info = {
            "name": "evolver-mcp",
            "version": "0.1.0"
        }
        self._protocol_version = "2024-11-05"

    def set_tool_registry(self, registry):
        self._tool_registry = registry

    def handle_request(self, request: Dict) -> Dict:
        method = request.get("method", "")
        request_id = request.get("id")
        params = request.get("params", {})

        handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "prompts/list": self._handle_prompts_list,
        }

        handler = handlers.get(method)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

        try:
            result = handler(params)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        except Exception as e:
            logger.error(f"MCP handler error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": "Internal error"}
            }

    def _handle_initialize(self, params: Dict) -> Dict:
        return {
            "protocolVersion": self._protocol_version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False}
            },
            "serverInfo": self._server_info
        }

    def _handle_tools_list(self, params: Dict) -> Dict:
        tools = []
        if self._tool_registry:
            tool_defs = self._tool_registry.get_tool_definitions()
            for td in tool_defs:
                func = td.get("function", {})
                tools.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "inputSchema": func.get("parameters", {"type": "object", "properties": {}})
                })
        return {"tools": tools}

    def _handle_tools_call(self, params: Dict) -> Dict:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if not self._tool_registry:
            return {"content": [{"type": "text", "text": "工具注册表未初始化"}], "isError": True}

        result = self._tool_registry.execute_tool(tool_name, arguments)

        if isinstance(result, dict) and result.get("error"):
            return {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "isError": True
            }

        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
            "isError": False
        }

    def _handle_resources_list(self, params: Dict) -> Dict:
        return {"resources": []}

    def _handle_prompts_list(self, params: Dict) -> Dict:
        return {"prompts": []}

    def run_stdio(self):
        logger.info("MCP Server starting in stdio mode...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError:
                error_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }
                sys.stdout.write(json.dumps(error_resp) + "\n")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"MCP Server error: {e}")
