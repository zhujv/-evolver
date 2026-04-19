import os
import json
import logging
from typing import Dict, Any
from .defaults import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class ConfigLoader:
    def __init__(self, config_path: str = "~/.evolver/config.json"):
        self.config_path = os.path.expanduser(config_path)
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            self._create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return self._validate_config(config)
        except json.JSONDecodeError as e:
            logger.error(f'Invalid JSON in config: {e}')
            return DEFAULT_CONFIG
        except Exception as e:
            logger.error(f'Failed to load config: {e}')
            return DEFAULT_CONFIG

    def _validate_config(self, config: Dict) -> Dict:
        validated = DEFAULT_CONFIG.copy()
        
        if not isinstance(config, dict):
            return validated
        
        if 'model' in config and isinstance(config['model'], dict):
            validated['model'] = {**validated['model'], **config['model']}
        
        if 'tools' in config and isinstance(config['tools'], dict):
            validated['tools'] = {**validated['tools'], **config['tools']}
        
        if 'permissions' in config and isinstance(config['permissions'], dict):
            validated['permissions'] = {**validated['permissions'], **config['permissions']}
        
        if 'memory' in config and isinstance(config['memory'], dict):
            validated['memory'] = {**validated['memory'], **config['memory']}
        
        if 'privacy' in config and isinstance(config['privacy'], dict):
            validated['privacy'] = {**validated['privacy'], **config['privacy']}
        
        if 'ui' in config and isinstance(config['ui'], dict):
            validated['ui'] = {**validated['ui'], **config['ui']}
        
        if 'evolution' in config and isinstance(config['evolution'], dict):
            validated['evolution'] = {**validated['evolution'], **config['evolution']}

        if 'mcp' in config and isinstance(config['mcp'], dict):
            validated['mcp'] = {**validated['mcp'], **config['mcp']}

        if 'project' in config and isinstance(config['project'], dict):
            validated['project'] = {**validated['project'], **config['project']}

        if 'integrations' in config and isinstance(config['integrations'], dict):
            merged_integrations = dict(validated.get('integrations', {}))
            for name, value in config['integrations'].items():
                if isinstance(value, dict) and isinstance(merged_integrations.get(name), dict):
                    merged_integrations[name] = {**merged_integrations[name], **value}
                else:
                    merged_integrations[name] = value
            validated['integrations'] = merged_integrations

        if 'api' in config and isinstance(config['api'], dict):
            validated['api'] = config['api']
        
        return validated

    def _create_default_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)

    def save(self, config: Dict):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)