import json
import re
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Any, List, Dict

logger = logging.getLogger(__name__)


class ModelAdapter(ABC):
    @abstractmethod
    def format_tools(self, tools: list[dict]) -> list[dict]:
        pass

    @abstractmethod
    def parse_tool_calls(self, response: Any) -> list[dict]:
        pass


class OpenAIAdapter(ModelAdapter):
    def format_tools(self, tools: List[Dict]) -> List[Dict]:
        formatted = []
        for tool in tools:
            formatted.append({
                'type': 'function',
                'function': {
                    'name': tool.get('name', ''),
                    'description': tool.get('description', ''),
                    'parameters': tool.get('parameters', {})
                }
            })
        return formatted

    def parse_tool_calls(self, response: Any) -> List[Dict]:
        tool_calls = []
        
        try:
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tc in message.tool_calls:
                        tool_calls.append({
                            'id': tc.id,
                            'name': tc.function.name,
                            'parameters': json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                        })
            
            elif isinstance(response, dict):
                if response.get('tool_calls'):
                    for tc in response['tool_calls']:
                        tool_calls.append({
                            'id': tc.get('id', str(uuid.uuid4())),
                            'name': tc.get('name', ''),
                            'parameters': tc.get('parameters', {})
                        })
        
        except Exception as e:
            logger.error(f'OpenAI parse_tool_calls error: {e}')
        
        return tool_calls


class AnthropicAdapter(ModelAdapter):
    def format_tools(self, tools: List[Dict]) -> List[Dict]:
        formatted = []
        for tool in tools:
            formatted.append({
                'name': tool.get('name', ''),
                'description': tool.get('description', ''),
                'input_schema': tool.get('parameters', {})
            })
        return formatted

    def parse_tool_calls(self, response: Any) -> List[Dict]:
        tool_calls = []
        
        try:
            if hasattr(response, 'content') and response.content:
                for block in response.content:
                    if hasattr(block, 'type') and block.type == 'tool_use':
                        tool_calls.append({
                            'id': block.id,
                            'name': block.name,
                            'parameters': block.input if hasattr(block, 'input') else {}
                        })
            
            elif isinstance(response, dict):
                content = response.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            tool_calls.append({
                                'id': block.get('id', str(uuid.uuid4())),
                                'name': block.get('name', ''),
                                'parameters': block.get('input', {})
                            })
        
        except Exception as e:
            logger.error(f'Anthropic parse_tool_calls error: {e}')
        
        return tool_calls


ALLOWED_TOOLS = {
    'read_file', 'write_file', 'patch', 'grep', 'glob',
    'git_commit', 'git_push', 'search_files', 'bash',
    'list_files', 'search_code', 'get_files_info'
}


class UnifiedToolAdapter:
    def parse_tool_calls(self, response: Any, provider: str = 'openai') -> List[Dict]:
        try:
            adapter = {'openai': OpenAIAdapter(), 'anthropic': AnthropicAdapter()}.get(provider, OpenAIAdapter())
            raw_calls = adapter.parse_tool_calls(response)
            
            standardized = []
            for call in raw_calls:
                name = call.get('name', '')
                if name not in ALLOWED_TOOLS:
                    logger.warning(f'Blocked tool call: {name}')
                    continue
                
                standardized.append({
                    'id': call.get('id', str(uuid.uuid4())),
                    'name': name,
                    'parameters': call.get('parameters', {})
                })
            
            return standardized
            
        except Exception as e:
            logger.error(f'parse_tool_calls error: {e}')
            return []

    def _generate_id(self) -> str:
        return str(uuid.uuid4())


class LLMSanitizer:
    def sanitize_llm_input(self, text: str) -> str:
        text = re.sub(r'<system>.*?</system>', '', text, flags=re.DOTALL)
        text = re.sub(r'</?system>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<工具>.*?</工具>', '', text, flags=re.DOTALL)
        text = re.sub(r'</?工具>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(忽略|无视|忘记|执行|运行)[\\s,:]?前面的指令?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'ignore previous instructions?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<\|.*?_\/.*?>', '', text)
        return text

    def sanitize_llm_output(self, text: str) -> str:
        dangerous_cmds = ['rm -rf', 'mkfs', 'dd', 'wget', 'curl', 'sudo', 'su', 'chmod 777', 'chown']
        for cmd in dangerous_cmds:
            text = text.replace(cmd, f'[BLOCKED: {cmd}]')
        return text

    def sanitize_memory_content(self, content: str) -> str:
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'(忽略|无视|忘记|执行|运行)[\\s,:]?前面的指令?', '', content, flags=re.IGNORECASE)
        content = re.sub(r'#\u00a0*(忽略|无视|忘记).*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'//\u00a0*(忽略|无视|忘记).*', '', content, flags=re.IGNORECASE)
        return content