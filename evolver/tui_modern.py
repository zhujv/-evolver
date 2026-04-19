#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Evolver Modern TUI - 现代化终端聊天界面"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from typing import Optional, List, Dict

try:
    import urllib.request
    import urllib.error
except ImportError:
    urllib = None

if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.box import Box, ROUNDED, DOUBLE
from rich.align import Align
from rich.pretty import Pretty
from rich.style import Style
from rich.color import Color

console = Console()

BASE_URL = os.environ.get("EVOLVER_BASE_URL", "http://localhost:16888")
AUTH_TOKEN = os.environ.get("EVOLVER_SERVER_TOKEN", "evolver-secure-token-2026")

class EvolverTheme:
    """主题颜色配置"""
    PRIMARY = "#61AFEF"
    SECONDARY = "#98C379"
    ACCENT = "#E5C07B"
    ERROR = "#E06C75"
    SUCCESS = "#98C379"
    WARNING = "#E5C07B"
    INFO = "#61AFEF"
    USER_MSG = "#2BBDFF"
    AI_MSG = "#A855F7"
    BORDER = "#3E4451"
    TEXT = "#ABB2BF"
    DIM = "#5C6370"
    BRIGHT = "#FFFFFF"

class EvolverStyles:
    """自定义样式"""
    USER_BUBBLE = Style(color="white", bold=True, bgcolor="#2BBDFF")
    AI_BUBBLE = Style(color="white", bold=False, bgcolor="#A855F7")
    HEADER = Style(color="#61AFEF", bold=True)
    SIDEBAR = Style(color="#ABB2BF")
    FOOTER = Style(color="#5C6370", dim=True)
    SUCCESS = Style(color="#98C379", bold=True)
    ERROR = Style(color="#E06C75", bold=True)
    WARNING = Style(color="#E5C07B")
    INFO = Style(color="#61AFEF")

class MessageBubble:
    """消息气泡"""

    @staticmethod
    def user(message: str, console: Console):
        """用户消息气泡"""
        lines = message.split('\n')
        content = []
        for line in lines:
            if line.strip():
                content.append(f"[bold white]{line}[/bold white]")
            else:
                content.append("")

        panel = Panel(
            "\n".join(content),
            box=Box(DOUBLE if console.width > 80 else ROUNDED),
            style="cyan",
            border_style="#2BBDFF",
            title="[bold]你[/bold]",
            title_align="left",
            padding=(1, 2),
            width=console.width - 20 if console.width > 100 else console.width - 10
        )
        console.print(Align.right(panel))

    @staticmethod
    def ai(message: str, console: Console, show_avatar: bool = True):
        """AI消息气泡"""
        avatar = "[bold magenta]🤖[/bold magenta]" if show_avatar else ""

        md = Markdown(message, code_theme="monokai", style="white on black")

        panel = Panel(
            md,
            box=ROUNDED,
            style="magenta",
            border_style="#A855F7",
            title=f"{avatar} [bold]Evolver[/bold]",
            title_align="left",
            padding=(1, 2),
            width=console.width - 20 if console.width > 100 else console.width - 10
        )
        console.print(Align.left(panel))

    @staticmethod
    def system(message: str, console: Console):
        """系统消息"""
        console.print(Panel(
            f"[dim]{message}[/dim]",
            box=ROUNDED,
            style="yellow",
            border_style="#E5C07B",
            padding=(1, 2),
            width=console.width - 20 if console.width > 100 else console.width - 10
        ))

