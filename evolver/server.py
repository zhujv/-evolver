#!/usr/bin/env python3
"""AgentServer - JSON-RPC服务器"""
import sys
import os
import json
import time
import threading
import http.server
import socketserver
import logging
import urllib.request
import importlib.util

# 添加项目根目录到路径
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from evolver.agent.manager import AgentManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def _repo_root_for_logs() -> str:
    """从本文件向上查找含 pyproject.toml 的目录，避免子进程 cwd 与仓库根不一致时日志落到错误路径。"""
    d = os.path.abspath(os.path.dirname(__file__))
    for _ in range(10):
        if os.path.isfile(os.path.join(d, 'pyproject.toml')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.abspath(os.getcwd())


def _attach_process_file_log() -> None:
    """将根 logger 同时写入文件；默认写入仓库根目录下的 evolver-python.log。"""
    path = (os.environ.get('EVOLVER_PYTHON_LOG') or '').strip()
    if not path:
        path = os.path.join(_repo_root_for_logs(), 'evolver-python.log')
    try:
        parent = os.path.dirname(os.path.abspath(path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        fh = logging.FileHandler(path, encoding='utf-8')
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
        logging.getLogger().addHandler(fh)
        logging.getLogger(__name__).info('process file log -> %s', os.path.abspath(path))
    except Exception as e:
        try:
            sys.stderr.write(f'[Evolver] file log attach failed: {e}\n')
        except Exception:
            pass


THREAD_PORT = int(os.environ.get('EVOLVER_PORT', '16888'))


def effective_http_host() -> str:
    """返回 HTTP 监听地址。默认仅本机回环（127.0.0.1），
    需远程访问请显式设置环境变量 EVOLVER_HTTP_HOST=0.0.0.0 并务必配置强令牌。"""
    return os.environ.get('EVOLVER_HTTP_HOST', '127.0.0.1')


# 默认仅本机回环，避免未配置令牌时 RPC 被局域网内其他机器访问。需远程访问请显式设置 EVOLVER_HTTP_HOST=0.0.0.0 并务必配置强令牌。
HTTP_HOST = effective_http_host()
SOCKET_PATH = os.environ.get('EVOLVER_SOCKET', '/tmp/evolver.sock')


def check_runtime_dependencies() -> list[str]:
    """检查后端启动前所需的运行依赖。"""
    import shutil
    import site
    print(f'[Evolver] 使用 Python: {sys.executable}')
    print(f'[Evolver] Python路径: {shutil.which(sys.executable)}')
    print(f'[Evolver] Site packages: {site.getsitepackages()}')
    
    required_modules = [
        'httpx',
        'anthropic',
        'openai',
        'yaml',
        'dotenv',
        'cryptography',
        'tiktoken',
        'psutil',
    ]
    missing = []
    for module_name in required_modules:
        try:
            __import__(module_name)
        except Exception as e:
            logger.warning(f'Dependency import failed for {module_name}: {e}')
            missing.append(module_name)
    
    if missing:
        print(f'[警告] 缺少 {len(missing)} 个依赖模块: {missing}')
        print(f'[提示] 如果使用虚拟环境，请确保使用 .venv\\Scripts\\python.exe')
    
    return missing


class AgentServer:
    """JSON-RPC服务器"""

    def __init__(self, port: int = THREAD_PORT, host: str = HTTP_HOST, socket_path: str = SOCKET_PATH):
        self.port = port
        self.host = host
        self.socket_path = socket_path
        self.restart_token = os.environ.get('EVOLVER_RESTART_TOKEN')
        self.server_token = os.environ.get('EVOLVER_SERVER_TOKEN')
        self.manager = AgentManager()
        self.running = True
        self._health_status = {
            'last_ping': time.time(),
            'uptime': 0,
            'start_time': time.time(),
            'request_count': 0,
        }
        if not self.server_token:
            logger.warning(
                'EVOLVER_SERVER_TOKEN 未配置：RPC 将不校验令牌（开发便利）。'
                '任何能访问该端口的客户端均可调用接口；生产或共享网络请务必设置强令牌。'
            )
        if self.host not in ('127.0.0.1', 'localhost', '::1'):
            logger.warning(
                'HTTP 监听地址为 %s（非仅本机回环）。请配置 EVOLVER_SERVER_TOKEN，并避免将端口暴露到不可信网络。',
                self.host,
            )

    @staticmethod
    def get_repo_root() -> str:
        """获取仓库根目录"""
        d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for _ in range(5):
            if os.path.isfile(os.path.join(d, 'pyproject.toml')):
                return d
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _get_static_path(self) -> str:
        """获取静态文件路径"""
        repo_root = self.get_repo_root()
        dist_dir = os.path.join(repo_root, 'frontend', 'dist')
        logger.info(f'static_path check: {dist_dir}, exists={os.path.isdir(dist_dir)}')
        if os.path.isdir(dist_dir):
            return dist_dir
        return ''

    def start_http(self):
        """启动HTTP服务器"""
        static_path = self._get_static_path()
        print(f'[Evolver] static_path: {repr(static_path)}, exists={os.path.isdir(static_path)}')
        
        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            
            def do_GET(self):
                path = self.path.split('?')[0]
                print(f'[DEBUG GET] path={path}, static={static_path}')
                
                if path in ('/', '/index.html'):
                    if static_path and os.path.isfile(os.path.join(static_path, 'index.html')):
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.end_headers()
                        with open(os.path.join(static_path, 'index.html'), 'rb') as f:
                            self.wfile.write(f.read())
                    else:
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Evolver Ready</h1></body></html>')
                    return
                
                if static_path:
                    file_path = path.lstrip('/')
                    full_path = os.path.join(static_path, file_path)
                    if os.path.isfile(full_path):
                        ext = os.path.splitext(full_path)[1].lower()
                        ctype = {'.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css'}.get(ext, 'application/octet-stream')
                        self.send_response(200)
                        self.send_header('Content-Type', ctype)
                        self.end_headers()
                        with open(full_path, 'rb') as f:
                            self.wfile.write(f.read())
                        return
                
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Not Found')
            
            def log_message(self, format, *args):
                pass
        
        class RPCHandler(Handler):
            def do_POST(self):
                if self.path not in ('/', '/rpc'):
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': {'code': 404, 'message': 'Not found'}}).encode())
                    return

                content_length = int(self.headers.get('Content-Length', 0))

                if content_length > 10 * 1024 * 1024:
                    self.send_response(413)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': {'code': 413, 'message': 'Request entity too large'}}).encode())
                    return

                content_type = self.headers.get('Content-Type', '')
                if not content_type.lower().startswith('application/json'):
                    self.send_response(415)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': {'code': 415, 'message': 'Unsupported media type'}}).encode())
                    return

                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)
                    request = json.loads(body)
                    request['_meta_headers'] = {k.lower(): v for k, v in self.headers.items()}
                    response = self.server.agent_server._handle_request(request)
                    response_json = json.dumps(response).encode()
                    
                    # 构建完整的HTTP响应
                    response_str = f"HTTP/1.1 200 OK\r\n"
                    response_str += f"Content-Type: application/json\r\n"
                    response_str += f"Content-Length: {len(response_json)}\r\n"
                    response_str += f"Access-Control-Allow-Methods: POST, OPTIONS\r\n"
                    response_str += f"Access-Control-Allow-Headers: Content-Type, Authorization\r\n"
                    
                    # 添加CORS头
                    origin = self.headers.get('Origin', '')
                    allowed_origins = [
                        'http://localhost:3000',
                        'http://127.0.0.1:3000',
                        'http://localhost:5173',
                        'http://127.0.0.1:5173',
                        'http://localhost:5174',
                        'http://127.0.0.1:5174',
                        'http://localhost:4173',
                        'http://127.0.0.1:4173',
                        'http://localhost:8080',
                        'http://127.0.0.1:8080',
                    ]
                    if origin in allowed_origins or origin.startswith('http://localhost:') or origin.startswith('http://127.0.0.1:'):
                        response_str += f"Access-Control-Allow-Origin: {origin}\r\n"
                        response_str += f"Vary: Origin\r\n"
                    
                    response_str += "\r\n"
                    
                    # 发送响应
                    self.wfile.write(response_str.encode())
                    self.wfile.write(response_json)
                    self.wfile.flush()
                except json.JSONDecodeError:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': {'code': 400, 'message': 'Invalid JSON'}}).encode())
                except Exception as e:
                    logger.error(f'HTTP request failed: {e}')
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': {'code': 500, 'message': 'Internal server error'}}).encode())

            def do_OPTIONS(self):
                self.send_response(200)
                allowed_origins = [
                    'http://localhost:3000',
                    'http://127.0.0.1:3000',
                    'http://localhost:5173',
                    'http://127.0.0.1:5173',
                    'http://localhost:5174',
                    'http://127.0.0.1:5174',
                    'http://localhost:4173',
                    'http://127.0.0.1:4173',
                    'http://localhost:8080',
                    'http://127.0.0.1:8080',
                ]
                origin = self.headers.get('Origin', '')
                if origin in allowed_origins or origin.startswith('http://localhost:') or origin.startswith('http://127.0.0.1:'):
                    self.send_header('Access-Control-Allow-Origin', origin)
                    self.send_header('Vary', 'Origin')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()

        class HTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True
            daemon_threads = True

            def __init__(self, server_address, RequestHandlerClass, agent_server):
                super().__init__(server_address, RequestHandlerClass)
                self.agent_server = agent_server

        try:
            httpd = HTTPServer((self.host, self.port), RPCHandler, self)
            print(f'[Evolver] HTTP server listening on http://{self.host}:{self.port}')
            print(f'[Evolver] Server ready at http://127.0.0.1:{self.port}/rpc')
            
            if static_path and os.environ.get('EVOLVER_AUTO_OPEN', '1') == '1':
                try:
                    import threading
                    def open_browser():
                        import webbrowser
                        time.sleep(1.5)
                        webbrowser.open(f'http://127.0.0.1:{self.port}/launch.html')
                    threading.Thread(target=open_browser, daemon=True).start()
                except Exception:
                    pass
            
            httpd.serve_forever()
        except OSError as e:
            if e.errno == 10048:
                print(f'[Evolver] Error: Port {self.port} is already in use')
            else:
                print(f'[Evolver] HTTP server error: {e}')
            raise

    def start_socket(self):
        """启动Socket服务器"""
        try:
            if os.path.exists(self.socket_path):
                os.remove(self.socket_path)
            
            import socket
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(self.socket_path)
            os.chmod(self.socket_path, 0o600)
            server.listen(5)
            print(f'[Evolver] Unix socket server listening on {self.socket_path}')
            
            while self.running:
                conn, _ = server.accept()
                try:
                    self._handle_connection(conn)
                except Exception as e:
                    logger.error(f'Connection handling failed: {e}')
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f'Socket server error: {e}')
            # 如果socket模式失败，尝试回退到HTTP模式
            print('Socket mode failed, falling back to HTTP mode')
            threading.Thread(target=self.start_http, daemon=True).start()

    def _handle_connection(self, conn):
        """处理Socket连接"""
        try:
            data = conn.recv(4)
            if len(data) < 4:
                return
            length = int.from_bytes(data, 'big')
            if length <= 0 or length > 10 * 1024 * 1024:
                return

            body = b''
            while len(body) < length:
                chunk = conn.recv(length - len(body))
                if not chunk:
                    break
                body += chunk

            if len(body) != length:
                return

            request = json.loads(body)
            response = self._handle_request(request)

            resp_data = json.dumps(response).encode()
            conn.sendall(len(resp_data).to_bytes(4, 'big'))
            conn.sendall(resp_data)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _handle_request(self, request: dict) -> dict:
        """处理请求"""
        # 验证请求格式
        if not isinstance(request, dict):
            return {'error': {'code': -32600, 'message': 'Invalid Request'}, 'id': None}

        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        request_headers = request.get('_meta_headers', {})

        if not isinstance(method, str) or not method:
            return {'error': {'code': -32600, 'message': 'Invalid Request'}, 'id': request_id}
        
        # 验证方法是否存在
        handlers = {
            'chat': self.manager.chat,
            'create_session': self.manager.create_session,
            'delete_session': self.manager.delete_session,
            'list_sessions': self.manager.list_sessions,
            'get_session_history': self.manager.get_session_history,
            'interrupt': self.manager.interrupt,
            'get_agents': self.manager.list_agents,
            'get_skills': self.manager.list_skills,
            'save_skill': self.manager.save_skill,
            'approve_skill': self.manager.approve_skill,
            'reject_skill': self.manager.reject_skill,
            'get_pending_approvals': self.manager.get_pending_approvals,
            'execute_skill': self.manager.execute_skill,
            'get_memory': self.manager.recall_memory,
            'search_memory': self.manager.search_memory,
            'save_memory': self.manager.save_memory,
            'self_evolve': self.manager.self_evolve,
            'create_project': self.manager.create_project,
            'list_projects': self.manager.list_projects,
            'set_active_project': self.manager.set_active_project,
            'get_active_project': self.manager.get_active_project,
            'update_api_config': self.manager.update_api_config,
            'validate_api_config': self.manager.validate_api_config,
            'list_local_files': self.manager.list_local_files,
            'select_directory': self.manager.select_directory,
            'read_local_file': self.manager.read_local_file,
            'exec_shell': self.manager.exec_shell,
            'get_self_evolution_history': self.manager.get_self_evolution_history,
            'get_recent_failures': self.manager.get_recent_failures,
            'record_failure': self.manager.record_failure,
            'list_work_items': self.manager.list_work_items,
            'update_work_item': self.manager.update_work_item,
            'list_mcp_servers': self.manager.list_mcp_servers,
            'connect_mcp_server': self.manager.connect_mcp_server,
            'disconnect_mcp_server': self.manager.disconnect_mcp_server,
            'list_mcp_tools': self.manager.list_mcp_tools,
            'call_mcp_tool': self.manager.call_mcp_tool,
            'health': lambda: self._health_status,
            'restart': self._graceful_restart,
        }
        
        if method not in handlers:
            return {'error': {'code': -32601, 'message': 'Method not found'}, 'id': request_id}
        
        # 验证参数格式
        if not isinstance(params, dict):
            return {'error': {'code': -32602, 'message': 'Invalid params'}, 'id': request_id}

        if method != 'health' and not self._is_method_authorized(method, params, request_headers):
            return {'error': {'code': -32001, 'message': 'Unauthorized'}, 'id': request_id}
        
        # restart属于高危操作，必须显式校验令牌
        if method == 'restart':
            if not self._is_restart_authorized(params.get('restart_token')):
                return {'error': {'code': -32001, 'message': 'Unauthorized'}, 'id': request_id}
            params = {}
        elif 'auth_token' in params:
            params = {k: v for k, v in params.items() if k != 'auth_token'}

        self._health_status['request_count'] += 1
        
        # 处理请求
        handler = handlers.get(method)
        try:
            # 所有操作都同步处理
            result = handler(**params) if params else handler()
            
            # 允许非字典类型的返回值
            return {'result': result, 'id': request_id}
        except Exception as e:
            import traceback
            logger.error(f'Request failed: {e}\n{traceback.format_exc()}')
            return {'error': {'code': -32603, 'message': f'Internal error: {e}'}, 'id': request_id}

    def _graceful_restart(self):
        """优雅重启"""
        self.running = False
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)

    def _is_restart_authorized(self, provided_token: str) -> bool:
        """验证重启操作权限。未配置令牌时，默认禁用远程重启。"""
        if not self.restart_token:
            return False
        return provided_token == self.restart_token

    def _is_method_authorized(self, method: str, params: dict, headers: dict = None) -> bool:
        """统一方法鉴权：除health外均需有效token。未配置token时允许所有请求（开发模式）。"""
        if not self.server_token:
            return True
        header_token = self._extract_bearer_token(headers or {})
        if header_token == self.server_token:
            return True
        return params.get('auth_token') == self.server_token

    def _extract_bearer_token(self, headers: dict) -> str:
        auth = headers.get('authorization', '')
        if not isinstance(auth, str):
            return ''
        parts = auth.split(' ', 1)
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            return parts[1].strip()
        # 支持直接的token（没有Bearer前缀）
        return auth.strip()

    def health_check(self) -> dict:
        """健康检查"""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'uptime': time.time() - self._health_status['start_time'],
            'requests': self._health_status['request_count'],
            'last_ping': time.time() - self._health_status['last_ping'],
        }


