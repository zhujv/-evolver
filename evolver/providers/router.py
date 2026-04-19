import os
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from .adapter import LLMSanitizer

logger = logging.getLogger(__name__)


def _agent_debug_ndjson(location: str, message: str, data: dict, hypothesis_id: str) -> None:
    # region agent log
    try:
        here = Path(__file__).resolve().parent
        root = Path.cwd()
        for d in (here, *here.parents):
            if (d / 'pyproject.toml').is_file():
                root = d
                break
        path = str(root / 'debug-24e034.log')
        payload = {
            'sessionId': '24e034',
            'timestamp': int(time.time() * 1000),
            'location': location,
            'message': message,
            'data': data,
            'hypothesisId': hypothesis_id,
            'runId': os.environ.get('EVOLVER_DEBUG_RUN_ID', 'pre-fix'),
        }
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    except Exception:
        pass
    # endregion


def _pick_provider_by_priority(provider_configs: Dict[str, Dict]) -> Optional[str]:
    """未显式指定 preferred_provider 时，按固定优先级选择，避免 JSON 键序让旧的 custom 中转长期优先于官方线路。"""
    priority = ("zhipu", "deepseek", "openai", "anthropic", "google", "custom")
    for name in priority:
        cfg = provider_configs.get(name)
        if isinstance(cfg, dict) and cfg.get("endpoint"):
            return name
    for name, cfg in provider_configs.items():
        if isinstance(cfg, dict) and cfg.get("endpoint"):
            return name
    return None


try:
    import httpx  # type: ignore
except ImportError:  # pragma: no cover
    httpx = None


