#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Evolver UI Components - 高级UI组件库"""

import os
import sys
import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Callable
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.box import Box, ROUNDED, DOUBLE, HEAVY, ASCII2
from rich.align import Align
from rich.style import Style
from rich.color import Color
from rich.rule import Rule

if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass


class EvolverTheme:
    """主题颜色配置 - One Dark配色方案"""

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

    RAINBOW = [
        "#E06C75",
        "#E5C07B",
        "#98C379",
        "#61AFEF",
        "#A855F7",
    ]


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


class MessageType(Enum):
    """消息类型枚举"""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"


class MessageBubble:
    """消息气泡组件"""

    @staticmethod
    def user(message: str, console: Console, max_width: Optional[int] = None):
        """用户消息气泡"""
        if not message.strip():
            return

        lines = message.split('\n')
        content = []
        for line in lines:
            if line.strip():
                content.append(f"[bold white]{line}[/bold white]")
            else:
                content.append("")

        width = max_width or (console.width - 20 if console.width > 100 else console.width - 10)

        panel = Panel(
            "\n".join(content),
            box=ROUNDED,
            style="cyan",
            border_style="#2BBDFF",
            title="[bold]👤 你[/bold]",
            title_align="left",
            padding=(1, 2),
            width=width
        )
        console.print(Align.right(panel))

    @staticmethod
    def ai(message: str, console: Console, show_avatar: bool = True, max_width: Optional[int] = None):
        """AI消息气泡"""
        avatar = "[bold magenta]🤖[/bold magenta]" if show_avatar else ""

        try:
            md = Markdown(message, code_theme="monokai", style="white on black")
            content = md
        except:
            content = message

        width = max_width or (console.width - 20 if console.width > 100 else console.width - 10)

        panel = Panel(
            content,
            box=ROUNDED,
            style="magenta",
            border_style="#A855F7",
            title=f"{avatar} [bold]Evolver AI[/bold]",
            title_align="left",
            padding=(1, 2),
            width=width
        )
        console.print(Align.left(panel))

    @staticmethod
    def system(message: str, console: Console, max_width: Optional[int] = None):
        """系统消息"""
        width = max_width or (console.width - 20 if console.width > 100 else console.width - 10)

        panel = Panel(
            f"[dim]{message}[/dim]",
            box=ROUNDED,
            style="yellow",
            border_style="#E5C07B",
            padding=(1, 2),
            width=width
        )
        console.print(Align.center(panel))

    @staticmethod
    def error(message: str, console: Console, max_width: Optional[int] = None):
        """错误消息"""
        width = max_width or (console.width - 20 if console.width > 100 else console.width - 10)

        panel = Panel(
            f"[bold red]✗[/bold red] {message}",
            box=ROUNDED,
            style="red",
            border_style="#E06C75",
            padding=(1, 2),
            width=width
        )
        console.print(Align.center(panel))

    @staticmethod
    def success(message: str, console: Console, max_width: Optional[int] = None):
        """成功消息"""
        width = max_width or (console.width - 20 if console.width > 100 else console.width - 10)

        panel = Panel(
            f"[bold green]✓[/bold green] {message}",
            box=ROUNDED,
            style="green",
            border_style="#98C379",
            padding=(1, 2),
            width=width
        )
        console.print(Align.center(panel))

    @staticmethod
    def code(message: str, language: str = "python", console: Console = None):
        """代码消息"""
        if console is None:
            console = Console()

        syntax = Syntax(message, language, theme="monokai", line_numbers=True)
        panel = Panel(
            syntax,
            box=ROUNDED,
            style="cyan",
            border_style="#61AFEF",
            title=f"[bold]📝 {language.upper()}[/bold]",
            title_align="left",
            padding=(1, 2)
        )
        console.print(panel)

    @staticmethod
    def stream(message: str, console: Console):
        """流式消息（用于打字效果）"""
        console.print(f"[magenta]{message}[/magenta]", end="", flush=True)


