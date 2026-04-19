"""MCPTools - MCP工具适配器（将MCP工具注册到ToolRegistry）"""

import logging
from typing import Dict, List
from ..mcp.client import MCPClient

logger = logging.getLogger(__name__)


class MCPTools:
    """MCP工具适配器 - 将MCP发现的外部工具注册到Evolver工具系统"""

    def __init__(self, mcp_client: MCPClient = None):
        self._client = mcp_client or MCPClient()
        self._registered_tools: Dict[str, Dict] = {}

    def connect_server(self, server_id: str, command: str, args: List[str] = None, env: Dict = None) -> Dict:
        result = self._client.connect_stdio(server_id, command, args, env)
        if result.get("success"):
            self._register_discovered_tools(server_id)
        return result

    def disconnect_server(self, server_id: str) -> bool:
        for tool_name in list(self._registered_tools.keys()):
            if self._registered_tools[tool_name].get("server_id") == server_id:
                del self._registered_tools[tool_name]
        return self._client.disconnect(server_id)

    def get_tool_definitions(self) -> List[Dict]:
        definitions = []
        for tool_name, tool_info in self._registered_tools.items():
            definitions.append({
                "type": "function",
                "function": {
                    "name": f"mcp_{tool_name}",
                    "description": f"[MCP:{tool_info.get('server_id', '')}] {tool_info.get('description', '')}",
                    "parameters": tool_info.get("inputSchema", {
                        "type": "object",
                        "properties": {}
                    })
                }
            })
        return definitions

    def execute_mcp_tool(self, tool_name: str, parameters: Dict) -> Dict:
        tool_info = self._registered_tools.get(tool_name)
        if not tool_info:
            return {"error": f"MCP工具 {tool_name} 不存在"}

        server_id = tool_info.get("server_id", "")
        return self._client.call_tool(server_id, tool_name, parameters)

    def list_mcp_tools(self) -> List[Dict]:
        return list(self._registered_tools.values())

    def list_servers(self) -> List[Dict]:
        return self._client.list_servers()

    def _register_discovered_tools(self, server_id: str):
        tools = self._client.list_tools(server_id)
        for tool in tools:
            tool_name = tool.get("name", "")
            if tool_name:
                self._registered_tools[tool_name] = {
                    "name": tool_name,
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("inputSchema", {}),
                    "server_id": server_id,
                    "source": "mcp"
                }
                logger.info(f"Registered MCP tool: {tool_name} from {server_id}")
