"""安全回归测试：覆盖高风险修复点。"""

import os
import sys
import tempfile
import types
import unittest

# 兼容最小测试环境依赖缺失
if "psutil" not in sys.modules:
    psutil_stub = types.ModuleType("psutil")

    class _FakeMemoryInfo:
        rss = 64 * 1024 * 1024

    class _FakeProcess:
        def __init__(self, _pid):
            pass

        def memory_info(self):
            return _FakeMemoryInfo()

    psutil_stub.Process = _FakeProcess
    sys.modules["psutil"] = psutil_stub

try:
    import httpx as _httpx_check  # noqa: F401
except ImportError:
    httpx_stub = types.ModuleType("httpx")

    class _StubClient:
        def __init__(self, *a, **k):
            pass

        def post(self, *a, **k):
            raise RuntimeError("httpx stub: install httpx for full tests")

        def close(self):
            pass

    httpx_stub.Client = _StubClient
    httpx_stub.AsyncClient = _StubClient
    httpx_stub.Limits = lambda **kw: None
    httpx_stub.HTTPStatusError = Exception
    httpx_stub.RequestError = Exception
    sys.modules["httpx"] = httpx_stub

if "msgpack" not in sys.modules:
    msgpack_stub = types.ModuleType("msgpack")
    msgpack_stub.dumps = lambda data, use_bin_type=True: b"{}"
    msgpack_stub.loads = lambda data, raw=False: {}
    sys.modules["msgpack"] = msgpack_stub

from evolver.tools.bash_tool import BashTool
from evolver.tools.file_tools import FileTools
from evolver.tools.search_tools import SearchTools
from evolver.tools.sandbox import DockerSandbox
from evolver.skills.skill_store import SkillStore
from evolver.skills.skill_sandbox import SkillSandbox
from evolver.server import AgentServer


class SecurityRegressionTests(unittest.TestCase):
    def test_filetools_block_path_prefix_bypass(self):
        tool = FileTools()
        cwd = os.path.abspath(os.getcwd())
        sibling = f"{cwd}_evil"
        result = tool.read_file(os.path.join(sibling, "a.txt"))
        self.assertIn("error", result)

    def test_filetools_reject_invalid_regex(self):
        tool = FileTools()
        result = tool.grep("[abc", path=os.getcwd())
        self.assertIn("error", result)
        self.assertIn("无效正则表达式", result["error"])

    def test_searchtools_reject_too_long_regex(self):
        tool = SearchTools()
        result = tool.search_files("a" * 201, root_path=os.getcwd())
        self.assertIn("error", result)
        self.assertIn("过长", result["error"])

    def test_bash_tool_reject_multiline_and_danger_chars(self):
        tool = BashTool()
        self.assertIn("error", tool.execute("echo hello\necho world"))
        self.assertIn("error", tool.execute("echo hi; ls"))

    def test_skill_store_reject_path_traversal_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SkillStore(skills_dir=temp_dir)
            ok = store.save_skill({"name": "../escape", "action": {"steps": []}})
            self.assertFalse(ok)

    def test_skill_sandbox_reject_unknown_bash_base(self):
        sandbox = SkillSandbox()
        valid, _ = sandbox.validate_skill(
            {"action": {"steps": [{"tool": "bash", "command": "unknowncmd arg"}]}}
        )
        self.assertFalse(valid)

    def test_docker_failure_does_not_fallback_to_host(self):
        sandbox = DockerSandbox()
        sandbox.docker_available = True

        class _FakeContainers:
            @staticmethod
            def run(*args, **kwargs):
                raise RuntimeError("docker runtime failure")

        class _FakeClient:
            containers = _FakeContainers()

        sandbox.client = _FakeClient()
        with self.assertRaises(RuntimeError):
            sandbox.execute("git status")

    def test_read_file_rejects_large_file(self):
        tool = FileTools()
        with tempfile.NamedTemporaryFile(delete=False, mode="wb", dir=os.getcwd()) as tmp:
            tmp.write(b"a" * (FileTools.MAX_FILE_SIZE_BYTES + 1))
            tmp_path = tmp.name
        try:
            result = tool.read_file(tmp_path)
            self.assertIn("error", result)
            self.assertIn("文件过大", result["error"])
        finally:
            os.remove(tmp_path)

    def test_server_requires_token_for_non_health(self):
        # 已配置 EVOLVER_SERVER_TOKEN 时，非 health 方法必须带令牌（与 _is_method_authorized 一致）
        os.environ["EVOLVER_SERVER_TOKEN"] = "required-token-xyz"
        try:
            server = AgentServer(port=16891)
            response = server._handle_request({"method": "create_session", "params": {}, "id": 10})
            self.assertIn("error", response)
            self.assertEqual(response["error"]["message"], "Unauthorized")
        finally:
            os.environ.pop("EVOLVER_SERVER_TOKEN", None)

    def test_server_accepts_authorization_header(self):
        os.environ["EVOLVER_SERVER_TOKEN"] = "server-token-1"
        try:
            server = AgentServer(port=16892)
            response = server._handle_request(
                {
                    "method": "create_session",
                    "params": {},
                    "id": 11,
                    "_meta_headers": {"authorization": "Bearer server-token-1"},
                }
            )
            self.assertIn("result", response)
        finally:
            del os.environ["EVOLVER_SERVER_TOKEN"]

if __name__ == "__main__":
    unittest.main()