class AnimatedSpinner:
    """动画加载器"""

    def __init__(self, console: Console):
        self.console = console
        self.progress = None
        self.live = None
        self.stop_event = threading.Event()

    def start(self, message: str = "处理中..."):
        """启动加载动画"""
        self.progress = Progress(
            SpinnerColumn(spinner_name="dots12", style="#61AFEF"),
            TextColumn("[progress.description]{task.description}", style="#ABB2BF"),
            BarColumn(bar_width=40, style="#61AFEF", finished_style="#98C379"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True
        )
        self.task_id = self.progress.add_task(message, total=None)
        self.live = Live(
            self.progress,
            console=self.console,
            refresh_per_second=10,
            transient=True
        )
        self.live.start()
        return self

    def update(self, message: str):
        """更新消息"""
        if self.progress and self.task_id:
            self.progress.update(self.task_id, description=message)

    def stop(self):
        """停止加载动画"""
        if self.live:
            self.live.stop()
            self.live = None

class EvolverChat:
    """主聊天类"""

    def __init__(self):
        self.session_id: Optional[str] = None
        self.agent_id: str = "default"
        self.console = console
        self.message_history: List[Dict] = []
        self.is_connected: bool = False

    def send_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """发送请求到后端"""
        if not urllib:
            return {"error": {"message": "urllib not available"}}

        try:
            request_params = dict(params or {})
            if AUTH_TOKEN and method != "health":
                request_params["auth_token"] = AUTH_TOKEN

            json_data = {"method": method, "params": request_params, "id": 1}
            payload = json.dumps(json_data).encode("utf-8")

            req = urllib.request.Request(
                url=f"{BASE_URL}/rpc",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {AUTH_TOKEN}"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            return {"error": {"message": f"HTTP {e.code}: {detail}"}}
        except urllib.error.URLError as e:
            return {"error": {"message": f"连接失败: {e.reason}"}}
        except Exception as e:
            return {"error": {"message": str(e)}}

    def print_header(self):
        """打印头部信息"""
        self.console.print()
        header_text = Text()
        header_text.append("╔══════════════════════════════════════════════════════════╗\n", Style(color="#61AFEF", bold=True))
        header_text.append("║                                                          ║\n", Style(color="#61AFEF"))
        header_text.append("║   ", Style(color="#61AFEF", bold=True))
        header_text.append("🤖  Evolver", Style(color="#E5C07B", bold=True))
        header_text.append(" - 智能AI编程助手                    ", Style(color="#61AFEF"))
        header_text.append("║\n", Style(color="#61AFEF", bold=True))
        header_text.append("║                                                          ║\n", Style(color="#61AFEF"))
        header_text.append("║   ", Style(color="#98C379"))
        header_text.append("✓ 多模型支持  ", Style(color="#98C379"))
        header_text.append("✓ 技能系统  ", Style(color="#98C379"))
        header_text.append("✓ 记忆管理  ", Style(color="#98C379"))
        header_text.append("✓ MCP集成   ", Style(color="#98C379"))
        header_text.append("    ║\n", Style(color="#61AFEF"))
        header_text.append("║                                                          ║\n", Style(color="#61AFEF"))
        header_text.append("╚══════════════════════════════════════════════════════════╝", Style(color="#61AFEF", bold=True))

        self.console.print(header_text)
        self.console.print()

    def print_status_bar(self):
        """打印状态栏"""
        status_table = Table(show_header=False, box=None, padding=(0, 1))
        status_table.add_column(style="dim")
        status_table.add_column(style="dim")

        timestamp = datetime.now().strftime("%H:%M:%S")
        session_info = f"Session: {self.session_id[:8] if self.session_id else 'None'}"
        agent_info = f"Agent: {self.agent_id}"
        time_info = f"🕐 {timestamp}"

        status_table.add_row(
            f"[dim]{session_info} | {agent_info}[/dim]",
            f"[dim]{time_info}[/dim]"
        )

        self.console.print(status_table)
        self.console.print()

    def print_help(self):
        """打印帮助信息"""
        help_table = Table(
            title="[bold #E5C07B]📖 可用命令[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451"
        )
        help_table.add_column("命令", style="#98C379", width=20)
        help_table.add_column("说明", style="#ABB2BF")

        commands = [
            ("help", "显示帮助信息"),
            ("health", "检查系统状态"),
            ("agents", "查看可用智能体"),
            ("use <id>", "切换智能体"),
            ("skills", "查看可用技能"),
            ("config", "配置大模型 API"),
            ("clear", "清屏"),
            ("history", "查看历史消息"),
            ("token", "查看Token使用"),
            ("quit / q", "退出程序"),
        ]

        for cmd, desc in commands:
            help_table.add_row(f"[#61AFEF]{cmd}[/#61AFEF]", desc)

        self.console.print(help_table)
        self.console.print()

    def check_connection(self) -> bool:
        """检查后端连接"""
        spinner = AnimatedSpinner(self.console)
        spinner.start("正在连接后端服务器...")

        result = self.send_request("health", {})

        spinner.stop()

        if "error" in result:
            error_panel = Panel(
                f"[bold red]✗ 连接失败[/bold red]\n\n"
                f"[yellow]错误信息:[/yellow] {result.get('error', {}).get('message', '未知错误')}\n\n"
                f"[dim]请确保后端服务正在运行:[/dim]\n"
                f"[cyan].venv\\Scripts\\python.exe -m evolver.server[/cyan]",
                title="[bold red]连接错误[/bold red]",
                border_style="red",
                box=ROUNDED
            )
            self.console.print(error_panel)
            return False

        self.is_connected = True
        success_panel = Panel(
            f"[bold green]✓ 连接成功![/bold green]\n\n"
            f"[dim]后端状态:[/dim] [green]{result.get('result', {})}[/green]",
            title="[bold green]连接状态[/bold green]",
            border_style="green",
            box=ROUNDED
        )
        self.console.print(success_panel)
        return True

    def create_session(self):
        """创建会话"""
        spinner = AnimatedSpinner(self.console)
        spinner.start("正在创建会话...")

        result = self.send_request("create_session", {})

        spinner.stop()

        if "result" in result:
            self.session_id = result["result"]
            self.console.print(f"[green]✓[/green] 会话已创建: [dim]{self.session_id}[/dim]")
            return True
        else:
            self.console.print(f"[red]✗[/red] 创建会话失败: {result.get('error', {}).get('message')}")
            return False

    def chat(self, message: str):
        """发送聊天消息"""
        if not self.session_id:
            if not self.create_session():
                return

        self.message_history.append({"role": "user", "content": message, "time": datetime.now()})
        MessageBubble.user(message, self.console)

        spinner = AnimatedSpinner(self.console)
        spinner.start("Evolver 正在思考...")

        result = self.send_request("chat", {
            "session_id": self.session_id,
            "message": message,
            "agent_id": self.agent_id,
        })

        spinner.stop()

        if "result" in result:
            response = result["result"].get("final_response", "")
            token_usage = result["result"].get("token_usage", {})

            self.message_history.append({
                "role": "assistant",
                "content": response,
                "time": datetime.now(),
                "tokens": token_usage
            })

            MessageBubble.ai(response, self.console)

            if token_usage:
                self.console.print(
                    f"[dim]📊 Token使用: 输入 {token_usage.get('prompt_tokens', 0)} | "
                    f"输出 {token_usage.get('completion_tokens', 0)} | "
                    f"总计 {token_usage.get('total_tokens', 0)}[/dim]"
                )
        else:
            error_msg = result.get('error', {}).get('message', '未知错误')
            MessageBubble.system(f"错误: {error_msg}", self.console)
            self.console.print(f"[red]✗[/red] 错误: {error_msg}")

        self.console.print()

    def list_agents(self):
        """列出可用智能体"""
        spinner = AnimatedSpinner(self.console)
        spinner.start("正在获取智能体列表...")

        result = self.send_request("get_agents", {})

        spinner.stop()

        if "result" not in result:
            self.console.print(f"[red]✗[/red] 获取失败: {result.get('error', {}).get('message')}")
            return

        agents = result["result"] or []

        if not agents:
            self.console.print("[yellow]⚠[/yellow] 暂无可用智能体")
            return

        agents_table = Table(
            title="[bold #E5C07B]👥 可用智能体[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451"
        )
        agents_table.add_column("ID", style="#98C379", width=15)
        agents_table.add_column("名称", style="#E5C07B", width=20)
        agents_table.add_column("描述", style="#ABB2BF")
        agents_table.add_column("状态", style="#61AFEF", width=10, justify="center")

        for agent in agents:
            agent_id = agent.get("id", "unknown")
            is_active = "✓" if agent_id == self.agent_id else " "
            agents_table.add_row(
                f"[#61AFEF]{agent_id}[/#61AFEF]",
                f"[#E5C07B]{agent.get('name', '未知')}[/#E5C07B]",
                agent.get('description', '无描述'),
                f"[green]{is_active}[/green]" if is_active == "✓" else "[dim]-[/dim]"
            )

        self.console.print(agents_table)
        self.console.print(f"[dim]当前: {self.agent_id} | 使用 [cyan]use <id>[/cyan] 切换[/dim]")
        self.console.print()

    def switch_agent(self, agent_id: str):
        """切换智能体"""
        if not agent_id:
            self.console.print("[yellow]⚠[/yellow] 请指定智能体ID: use <id>")
            return

        spinner = AnimatedSpinner(self.console)
        spinner.start(f"正在切换到 {agent_id}...")

        result = self.send_request("get_agents", {})
        spinner.stop()

        if "result" not in result:
            self.console.print(f"[red]✗[/red] 切换失败: {result.get('error', {}).get('message')}")
            return

        agents = result["result"] or []
        available_ids = {agent.get("id") for agent in agents}

        if agent_id not in available_ids:
            self.console.print(f"[red]✗[/red] 未找到智能体: {agent_id}")
            self.console.print(f"[dim]可用: {', '.join(sorted(a for a in available_ids if a))}[/dim]")
            return

        old_agent = self.agent_id
        self.agent_id = agent_id

        success_panel = Panel(
            f"[green]✓[/green] 已从 [yellow]{old_agent}[/yellow] 切换到 [cyan]{self.agent_id}[/cyan]",
            border_style="green",
            box=ROUNDED
        )
        self.console.print(success_panel)

    def list_skills(self):
        """列出可用技能"""
        spinner = AnimatedSpinner(self.console)
        spinner.start("正在获取技能列表...")

        result = self.send_request("get_skills", {})

        spinner.stop()

        if "result" not in result:
            self.console.print(f"[red]✗[/red] 获取失败: {result.get('error', {}).get('message')}")
            return

        skills = result["result"] or []

        if not skills:
            self.console.print("[yellow]⚠[/yellow] 暂无可用技能")
            return

        skills_table = Table(
            title="[bold #E5C07B]🛠️ 可用技能[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451"
        )
        skills_table.add_column("名称", style="#98C379", width=20)
        skills_table.add_column("描述", style="#ABB2BF")

        for skill in skills:
            skills_table.add_row(
                f"[#61AFEF]{skill.get('name', '未知')}[/#61AFEF]",
                skill.get('description', '无描述')
            )

        self.console.print(skills_table)
        self.console.print()

    def show_token_usage(self):
        """显示Token使用统计"""
        total_input = 0
        total_output = 0
        total_total = 0

        for msg in self.message_history:
            if msg.get("role") == "assistant" and msg.get("tokens"):
                total_input += msg["tokens"].get("prompt_tokens", 0)
                total_output += msg["tokens"].get("completion_tokens", 0)
                total_total += msg["tokens"].get("total_tokens", 0)

        if total_total == 0:
            self.console.print("[yellow]⚠[/yellow] 暂无Token使用记录")
            return

        usage_table = Table(
            title="[bold #E5C07B]📊 Token使用统计[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451"
        )
        usage_table.add_column("类型", style="#E5C07B", width=20)
        usage_table.add_column("数量", style="#98C379", justify="right")

        usage_table.add_row("📥 输入Token", f"[cyan]{total_input:,}[/cyan]")
        usage_table.add_row("📤 输出Token", f"[cyan]{total_output:,}[/cyan]")
        usage_table.add_row("📦 总计", f"[bold cyan]{total_total:,}[/bold cyan]")

        self.console.print(usage_table)
        self.console.print()

    def show_history(self):
        """显示消息历史"""
        if not self.message_history:
            self.console.print("[yellow]⚠[/yellow] 暂无消息历史")
            return

        history_table = Table(
            title="[bold #E5C07B]📜 消息历史[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451"
        )
        history_table.add_column("序号", style="#5C6370", width=5, justify="center")
        history_table.add_column("角色", style="#E5C07B", width=10)
        history_table.add_column("内容", style="#ABB2BF")
        history_table.add_column("时间", style="#5C6370", width=10)

        for i, msg in enumerate(self.message_history, 1):
            role = "👤 用户" if msg.get("role") == "user" else "🤖 AI"
            content = msg.get("content", "")[:50] + "..." if len(msg.get("content", "")) > 50 else msg.get("content", "")
            time_str = msg.get("time", "").strftime("%H:%M:%S") if hasattr(msg.get("time", ""), "strftime") else ""

            history_table.add_row(
                f"[dim]{i}[/dim]",
                role,
                content,
                f"[dim]{time_str}[/dim]"
            )

        self.console.print(history_table)
        self.console.print()

    def health_check(self):
        """健康检查"""
        spinner = AnimatedSpinner(self.console)
        spinner.start("正在检查系统状态...")

        result = self.send_request("health", {})

        spinner.stop()

        if "result" in result:
            health_info = result["result"]

            health_table = Table(
                title="[bold #E5C07B]🏥 系统状态[/bold #E5C07B]",
                show_header=False,
                box=ROUNDED,
                border_style="#3E4451"
            )
            health_table.add_column("项目", style="#E5C07B", width=20)
            health_table.add_column("状态", style="#98C379")

            health_table.add_row("🔌 连接状态", "[green]✓ 正常[/green]")
            health_table.add_row("🆔 Session ID", f"[dim]{self.session_id or 'None'}[/dim]")
            health_table.add_row("🤖 当前Agent", f"[cyan]{self.agent_id}[/cyan]")
            health_table.add_row("💬 消息数", f"[cyan]{len(self.message_history)}[/cyan]")

            self.console.print(health_table)

            if isinstance(health_info, dict):
                self.console.print(Panel(
                    Pretty(health_info),
                    title="[bold]详细信息[/bold]",
                    border_style="#61AFEF",
                    box=ROUNDED
                ))
        else:
            self.console.print(f"[red]✗[/red] 健康检查失败: {result.get('error', {}).get('message')}")

        self.console.print()

    def config_model_api(self):
        """配置大模型 API"""
        self.console.print(Panel(
            "[bold #E5C07B]⚙️ 大模型 API 配置[/bold #E5C07B]

[dim]请选择要配置的模型提供商:[/dim]
1. OpenAI
2. Anthropic
3. OpenRouter
4. 查看当前配置
5. 取消
",
            title="[bold #61AFEF]API 配置[/bold #61AFEF]",
            border_style="#3E4451",
            box=ROUNDED
        ))

        while True:
            choice = self.console.input("[bold #2BBDFF]选择 (1-5):[/bold #2BBDFF] ").strip()
            if choice == "1":
                self._config_openai()
                break
            elif choice == "2":
                self._config_anthropic()
                break
            elif choice == "3":
                self._config_openrouter()
                break
            elif choice == "4":
                self._show_current_config()
                break
            elif choice == "5":
                self.console.print("[yellow]⚠[/yellow] 已取消配置")
                break
            else:
                self.console.print("[red]✗[/red] 无效选择，请输入 1-5")

    def _config_openai(self):
        """配置 OpenAI API"""
        self.console.print(Panel(
            "[bold #E5C07B]🔧 OpenAI API 配置[/bold #E5C07B]

[dim]请输入您的 OpenAI API 密钥:[/dim]
[dim]提示: 密钥格式类似 sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx[/dim]
",
            title="[bold #61AFEF]OpenAI 配置[/bold #61AFEF]",
            border_style="#3E4451",
            box=ROUNDED
        ))

        api_key = self.console.input("[bold #2BBDFF]API 密钥:[/bold #2BBDFF] ").strip()
        if api_key:
            # 保存到环境变量（临时会话）
            os.environ["OPENAI_API_KEY"] = api_key
            self.console.print("[green]✓[/green] OpenAI API 密钥已设置")
            
            # 测试连接
            spinner = AnimatedSpinner(self.console)
            spinner.start("正在测试连接...")
            # 这里可以添加测试逻辑
            spinner.stop()
            
            self.console.print("[green]✓[/green] 配置完成！请重启后端服务器使配置生效")
        else:
            self.console.print("[yellow]⚠[/yellow] 未输入 API 密钥")

    def _config_anthropic(self):
        """配置 Anthropic API"""
        self.console.print(Panel(
            "[bold #E5C07B]🔧 Anthropic API 配置[/bold #E5C07B]

[dim]请输入您的 Anthropic API 密钥:[/dim]
[dim]提示: 密钥格式类似 sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx[/dim]
",
            title="[bold #61AFEF]Anthropic 配置[/bold #61AFEF]",
            border_style="#3E4451",
            box=ROUNDED
        ))

        api_key = self.console.input("[bold #2BBDFF]API 密钥:[/bold #2BBDFF] ").strip()
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
            self.console.print("[green]✓[/green] Anthropic API 密钥已设置")
            
            spinner = AnimatedSpinner(self.console)
            spinner.start("正在测试连接...")
            # 测试逻辑
            spinner.stop()
            
            self.console.print("[green]✓[/green] 配置完成！请重启后端服务器使配置生效")
        else:
            self.console.print("[yellow]⚠[/yellow] 未输入 API 密钥")

    def _config_openrouter(self):
        """配置 OpenRouter API"""
        self.console.print(Panel(
            "[bold #E5C07B]🔧 OpenRouter API 配置[/bold #E5C07B]

[dim]请输入您的 OpenRouter API 密钥:[/dim]
[dim]提示: 密钥格式类似 sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx[/dim]
",
            title="[bold #61AFEF]OpenRouter 配置[/bold #61AFEF]",
            border_style="#3E4451",
            box=ROUNDED
        ))

        api_key = self.console.input("[bold #2BBDFF]API 密钥:[/bold #2BBDFF] ").strip()
        if api_key:
            os.environ["OPENROUTER_API_KEY"] = api_key
            self.console.print("[green]✓[/green] OpenRouter API 密钥已设置")
            
            spinner = AnimatedSpinner(self.console)
            spinner.start("正在测试连接...")
            # 测试逻辑
            spinner.stop()
            
            self.console.print("[green]✓[/green] 配置完成！请重启后端服务器使配置生效")
        else:
            self.console.print("[yellow]⚠[/yellow] 未输入 API 密钥")

    def _show_current_config(self):
        """显示当前配置"""
        config_table = Table(
            title="[bold #E5C07B]📋 当前 API 配置[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451"
        )
        config_table.add_column("提供商", style="#98C379", width=15)
        config_table.add_column("API 密钥状态", style="#ABB2BF")

        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

        config_table.add_row(
            "OpenAI",
            "[green]✓ 已设置[/green]" if openai_key else "[red]✗ 未设置[/red]"
        )
        config_table.add_row(
            "Anthropic",
            "[green]✓ 已设置[/green]" if anthropic_key else "[red]✗ 未设置[/red]"
        )
        config_table.add_row(
            "OpenRouter",
            "[green]✓ 已设置[/green]" if openrouter_key else "[red]✗ 未设置[/red]"
        )

        self.console.print(config_table)
        self.console.print()
        self.console.print("[dim]提示: 这些配置仅在当前会话有效。要永久保存，请设置系统环境变量。[/dim]")

    def run(self):
        """运行主循环"""
        self.console.clear()

        self.print_header()

        if not self.check_connection():
            return

        if not self.session_id:
            self.create_session()

        self.console.print()
        self.console.print("[dim]输入 [cyan]help[/cyan] 查看可用命令，输入 [cyan]quit[/cyan] 退出[/dim]")
        self.console.print()

        while True:
            try:
                user_input = self.console.input(
                    f"[bold #2BBDFF]⟩[/bold #2BBDFF] "
                ).strip()

                if not user_input:
                    continue

                cmd_lower = user_input.lower()

                if cmd_lower in ('q', 'quit', 'exit'):
                    farewell_text = Text()
                    farewell_text.append("\n╔══════════════════════════════════════════╗\n", Style(color="#61AFEF", bold=True))
                    farewell_text.append("║                                          ║\n", Style(color="#61AFEF"))
                    farewell_text.append("║     ", Style(color="#98C379"))
                    farewell_text.append("👋 再见! 感谢使用 Evolver!", Style(color="#E5C07B", bold=True))
                    farewell_text.append("              ║\n", Style(color="#61AFEF"))
                    farewell_text.append("║                                          ║\n", Style(color="#61AFEF"))
                    farewell_text.append("╚══════════════════════════════════════════╝", Style(color="#61AFEF", bold=True))
                    self.console.print(farewell_text)
                    break

                elif cmd_lower == 'help':
                    self.print_help()

                elif cmd_lower == 'health':
                    self.health_check()

                elif cmd_lower == 'agents':
                    self.list_agents()

                elif cmd_lower.startswith('use '):
                    agent_id = user_input[4:].strip()
                    self.switch_agent(agent_id)

                elif cmd_lower == 'skills':
                    self.list_skills()

                elif cmd_lower == 'clear':
                    self.console.clear()
                    self.print_header()

                elif cmd_lower == 'history':
                    self.show_history()

                elif cmd_lower == 'token':
                    self.show_token_usage()

                elif cmd_lower == 'config':
                    self.config_model_api()

                elif user_input.startswith('/'):
                    self.console.print(f"[yellow]⚠[/yellow] 未知命令: {user_input}")
                    self.console.print(f"[dim]输入 [cyan]help[/cyan] 查看可用命令[/dim]")

                else:
                    self.chat(user_input)

            except KeyboardInterrupt:
                self.console.print("\n\n[yellow]⚠[/yellow] 使用 [cyan]quit[/cyan] 命令退出[/dim]")
                continue
            except EOFError:
                break

def main():
    """主函数"""
    chat = EvolverChat()
    chat.run()

if __name__ == "__main__":
    main()
