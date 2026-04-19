"""MCPClient - MCP客户端（连接外部MCP服务器发现和调用工具）"""

import json
import logging
import subprocess
import threading
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP客户端 - 连接外部MCP服务器，发现并调用工具"""

    def __init__(self):
        self._connections: Dict[str, Dict] = {}
        self._discovered_tools: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def connect_stdio(self, server_id: str, command: str, args: List[str] = None, env: Dict = None) -> Dict:
        try:
            process_env = None
            if env:
                import os
                process_env = {**os.environ, **env}

            process = subprocess.Popen(
                [command, *(args or [])],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=process_env,
                bufsize=0
            )

            conn = {
                "server_id": server_id,
                "type": "stdio",
                "process": process,
                "command": command,
                "args": args or [],
            }
            self._connections[server_id] = conn

            init_result = self._send_request(server_id, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "evolver", "version": "0.1.0"}
            })

            if init_result and not init_result.get("error"):
                self._discover_tools(server_id)
                return {"success": True, "server_id": server_id, "tools": len(self._discovered_tools.get(server_id, {}))}
            else:
                logger.warning(f"MCP server {server_id} init failed: {init_result}")
                return {"success": False, "error": "初始化失败", "details": str(init_result)}

        except Exception as e:
            logger.error(f"MCP connect failed: {e}")
            return {"success": False, "error": str(e)}

    def disconnect(self, server_id: str) -> bool:
        with self._lock:
            conn = self._connections.pop(server_id, None)
            if conn and conn.get("process"):
                try:
                    conn["process"].terminate()
                    conn["process"].wait(timeout=5)
                except Exception:
                    try:
                        conn["process"].kill()
                    except Exception:
                        pass
            self._discovered_tools.pop(server_id, None)
            return True

    def list_tools(self, server_id: str = None) -> List[Dict]:
        if server_id:
            tools = self._discovered_tools.get(server_id, {})
            return list(tools.values())
        all_tools = []
        for sid, tools in self._discovered_tools.items():
            for tool in tools.values():
                tool_copy = dict(tool)
                tool_copy["server_id"] = sid
                all_tools.append(tool_copy)
        return all_tools

    def call_tool(self, server_id: str, tool_name: str, arguments: Dict = None) -> Dict:
        if server_id not in self._connections:
            return {"error": f"MCP服务器 {server_id} 未连接"}

        result = self._send_request(server_id, "tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })

        if result and not result.get("error"):
            return result.get("result", result)
        return result or {"error": "调用失败"}

    def list_servers(self) -> List[Dict]:
        servers = []
        for sid, conn in self._connections.items():
            servers.append({
                "server_id": sid,
                "type": conn.get("type", "unknown"),
                "command": conn.get("command", ""),
                "tools_count": len(self._discovered_tools.get(sid, {})),
                "connected": conn.get("process") is not None and conn["process"].poll() is None
            })
        return servers

    def _discover_tools(self, server_id: str):
        result = self._send_request(server_id, "tools/list", {})
        if result and not result.get("error"):
            tools = result.get("tools", [])
            with self._lock:
                self._discovered_tools[server_id] = {}
                for tool in tools:
                    tool_name = tool.get("name", "")
                    self._discovered_tools[server_id][tool_name] = {
                        "name": tool_name,
                        "description": tool.get("description", ""),
                        "inputSchema": tool.get("inputSchema", {}),
                        "source": "mcp",
                        "server_id": server_id
                    }
            logger.info(f"Discovered {len(tools)} tools from MCP server {server_id}")

    def _send_request(self, server_id: str, method: str, params: Dict = None) -> Optional[Dict]:
        conn = self._connections.get(server_id)
        if not conn or not conn.get("process"):
            return {"error": "连接不存在"}

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params:
            request["params"] = params

        try:
            message = json.dumps(request) + "\n"
            conn["process"].stdin.write(message.encode())
            conn["process"].stdin.flush()

            response_line = conn["process"].stdout.readline()
            if response_line:
                return json.loads(response_line.decode())
            return {"error": "无响应"}
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            return {"error": str(e)}
