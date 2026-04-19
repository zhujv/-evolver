"""CLI界面"""

import cmd
import json
import os
import urllib.request
import urllib.error


class EvolverCLI(cmd.Cmd):
    """Evolver命令行界面"""

    prompt = "evolver> "
    intro = "欢迎使用Evolver CLI！输入help查看可用命令。"

    def __init__(self):
        super().__init__()
        self.session_id = None
        self.base_url = "http://localhost:16888"
        self.auth_token = os.environ.get("EVOLVER_SERVER_TOKEN", "").strip()
        if not self.auth_token:
            self.auth_token = "evolver-secure-token-2026"
        self.agent_id = "default"

    def _send_request(self, method, params):
        """发送请求"""
        try:
            request_params = dict(params or {})
            if self.auth_token and method != "health":
                request_params["auth_token"] = self.auth_token

            json_data = {"method": method, "params": request_params, "id": 1}
            payload = json.dumps(json_data).encode("utf-8")
            req = urllib.request.Request(
                url=f"{self.base_url}/rpc",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    **({"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}),
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            return {"error": {"message": f"HTTP {e.code}: {detail}"}}
        except urllib.error.URLError as e:
            return {"error": {"message": f"连接失败: {e.reason}"}}
        except Exception as e:
            return {"error": {"message": str(e)}}

    def do_create_session(self, arg):
        """创建新会话"""
        result = self._send_request("create_session", {})
        if "result" in result:
            self.session_id = result["result"]
            print(f"创建会话成功，会话ID: {self.session_id}")
        else:
            print(f"创建会话失败: {result.get('error', {}).get('message', '未知错误')}")

    def do_chat(self, arg):
        """发送消息"""
        if not self.session_id:
            print("请先创建会话")
            return
        
        result = self._send_request("chat", {
            "session_id": self.session_id,
            "message": arg,
            "agent_id": self.agent_id,
        })
        if "result" in result:
            chat_result = result["result"]
            print(f"AI响应({self.agent_id}):")
            print(chat_result.get("final_response", ""))
        else:
            print(f"聊天失败: {result.get('error', {}).get('message', '未知错误')}")

    def do_agents(self, arg):
        """列出内置智能体画像"""
        result = self._send_request("get_agents", {})
        if "result" not in result:
            print(f"获取画像失败: {result.get('error', {}).get('message', '未知错误')}")
            return
        agents = result["result"] or []
        if not agents:
            print("暂无可用画像")
            return
        print("可用画像:")
        for agent in agents:
            aid = agent.get("id", "unknown")
            mark = "*" if aid == self.agent_id else " "
            print(f"{mark} {aid}: {agent.get('name', '未知')} - {agent.get('description', '无描述')}")

    def do_use_agent(self, arg):
        """切换当前会话使用的智能体画像: use_agent <agent_id>"""
        target = (arg or "").strip()
        if not target:
            print("用法: use_agent <agent_id>")
            return
        result = self._send_request("get_agents", {})
        if "result" not in result:
            print(f"切换失败: {result.get('error', {}).get('message', '未知错误')}")
            return
        agents = result["result"] or []
        available_ids = {agent.get("id") for agent in agents}
        if target not in available_ids:
            print(f"未找到画像: {target}")
            print("可用画像ID: " + ", ".join(sorted(a for a in available_ids if a)))
            return
        self.agent_id = target
        print(f"已切换为画像: {self.agent_id}")

    def do_skills(self, arg):
        """列出所有技能"""
        result = self._send_request("get_skills", {})
        if "result" in result:
            skills = result["result"]
            if skills:
                for skill in skills:
                    print(f"- {skill.get('name', '未知')}: {skill.get('description', '无描述')}")
            else:
                print("暂无技能")
        else:
            print(f"获取技能失败: {result.get('error', {}).get('message', '未知错误')}")

    def do_health(self, arg):
        """健康检查"""
        result = self._send_request("health", {})
        if "result" in result:
            health = result["result"]
            print("健康状态:")
            print(str(health))
        else:
            print(f"健康检查失败: {result.get('error', {}).get('message', '未知错误')}")

    def do_exit(self, arg):
        """退出"""
        print("再见！")
        return True

    def do_quit(self, arg):
        """退出"""
        return self.do_exit(arg)
    
    def do_help(self, arg):
        """显示帮助"""
        print("""
Evolver CLI 可用命令:
  create_session   - 创建新会话
  chat <消息>      - 发送消息与AI对话
  agents           - 列出可用智能体画像
  use_agent <ID>  - 切换智能体画像
  skills           - 列出所有技能
  health           - 健康检查
  exit/quit        - 退出
        """)


def main():
    """主函数"""
    cli = EvolverCLI()
    cli.cmdloop()


if __name__ == '__main__':
    main()