class AnimatedSpinner:
    """动画加载器组件"""

    SPINNERS = [
        "dots12", "dots13", "dots14", "dots15", "dots16",
        "simpleDots", "arrow", "toggle", "hamburger"
    ]

    def __init__(self, console: Console):
        self.console = console
        self.progress = None
        self.live = None
        self.task_id = None
        self.stop_event = threading.Event()

    def start(self, message: str = "处理中..."):
        """启动加载动画"""
        self.progress = Progress(
            SpinnerColumn(spinner_name="dots12", style="#61AFEF"),
            TextColumn("[progress.description]{task.description}", style="#ABB2BF"),
            BarColumn(
                bar_width=30,
                style="#61AFEF",
                finished_style="#98C379"
            ),
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
        """更新加载消息"""
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, description=message)

    def stop(self):
        """停止加载动画"""
        if self.live:
            self.live.stop()
            self.live = None
            self.progress = None
            self.task_id = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class StatusBar:
    """状态栏组件"""

    def __init__(self, console: Console):
        self.console = console

    def render(
        self,
        session_id: Optional[str] = None,
        agent_id: str = "default",
        message_count: int = 0,
        token_count: int = 0,
        show_time: bool = True
    ):
        """渲染状态栏"""
        status_table = Table(show_header=False, box=None, padding=(0, 1), style="dim")
        status_table.add_column(style="dim")
        status_table.add_column(style="dim", justify="right")

        left_items = []

        if session_id:
            left_items.append(f"Session: [cyan]{session_id[:8]}...[/cyan]")
        else:
            left_items.append("[yellow]No Session[/yellow]")

        left_items.append(f"Agent: [yellow]{agent_id}[/yellow]")
        left_items.append(f"Messages: [cyan]{message_count}[/cyan]")

        if token_count > 0:
            left_items.append(f"Tokens: [cyan]{token_count:,}[/cyan]")

        left_text = " │ ".join(left_items)

        right_items = []
        if show_time:
            right_items.append(datetime.now().strftime("%H:%M:%S"))

        right_text = " │ ".join(right_items)

        status_table.add_row(left_text, f"[dim]{right_text}[/dim]")

        self.console.print(status_table)

    def separator(self, style: str = "#3E4451"):
        """分隔线"""
        self.console.print(Rule(style=style))


class Header:
    """头部组件"""

    @staticmethod
    def render(console: Console, title: str = "Evolver", subtitle: Optional[str] = None):
        """渲染头部"""
        console.print()

        header_box = Box(
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║                                                              ║\n"
            "║  ╔╦╗╔═╗╦═╗╔═╗╔═╗╔╗╔╔═╗  ╔═╗╔═╗╔═╗╔═╗╔═╗  ╔╦╗╔═╗╔═╗╔═╗   ║\n"
            "║  ║║║╠═╣╠╦╝║ ╦║ ╦║║║║ ╦  ╚═╗╠═╣╠═╝║╣ ║╣   ║║║╠═╣╚═╗║╣    ║\n"
            "║  ╩ ╩╩ ╩╩╚═╚═╝╚═╝╝╚╝╚═╝  ╚═╝╩ ╩╩  ╚═╝╚═╝  ═╩╝╩ ╩╚═╝╚═╝   ║\n"
            "║                                                              ║\n"
            "╚══════════════════════════════════════════════════════════════╝"
        )

        title_text = Text()
        title_text.append("╔", Style(color="#61AFEF", bold=True))
        title_text.append("═" * 58, Style(color="#61AFEF"))
        title_text.append("╗\n", Style(color="#61AFEF", bold=True))

        title_text.append("║", Style(color="#61AFEF"))
        title_text.append("  " * 15, Style(color="#61AFEF"))
        title_text.append(f"  {title}", Style(color="#E5C07B", bold=True, size=20))
        if subtitle:
            title_text.append(f" - {subtitle}", Style(color="#98C379", size=14))
        title_text.append("  " * 15, Style(color="#61AFEF"))
        title_text.append("║\n", Style(color="#61AFEF"))

        title_text.append("║", Style(color="#61AFEF"))
        title_text.append("  " * 20, Style(color="#61AFEF"))
        title_text.append("✓ 多模型支持  ✓ 技能系统  ✓ 记忆管理  ✓ MCP集成", Style(color="#98C379", size=10))
        title_text.append("  " * 8, Style(color="#61AFEF"))
        title_text.append("║\n", Style(color="#61AFEF"))

        title_text.append("╚", Style(color="#61AFEF", bold=True))
        title_text.append("═" * 58, Style(color="#61AFEF"))
        title_text.append("╝", Style(color="#61AFEF", bold=True))

        console.print(title_text)
        console.print()