class HealthMonitor:
    """健康监控"""
    def __init__(self, server: AgentServer, check_interval: int = 10):
        self.server = server
        self.check_interval = check_interval
        self._stop = threading.Event()
        self._unresponsive_count = 0
        self._max_unresponsive_count = 3
        self._started = False
    
    def start(self):
        """启动监控"""
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
    
    def _monitor_loop(self):
        """监控循环"""
        while not self._stop.is_set():
            time.sleep(self.check_interval)
            
            if not self._started:
                self._started = True
                print('[Health] Monitor started')
                continue
            
            health = self.server.health_check()
            
            # 更新最后ping时间
            self.server._health_status['last_ping'] = time.time()
            
            # 检查服务器是否无响应 - 检查uptime是否异常大（新启动时uptime应该很小）
            uptime = health.get('uptime', 0)
            if uptime > 3600:  # uptime超过1小时才认为是真正无响应
                self._unresponsive_count += 1
                print(f'[Health] Server uptime abnormal: {uptime}s, count={self._unresponsive_count}')
                if self._unresponsive_count >= self._max_unresponsive_count:
                    print(f'[Health] Unresponsive for {self._max_unresponsive_count} checks, restarting...')
                    self.server._graceful_restart()
            else:
                self._unresponsive_count = 0
            
            # 每24小时进行一次滚动重启
            if health['uptime'] > 24 * 3600:
                print(f'[Health] Rolling restart after 24h')
                self.server._graceful_restart()


