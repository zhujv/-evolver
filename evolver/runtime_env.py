"""HTTP 绑定地址解析：server 与 agent 共用，避免两套逻辑不一致或循环 import。"""

import os
from pathlib import Path
from typing import List, Optional, Set


def load_application_dotenv(repo_root: Optional[str] = None) -> None:
    """从仓库根目录或当前工作目录加载 `.env`（不覆盖已存在的环境变量）。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    seen: Set[str] = set()
    paths: List[Path] = []
    if repo_root:
        paths.append(Path(repo_root) / ".env")
    paths.append(Path.cwd() / ".env")
    here = Path(__file__).resolve()
    pkg_parent = here.parents[1]
    if (pkg_parent / "pyproject.toml").is_file():
        paths.append(pkg_parent / ".env")
    for p in paths:
        try:
            key = str(p.resolve())
        except OSError:
            continue
        if key in seen or not p.is_file():
            continue
        seen.add(key)
        load_dotenv(p, override=False)


def effective_http_host() -> str:
    """与历史 server._effective_http_host 行为一致：空字符串视为 127.0.0.1。"""
    h = os.environ.get('EVOLVER_HTTP_HOST', '127.0.0.1').strip()
    return h if h else '127.0.0.1'


def _exec_shell_enabled() -> bool:
    """检查是否允许执行 shell 命令。"""
    return os.environ.get('EVOLVER_ALLOW_EXEC_SHELL', '').strip().lower() in ('1', 'true', 'yes')