class Footer:
    """底部组件"""

    @staticmethod
    def render(console: Console, tips: Optional[List[str]] = None):
        """渲染底部"""
        if tips is None:
            tips = [
                "输入 [cyan]help[/cyan] 查看可用命令",
                "使用 [cyan]agents[/cyan] 切换智能体",
                "使用 [cyan]skills[/cyan] 查看技能",
            ]

        tip = tips[datetime.now().second % len(tips)]

        footer_table = Table(show_header=False, box=None, padding=(0, 0))
        footer_table.add_column(style="dim")
        footer_table.add_column(style="dim", justify="right")

        footer_table.add_row(
            f"[dim]💡 提示: {tip}[/dim]",
            f"[dim]v0.1.0 | Evolver[/dim]"
        )

        console.print()
        console.print(footer_table)


class ChatInterface:
    """聊天界面主组件"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.header = Header()
        self.footer = Footer()
        self.status_bar = StatusBar(self.console)
        self.message_history: List[Dict] = []
        self.session_id: Optional[str] = None
        self.agent_id: str = "default"

    def render_header(self):
        """渲染头部"""
        self.header.render(self.console, "Evolver", "智能AI助手")

    def render_status(self):
        """渲染状态栏"""
        total_tokens = sum(
            msg.get("tokens", {}).get("total_tokens", 0)
            for msg in self.message_history
            if msg.get("role") == "assistant"
        )
        self.status_bar.render(
            session_id=self.session_id,
            agent_id=self.agent_id,
            message_count=len(self.message_history),
            token_count=total_tokens
        )
        self.status_bar.separator()

    def render_footer(self):
        """渲染底部"""
        self.footer.render(self.console)

    def add_message(self, role: str, content: str, tokens: Optional[Dict] = None):
        """添加消息"""
        self.message_history.append({
            "role": role,
            "content": content,
            "time": datetime.now(),
            "tokens": tokens or {}
        })

    def render_welcome(self):
        """渲染欢迎界面"""
        self.console.clear()
        self.render_header()
        self.render_status()

        welcome_text = Text()
        welcome_text.append("\n")
        welcome_text.append("  [bold green]✓[/bold green] 连接成功\n\n", Style(color="#98C379"))
        welcome_text.append("  [dim]欢迎使用 Evolver 智能AI助手！[/dim]\n\n", Style(color="#5C6370"))
        welcome_text.append("  [dim]开始对话，或输入 [cyan]help[/cyan] 查看所有命令[/dim]\n", Style(color="#5C6370"))

        self.console.print(welcome_text)
        self.render_footer()

    def render_help(self):
        """渲染帮助信息"""
        help_table = Table(
            title="[bold #E5C07B]📖 可用命令[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451",
            padding=(1, 2)
        )
        help_table.add_column("命令", style="#98C379", width=20)
        help_table.add_column("说明", style="#ABB2BF")

        commands = [
            ("help", "显示帮助信息"),
            ("health", "检查系统状态"),
            ("agents", "查看可用智能体"),
            ("use <id>", "切换智能体"),
            ("skills", "查看可用技能"),
            ("history", "查看历史消息"),
            ("token", "查看Token使用"),
            ("clear", "清屏"),
            ("quit / q", "退出程序"),
        ]

        for cmd, desc in commands:
            help_table.add_row(f"[#61AFEF]{cmd}[/#61AFEF]", desc)

        self.console.print(help_table)
        self.console.print()


class AgentManager:
    """智能体管理器组件"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render_list(self, agents: List[Dict], current_agent: str):
        """渲染智能体列表"""
        agents_table = Table(
            title="[bold #E5C07B]👥 可用智能体[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451",
            padding=(1, 2)
        )
        agents_table.add_column("ID", style="#98C379", width=15)
        agents_table.add_column("名称", style="#E5C07B", width=20)
        agents_table.add_column("描述", style="#ABB2BF")
        agents_table.add_column("状态", style="#61AFEF", width=10, justify="center")

        for agent in agents:
            agent_id = agent.get("id", "unknown")
            is_active = "✓" if agent_id == current_agent else " "
            agents_table.add_row(
                f"[#61AFEF]{agent_id}[/#61AFEF]",
                f"[#E5C07B]{agent.get('name', '未知')}[/#E5C07B]",
                agent.get('description', '无描述'),
                f"[green]{is_active}[/green]" if is_active == "✓" else "[dim]-[/dim]"
            )

        self.console.print(agents_table)
        self.console.print(f"[dim]当前: {current_agent} | 使用 [cyan]use <id>[/cyan] 切换[/dim]")
        self.console.print()