def main():
    """主函数"""
    from evolver.runtime_env import load_application_dotenv, _exec_shell_enabled
    load_application_dotenv()
    missing = check_runtime_dependencies()
    strict_deps = os.environ.get('EVOLVER_STRICT_DEPS', '').strip().lower() in ('1', 'true', 'yes')
    if missing:
        print('[Evolver] 依赖检查发现缺少以下包:')
        for pkg in missing:
            print(f'  - {pkg}')
        if strict_deps:
            print('[Evolver] 已设置 EVOLVER_STRICT_DEPS=1，缺依赖时退出。')
            print('[Evolver] 请执行: pip install -r requirements.txt')
            raise SystemExit(1)
        print(
            '[Evolver] 仍将继续启动 HTTP（缺包时部分 RPC 可能失败）；'
            '若要在缺依赖时强制退出，请设置环境变量 EVOLVER_STRICT_DEPS=1；'
            '安装依赖: pip install -r requirements.txt'
        )

    _attach_process_file_log()

    try:
        import evolver as _evolver_pkg  # 启动诊断：确认实际加载的包路径
        logger.info('Loaded evolver package from: %s', getattr(_evolver_pkg, '__file__', '?'))
    except Exception as e:
        logger.warning('Could not resolve evolver package path: %s', e)

    server = AgentServer()

    logger.info(
        'Evolver 启动诊断: HTTP_HOST=%r EVOLVER_HTTP_HOST(raw)=%r EVOLVER_ALLOW_EXEC_SHELL=%r '
        'effective_listen=%r exec_shell=%s',
        HTTP_HOST,
        os.environ.get('EVOLVER_HTTP_HOST', '<unset>'),
        os.environ.get('EVOLVER_ALLOW_EXEC_SHELL', '<unset>'),
        effective_http_host().lower(),
        'enabled' if _exec_shell_enabled() else 'disabled',
    )
    
    # 检测系统类型，Windows系统使用HTTP模式
    if os.name == 'nt':
        mode = 'http'
    else:
        mode = os.environ.get('EVOLVER_IPC_MODE', 'socket')
    
    http_thread = None
    if mode == 'http':
        http_thread = threading.Thread(target=server.start_http, daemon=False)
        http_thread.start()
    else:
        try:
            socket_thread = threading.Thread(target=server.start_socket, daemon=False)
            socket_thread.start()
        except AttributeError:
            print('Socket mode not supported, falling back to HTTP mode')
            mode = 'http'
            http_thread = threading.Thread(target=server.start_http, daemon=False)
            http_thread.start()
    
    print(f'[Evolver] Server started in {mode} mode, waiting for HTTP server...')
    time.sleep(1)
    
    HealthMonitor(server).start()
    
    while server.running:
        time.sleep(1)


if __name__ == '__main__':
    main()