class ModelRouter:
    def __init__(self):
        self.main_model = os.environ.get('EVOLVER_MAIN_MODEL', 'claude-sonnet-4-20250514')
        self.fallback_model = os.environ.get('EVOLVER_FALLBACK_MODEL', 'gpt-4o')
        self.failure_count = 0
        self.circuit_breaker_open = False
        self.circuit_breaker_reset_time = 0
        self.max_failures = 3
        self.circuit_breaker_duration = 60
        self.timeout = int(os.environ.get('EVOLVER_TIMEOUT', '30'))
        
        # 添加LLM sanitizer，用于过滤敏感内容
        self._sanitizer = LLMSanitizer()
        
        self._init_proxy_config()
        
        # 导入异步模块
        try:
            import httpx
            self.async_client = None
            if self.api_base:
                self.async_client = httpx.AsyncClient(
                    base_url=self.api_base.rstrip('/'),
                    timeout=self.timeout,
                    headers=self._build_headers()
                )
        except ImportError:
            self.async_client = None

    def _init_proxy_config(self):
        self.api_base = os.environ.get('EVOLVER_API_BASE', '').strip()
        self.api_key = os.environ.get('EVOLVER_API_KEY', '').strip()
        self.proxy_type = os.environ.get('EVOLVER_PROXY_TYPE', 'openai').lower()
        self.provider_configs: Dict[str, Dict] = {}
        effective_provider: Optional[str] = None
        file_preferred = ''
        
        logger.info(f'Initial config from env: api_base={self.api_base}, api_key={"***" if self.api_key else ""}')
        
        try:
            from ..config.loader import ConfigLoader
            config = ConfigLoader().load()
            api_config = config.get('api', {})
            providers_config = api_config.get('providers', {})
            file_preferred = (api_config.get('preferred_provider') or '').strip()
            
            logger.info(f'Loaded config: providers={list(providers_config.keys())}')
            self.provider_configs = {k: v for k, v in providers_config.items() if isinstance(v, dict)}

            # 磁盘 preferred_provider 优先于进程内 EVOLVER_PROXY_TYPE，避免陈旧环境变量压过界面保存结果
            preferred_raw = file_preferred
            if not preferred_raw:
                preferred_raw = os.environ.get('EVOLVER_PROXY_TYPE', '').strip()
            default_provider = preferred_raw.lower()
            effective_provider = (
                default_provider if default_provider and default_provider in self.provider_configs else None
            )
            if effective_provider is None:
                effective_provider = _pick_provider_by_priority(self.provider_configs)
            if effective_provider:
                provider_data = self.provider_configs[effective_provider]
                if provider_data.get('endpoint'):
                    self.api_base = provider_data['endpoint'].strip()
                if provider_data.get('api_key'):
                    self.api_key = provider_data['api_key'].strip()
                if provider_data.get('model_name'):
                    self.main_model = provider_data['model_name'].strip()
                self.proxy_type = str(effective_provider).strip().lower()
                logger.info(
                    'Applied API provider [%s] (preferred=%r, effective=%s)',
                    effective_provider,
                    default_provider or None,
                    effective_provider,
                )
        except Exception as e:
            logger.error(f'Failed to load API config: {e}')

        # validate_api_config 会先写入 EVOLVER_*；磁盘配置不应覆盖本次验证用的环境变量
        if os.environ.get('EVOLVER_API_BASE'):
            self.api_base = os.environ.get('EVOLVER_API_BASE', '').strip()
        if os.environ.get('EVOLVER_API_KEY'):
            self.api_key = os.environ.get('EVOLVER_API_KEY', '').strip()
        if os.environ.get('EVOLVER_MAIN_MODEL'):
            self.main_model = os.environ.get('EVOLVER_MAIN_MODEL', '').strip()

        # region agent log
        _agent_debug_ndjson(
            'router.py:_init_proxy_config',
            'merge complete',
            {
                'effective_provider': effective_provider,
                'file_preferred_set': bool(file_preferred),
                'env_EVOLVER_PROXY_TYPE': (os.environ.get('EVOLVER_PROXY_TYPE') or '')[:32],
                'env_has_api_base': bool(os.environ.get('EVOLVER_API_BASE')),
                'api_base_tail': (self.api_base or '')[-56:],
                'proxy_type': self.proxy_type,
            },
            'H1',
        )
        # endregion

        logger.info(
            'After config merge: api_key=%s',
            'set' if self.api_key else 'empty',
        )
        
        # 只有在API基础URL变更时才重新创建客户端
        if self.api_base:
            if httpx is None:
                logger.warning('httpx package not installed; proxy mode disabled')
                self.client = None
            else:
                try:
                    # 检查是否需要重新创建客户端
                    if not hasattr(self, '_client_api_base') or self._client_api_base != self.api_base:
                        # 关闭旧客户端
                        if hasattr(self, 'client') and self.client:
                            try:
                                self.client.close()
                            except:
                                pass
                        
                        # 创建新客户端，使用连接池
                        self.client = httpx.Client(
                            base_url=self.api_base.rstrip('/'),
                            timeout=self.timeout,
                            headers=self._build_headers(),
                            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
                        )
                        self._client_api_base = self.api_base
                        logger.info(f'Using custom API: {self.api_base} (type: {self.proxy_type})')
                        if not self.api_key:
                            logger.warning(
                                '已配置自定义 API 基址但未设置 api_key（环境变量或 ~/.evolver/config.json 中 '
                                'api.providers.*.api_key）。多数中转站会返回 401 或长时间无响应，请补全密钥。'
                            )
                except Exception as e:
                    logger.error(f'Failed to create httpx client: {e}')
                    self.client = None
        else:
            logger.info('No API base found, initializing direct clients')
            self._init_direct_clients()
    
    def reload_config(self):
        """重新加载API配置"""
        self._init_proxy_config()
        # 重新初始化异步客户端
        try:
            import httpx
            self.async_client = None
            if self.api_base:
                self.async_client = httpx.AsyncClient(
                    base_url=self.api_base.rstrip('/'),
                    timeout=self.timeout,
                    headers=self._build_headers()
                )
        except ImportError:
            self.async_client = None

    def get_provider_config(self, provider: str) -> Dict:
        return self.provider_configs.get(provider, {})

    def _build_headers(self) -> Dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def _init_direct_clients(self):
        self._anthropic_client = None
        self._openai_client = None
        
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        openai_key = os.environ.get('OPENAI_API_KEY')
        
        if anthropic_key:
            try:
                import anthropic
                self._anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                logger.info('Anthropic client initialized')
            except ImportError:
                logger.warning('anthropic package not installed')
        
        if openai_key:
            try:
                import openai
                openai.api_key = openai_key
                self._openai_client = openai
                logger.info('OpenAI client initialized')
            except ImportError:
                logger.warning('openai package not installed')

    def _get_provider(self, model: str) -> str:
        if self.api_base:
            return 'proxy'
        lower_model = (model or '').lower()
        if 'anthropic' in lower_model or 'claude' in lower_model:
            return 'anthropic'
        return 'openai'

    def chat(self, messages: List[Dict], prompt: str, tools: List[Dict] = None) -> Dict:
        # 只有在配置可能过期时才重新加载，避免每次调用都重载
        if time.time() - getattr(self, '_last_config_reload', 0) > 60:  # 每60秒重载一次
            self.reload_config()
            self._last_config_reload = time.time()
            
        if self.circuit_breaker_open:
            if time.time() < self.circuit_breaker_reset_time:
                logger.info(f'Circuit breaker open, using fallback: {self.fallback_model}')
                return self._call_model(self.fallback_model, messages, prompt, tools)
            else:
                self.circuit_breaker_open = False
                self.failure_count = 0
                logger.info('Circuit breaker reset')
        
        try:
            result = self._call_model(self.main_model, messages, prompt, tools)
            self.failure_count = 0
            return result
        except Exception as e:
            logger.error(f'Main model failed: {e}')
            self.failure_count += 1
            if self.failure_count >= self.max_failures:
                self.circuit_breaker_open = True
                self.circuit_breaker_reset_time = time.time() + self.circuit_breaker_duration
                logger.warning(f'Circuit breaker opened after {self.max_failures} failures')
            return self._call_model(self.fallback_model, messages, prompt, tools)

    def _call_model(self, model: str, messages: List[Dict], prompt: str, tools: List[Dict] = None) -> Dict:
        provider = self._get_provider(model)
        
        if provider == 'proxy':
            return self._call_proxy(model, messages, prompt, tools)
        elif provider == 'anthropic':
            return self._call_anthropic(model, messages, prompt, tools)
        else:
            return self._call_openai(model, messages, prompt, tools)

    def _call_proxy(self, model: str, messages: List[Dict], prompt: str, tools: List[Dict] = None) -> Dict:
        if not self.client:
            return self._mock_response(model, 'Proxy client not initialized')
        
        try:
            full_messages = [{'role': 'system', 'content': prompt}]
            
            for msg in messages:
                if msg.get('role') == 'system':
                    continue
                content = msg.get('content', '')
                if isinstance(content, list):
                    text_content = [c for c in content if isinstance(c, dict) and c.get('type') != 'image']
                    if text_content:
                        full_messages.append({**msg, 'content': text_content})
                    else:
                        return self._mock_response(model, '此模型不支持图片输入，请仅发送文本消息')
                else:
                    full_messages.append(msg)
            
            request_data = {
                'model': model,
                'messages': full_messages,
                'stream': False,
            }
            
            if tools:
                request_data['tools'] = self._format_tools_for_proxy(tools)
            
            response = self.client.post('/v1/chat/completions', json=request_data)
            response.raise_for_status()
            result = response.json()
            
            # 提取token使用信息
            token_usage = {}
            if 'usage' in result:
                token_usage = result['usage']
                logger.info(f'Token usage: {token_usage}')
            
            parsed_response = self._parse_proxy_response(result)
            parsed_response['token_usage'] = token_usage
            
            # 过滤敏感内容
            parsed_response['content'] = self._sanitizer.sanitize_llm_output(parsed_response['content'])
            
            return parsed_response
            
        except Exception as e:
            error_msg = str(e)
            status = None
            detail = ""
            
            if httpx is not None and isinstance(e, httpx.HTTPStatusError):
                status = e.response.status_code
                try:
                    detail = e.response.text
                    try:
                        error_data = e.response.json()
                        detail = error_data.get('error', {}).get('message', detail)
                    except:
                        pass
                except:
                    detail = str(e)
                logger.error(f'Proxy HTTP error: {status} {detail[:500]}')
            elif httpx is not None and isinstance(e, httpx.RequestError):
                logger.error(f'Proxy network error: {type(e).__name__}: {e}')
                error_msg = f"网络请求失败: {e}"
            else:
                logger.error(f'Proxy error: {type(e).__name__}: {e}')
            
            friendly_msg = self._get_friendly_error(status, error_msg, detail)
            return {'content': f'[错误] {friendly_msg}', 'tool_calls': [], 'error': friendly_msg}
    
    def _get_friendly_error(self, status: Optional[int], error_msg: str, detail: str) -> str:
        """将错误转换为友好提示"""
        detail_lower = (detail or '').lower()
        error_lower = error_msg.lower()
        
        if status == 401:
            return "API密钥无效，请检查配置中的 api_key 是否正确"
        elif status == 403:
            return "API访问被拒绝，可能是权限不足或IP限制"
        elif status == 404:
            return "API地址错误，请检查 endpoint 配置是否正确"
        elif status == 429:
            return "请求频率过高，请稍后重试或检查API配额"
        elif status == 500:
            return "服务商服务器错误，请稍后重试"
        elif status == 502 or status == 503:
            return "服务商服务暂时不可用，请检查 endpoint 或稍后重试"
        elif status == 504:
            return "服务商响应超时，请检查网络或尝试其他 endpoint"
        
        if 'unauthorized' in detail_lower or 'invalid api key' in detail_lower:
            return "API密钥无效，请检查配置中的 api_key"
        if 'not found' in detail_lower:
            return "API地址错误，请检查 endpoint 配置"
        if 'timeout' in detail_lower:
            return "请求超时，请检查网络或 endpoint 配置"
        if 'connection' in detail_lower:
            return "无法连接到API，请检查 endpoint 是否可访问"
        if 'dns' in detail_lower:
            return "DNS解析失败，请检查网络连接或endpoint地址"
        if 'ssl' in detail_lower or 'certificate' in detail_lower:
            return "SSL证书错误，请检查endpoint是否使用了有效的HTTPS证书"
        if 'network' in detail_lower:
            return "网络连接错误，请检查网络连接状态"
        
        # 图片输入不支持
        if 'does not support image' in error_lower or 'does not support image' in detail_lower:
            return "当前模型不支持图片输入，请仅发送文本消息"
        if 'image input' in error_lower:
            return "当前模型不支持图片输入，请仅发送文本消息"
        if 'cannot read' in error_lower and 'image' in error_lower:
            return "当前模型不支持图片输入，请仅发送文本消息"
        
        # 其他常见错误
        if 'rate limit' in detail_lower:
            return "API速率限制，请稍后重试"
        if 'quota' in detail_lower:
            return "API配额用尽，请检查账户状态"
        if 'invalid model' in detail_lower:
            return "模型名称无效，请检查模型配置"
        
        return f"模型调用失败: {error_msg}"

    def validate_api_config(self) -> Dict[str, any]:
        """验证API配置的有效性"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not self.api_base:
            validation_result['errors'].append('API endpoint 未配置')
            validation_result['valid'] = False
        else:
            # 验证endpoint格式
            if not (self.api_base.startswith('http://') or self.api_base.startswith('https://')):
                validation_result['errors'].append('API endpoint 格式错误，必须以 http:// 或 https:// 开头')
                validation_result['valid'] = False
            
            # 尝试测试连接
            if httpx:
                try:
                    test_client = httpx.Client(timeout=5)
                    response = test_client.get(self.api_base, timeout=5)
                    if response.status_code not in [200, 401, 403]:
                        validation_result['warnings'].append(f'Endpoint 响应状态码: {response.status_code}')
                except Exception as e:
                    validation_result['errors'].append(f'无法连接到 endpoint: {str(e)}')
                    validation_result['valid'] = False
                finally:
                    try:
                        test_client.close()
                    except:
                        pass
        
        if not self.api_key:
            validation_result['warnings'].append('API key 未配置，可能会导致认证失败')
        
        return validation_result
    
    async def _call_proxy_async(self, model: str, messages: List[Dict], prompt: str, tools: List[Dict] = None) -> Dict:
        if not self.async_client:
            return self._mock_response(model, 'Async proxy client not initialized')
        
        try:
            full_messages = [{'role': 'system', 'content': prompt}]
            
            for msg in messages:
                if msg.get('role') == 'system':
                    continue
                content = msg.get('content', '')
                if isinstance(content, list):
                    text_content = [c for c in content if isinstance(c, dict) and c.get('type') != 'image']
                    if text_content:
                        full_messages.append({**msg, 'content': text_content})
                    else:
                        return self._mock_response(model, '此模型不支持图片输入，请仅发送文本消息')
                else:
                    full_messages.append(msg)
            
            request_data = {
                'model': model,
                'messages': full_messages,
                'stream': False,
            }
            
            if tools:
                request_data['tools'] = self._format_tools_for_proxy(tools)
            
            response = await self.async_client.post('/v1/chat/completions', json=request_data)
            response.raise_for_status()
            result = response.json()
            
            # 提取token使用信息
            token_usage = {}
            if 'usage' in result:
                token_usage = result['usage']
                logger.info(f'Token usage: {token_usage}')
            
            parsed_response = self._parse_proxy_response(result)
            parsed_response['token_usage'] = token_usage
            
            # 过滤敏感内容
            parsed_response['content'] = self._sanitizer.sanitize_llm_output(parsed_response['content'])
            
            return parsed_response
            
        except Exception as e:
            # 统一上抛给上层熔断逻辑处理
            if httpx is not None and isinstance(e, getattr(httpx, "HTTPStatusError", Exception)):
                status = getattr(getattr(e, "response", None), "status_code", "unknown")
                logger.error(f'Proxy HTTP error: {status}')
            else:
                logger.error(f'Proxy error: {type(e).__name__}')
            raise

    def _format_tools_for_proxy(self, tools: List[Dict]) -> List[Dict]:
        formatted = []
        for tool in tools:
            if self.proxy_type == 'anthropic':
                formatted.append({
                    'name': tool.get('name', ''),
                    'description': tool.get('description', ''),
                    'input_schema': tool.get('parameters', {})
                })
            else:
                formatted.append({
                    'type': 'function',
                    'function': {
                        'name': tool.get('name', ''),
                        'description': tool.get('description', ''),
                        'parameters': tool.get('parameters', {})
                    }
                })
        return formatted

    def _parse_proxy_response(self, response: Dict) -> Dict:
        content = ''
        tool_calls = []
        
        if 'choices' in response:
            choice = response['choices'][0]
            message = choice.get('message', {})
            content = message.get('content', '')
            
            if message.get('tool_calls'):
                for tc in message['tool_calls']:
                    arguments = tc.get('function', {}).get('arguments', '{}')
                    try:
                        parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                    except json.JSONDecodeError:
                        parsed_args = {}
                    tool_calls.append({
                        'id': tc.get('id', ''),
                        'name': tc.get('function', {}).get('name', ''),
                        'parameters': parsed_args
                    })
        
        elif 'content' in response:
            content = response.get('content', '')
            if response.get('tool_calls'):
                for tc in response['tool_calls']:
                    tool_calls.append({
                        'id': tc.get('id', ''),
                        'name': tc.get('name', ''),
                        'parameters': tc.get('input', {})
                    })
        
        return {'content': content, 'tool_calls': tool_calls}

    def _call_anthropic(self, model: str, messages: List[Dict], prompt: str, tools: List[Dict] = None) -> Dict:
        if not self._anthropic_client:
            return self._mock_response(model, 'Anthropic client not initialized')
        
        try:
            system_msg = prompt
            user_msgs = []
            for msg in messages:
                if msg.get('role') == 'system':
                    system_msg = msg.get('content', '')
                elif msg.get('role') == 'user':
                    content = msg.get('content', '')
                    if isinstance(content, str):
                        user_msgs.append(msg)
                    elif isinstance(content, list):
                        text_content = [c for c in content if isinstance(c, dict) and c.get('type') != 'image']
                        if text_content:
                            user_msgs.append({**msg, 'content': text_content})
                        else:
                            user_msgs.append({'role': 'user', 'content': '请处理图片内容'})
                else:
                    user_msgs.append(msg)
            
            tool_defs = None
            if tools:
                tool_defs = [{'name': t['name'], 'description': t['description'], 'input_schema': t['parameters']} for t in tools]

            response = self._anthropic_client.messages.create(
                model=model.replace('anthropic/', '').replace('claude-', 'claude-'),
                max_tokens=4096,
                system=system_msg,
                messages=user_msgs,
                tools=tool_defs,
                timeout=self.timeout,
            )
            
            tool_calls = []
            content = ''
            if response.content:
                for block in response.content:
                    if hasattr(block, 'type'):
                        if block.type == 'tool_use':
                            tool_calls.append({'id': block.id, 'name': block.name, 'parameters': getattr(block, 'input', {})})
                        elif block.type == 'text':
                            content += block.text
            
            # 提取token使用信息
            token_usage = {}
            if hasattr(response, 'usage') and response.usage:
                token_usage = {
                    'prompt_tokens': getattr(response.usage, 'input_tokens', 0),
                    'completion_tokens': getattr(response.usage, 'output_tokens', 0),
                    'total_tokens': getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0)
                }
                logger.info(f'Token usage: {token_usage}')
            
            # 过滤敏感内容
            content = self._sanitizer.sanitize_llm_output(content)
            
            return {'content': content, 'tool_calls': tool_calls, 'token_usage': token_usage}
            
        except Exception as e:
            logger.error(f'Anthropic API error: {type(e).__name__}: {e}')
            raise

    def _call_openai(self, model: str, messages: List[Dict], prompt: str, tools: List[Dict] = None) -> Dict:
        if not self._openai_client:
            return self._mock_response(model, 'OpenAI client not initialized')
        
        try:
            full_messages = [{'role': 'system', 'content': prompt}]
            
            for msg in messages:
                if msg.get('role') == 'system':
                    continue
                content = msg.get('content', '')
                if isinstance(content, list):
                    text_content = [c for c in content if isinstance(c, dict) and c.get('type') != 'image']
                    if text_content:
                        full_messages.append({**msg, 'content': text_content})
                    else:
                        full_messages.append({'role': msg.get('role', 'user'), 'content': '请处理图片内容'})
                else:
                    full_messages.append(msg)
            
            tool_defs = None
            if tools:
                tool_defs = [{'type': 'function', 'function': t} for t in tools]

            model_name = model.replace('openai/', '')
            response = None

            # OpenAI SDK v1+
            if hasattr(self._openai_client, 'chat') and hasattr(self._openai_client.chat, 'completions'):
                response = self._openai_client.chat.completions.create(
                    model=model_name,
                    messages=full_messages,
                    tools=tool_defs,
                    timeout=self.timeout,
                )
            # Legacy OpenAI SDK
            elif hasattr(self._openai_client, 'ChatCompletion'):
                response = self._openai_client.ChatCompletion.create(
                    model=model_name,
                    messages=full_messages,
                    tools=tool_defs,
                    timeout=self.timeout,
                )
            else:
                raise RuntimeError('Unsupported OpenAI client interface')
            
            choice = response.choices[0]
            tool_calls = []
            message = getattr(choice, 'message', None)
            if message and getattr(message, 'tool_calls', None):
                for tc in message.tool_calls:
                    tool_calls.append({
                        'id': tc.id,
                        'name': tc.function.name,
                        'parameters': json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                    })
            
            # 提取token使用信息
            token_usage = {}
            if hasattr(response, 'usage') and response.usage:
                token_usage = {
                    'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                    'total_tokens': getattr(response.usage, 'total_tokens', 0)
                }
                logger.info(f'Token usage: {token_usage}')
            
            # 过滤敏感内容
            content = self._sanitizer.sanitize_llm_output(getattr(message, 'content', '') or '')
            
            return {'content': content, 'tool_calls': tool_calls, 'token_usage': token_usage}
            
        except Exception as e:
            logger.error(f'OpenAI API error: {type(e).__name__}: {e}')
            raise

    def _mock_response(self, model: str, reason: str) -> Dict:
        diagnostics = []
        if self.api_base:
            diagnostics.append(f'api_base={self.api_base}')
        if self.main_model:
            diagnostics.append(f'model={self.main_model}')
        if self.api_key:
            diagnostics.append('api_key=set')
        if httpx is None:
            diagnostics.append('httpx_missing')
        diag_text = f" ({', '.join(diagnostics)})" if diagnostics else ''
        return {
            'content': f'[Mock] {reason}{diag_text}. 请配置 API Key (ANTHROPIC_API_KEY / OPENAI_API_KEY) 或使用自定义中转 (EVOLVER_API_BASE + EVOLVER_API_KEY)',
            'tool_calls': [],
            '_mock': True,
        }

    def get_adapter(self, provider: str):
        from .adapter import OpenAIAdapter, AnthropicAdapter
        return {'openai': OpenAIAdapter(), 'anthropic': AnthropicAdapter()}.get(provider, OpenAIAdapter())
        return {'openai': OpenAIAdapter(), 'anthropic': AnthropicAdapter()}.get(provider, OpenAIAdapter())