class SkillManager:
    """技能管理器组件"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render_list(self, skills: List[Dict]):
        """渲染技能列表"""
        skills_table = Table(
            title="[bold #E5C07B]🛠️ 可用技能[/bold #E5C07B]",
            show_header=True,
            header_style="bold #61AFEF",
            box=ROUNDED,
            border_style="#3E4451",
            padding=(1, 2)
        )
        skills_table.add_column("名称", style="#98C379", width=20)
        skills_table.add_column("描述", style="#ABB2BF")

        if not skills:
            self.console.print("[yellow]⚠[/yellow] 暂无可用技能")
            return

        for skill in skills:
            skills_table.add_row(
                f"[#61AFEF]{skill.get('name', '未知')}[/#61AFEF]",
                skill.get('description', '无描述')
            )

        self.console.print(skills_table)
        self.console.print()


class TokenTracker:
    """Token跟踪器组件"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render_usage(self, message_history: List[Dict]):
        """渲染Token使用统计"""
        total_input = 0
        total_output = 0
        total_total = 0

        for msg in message_history:
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
            border_style="#3E4451",
            padding=(1, 2)
        )
        usage_table.add_column("类型", style="#E5C07B", width=20)
        usage_table.add_column("数量", style="#98C379", justify="right")

        usage_table.add_row("📥 输入Token", f"[cyan]{total_input:,}[/cyan]")
        usage_table.add_row("📤 输出Token", f"[cyan]{total_output:,}[/cyan]")
        usage_table.add_row("📦 总计", f"[bold cyan]{total_total:,}[/bold cyan]")

        self.console.print(usage_table)
        self.console.print()


class ProgressBars:
    """进度条组件"""

    @staticmethod
    def multi_task(console: Console, tasks: List[Dict[str, str]]) -> Progress:
        """多任务进度条"""
        progress = Progress(
            SpinnerColumn(spinner_name="dots12", style="#61AFEF"),
            TextColumn("[progress.description]{task.description}", style="#ABB2BF"),
            BarColumn(bar_width=30, style="#61AFEF", finished_style="#98C379"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%", style="#5C6370"),
            console=console,
            transient=True
        )

        progress_tasks = []
        for task in tasks:
            task_id = progress.add_task(
                task.get("description", "任务"),
                total=task.get("total", 100)
            )
            progress_tasks.append(task_id)

        return progress, progress_tasks

    @staticmethod
    def single_task(console: Console, description: str = "加载中...") -> tuple:
        """单任务进度条"""
        progress = Progress(
            SpinnerColumn(spinner_name="dots12", style="#61AFEF"),
            TextColumn("[progress.description]{task.description}", style="#ABB2BF"),
            BarColumn(bar_width=40, style="#61AFEF", finished_style="#98C379"),
            TimeElapsedColumn(),
            console=console,
            transient=True
        )

        task_id = progress.add_task(description, total=None)

        return progress, task_id


class MarkdownRenderer:
    """Markdown渲染器"""

    @staticmethod
    def render(console: Console, markdown_text: str, title: Optional[str] = None):
        """渲染Markdown"""
        md = Markdown(markdown_text, code_theme="monokai", style="white on black")

        if title:
            panel = Panel(
                md,
                title=f"[bold]📄 {title}[/bold]",
                border_style="#61AFEF",
                box=ROUNDED,
                padding=(1, 2)
            )
        else:
            panel = Panel(
                md,
                border_style="#61AFEF",
                box=ROUNDED,
                padding=(1, 2)
            )

        console.print(panel)


class TypewriterEffect:
    """打字机效果"""

    def __init__(self, console: Console, delay: float = 0.02):
        self.console = console
        self.delay = delay

    def print(self, text: str, style: str = "white"):
        """打印打字效果"""
        for char in text:
            self.console.print(f"[{style}]{char}[/{style}]", end="", flush=True)
            time.sleep(self.delay)
        self.console.print()


class ColorfulBorder:
    """彩色边框组件"""

    @staticmethod
    def rainbow(console: Console, content: str, title: Optional[str] = None):
        """彩虹边框"""
        colors = EvolverTheme.RAINBOW
        border_color = colors[datetime.now().second % len(colors)]

        panel = Panel(
            content,
            title=title,
            border_style=border_color,
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)

    @staticmethod
    def animated(console: Console, content: str, title: Optional[str] = None, frames: int = 3):
        """动画边框（渐变效果）"""
        colors = EvolverTheme.RAINBOW

        for i in range(frames):
            border_color = colors[(datetime.now().second + i) % len(colors)]
            panel = Panel(
                content,
                title=title,
                border_style=border_color,
                box=ROUNDED,
                padding=(1, 2)
            )
            console.print(panel)
            time.sleep(0.1)
