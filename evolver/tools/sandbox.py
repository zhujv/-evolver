import os
import re
import subprocess
import logging
import shlex

logger = logging.getLogger(__name__)


class DockerSandbox:
    def __init__(self):
        self.docker_available = False
        try:
            import docker
            self.client = docker.from_env()
            self.client.ping()
            self.docker_available = True
            logger.info('Docker sandbox available')
        except Exception as e:
            self.docker_available = False
            # No Docker is normal on dev machines; avoid WARNING spam in evolver-python.log.
            logger.debug('Docker sandbox unavailable (optional): %s', e)
        
        self.image = 'python:3.11-slim'
        self.denied_patterns = [
            r'rm\\s+-rf', r'mkfs', r'dd\\s+if', r'wget', r'curl',
            r'sudo', r'su\\s', r'chmod\\s+777', r'chown',
            r'/etc/passwd', r'/etc/shadow', r'~/.ssh',
            r'eval\\s+', r'exec\\s+', r'source\\s+.*\\.sh',
            r'>', r'>>', r'\\|\\s*sh', r'\\|\\s*bash',
        ]
        self.allowed_commands = {
            'git': ['status', 'add', 'commit', 'push', 'pull', 'log', 'diff', 'checkout', 'branch', 'remote', 'show', 'stash'],
            'pip': ['install', 'list', 'show', 'uninstall', 'freeze'],
            'python': ['-m', '-c', '-u', '-v'],
            'npm': ['install', 'run', 'test', 'list', 'view'],
            'node': ['-e', '-p', '-v', '--version'],
            'yarn': ['--version', 'list'],
        }
        self.readonly_commands = ['cat', 'ls', 'grep', 'find', 'echo', 'pwd', 'head', 'tail', 'wc', 'file', 'which', 'env', 'date', 'whoami']

    def execute(self, command: str, timeout: int = 30, workdir: str = None) -> dict:
        command = command.strip()
        if not command:
            raise ValueError('命令不能为空')
        
        for pattern in self.denied_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                logger.warning(f'Blocked dangerous command: {pattern}')
                raise PermissionError(f'禁止执行高危命令: {pattern}')
        
        cmd_parts = command.split()
        if cmd_parts:
            base_cmd = cmd_parts[0]
            if base_cmd in self.allowed_commands:
                if len(cmd_parts) > 1:
                    sub_cmd = cmd_parts[1]
                    if sub_cmd not in self.allowed_commands[base_cmd]:
                        raise PermissionError(f'不允许的子命令: {sub_cmd}')
            elif base_cmd not in self.readonly_commands:
                raise PermissionError(f'不允许的命令: {base_cmd}')
        
        workspace_path = workdir or os.getcwd()
        if os.path.exists('/workspace'):
            workspace_path = '/workspace'
        
        if self.docker_available:
            return self._execute_docker(command, workspace_path, timeout=timeout)
        else:
            return self._fallback_execute(command, timeout=timeout, workdir=workdir)

    def _execute_docker(self, command: str, workspace_path: str, timeout: int = 30) -> dict:
        try:
            escaped_cmd = command.replace('\\', '\\\\').replace('\"', '\\\"').replace('$', '\\$').replace('`', '\\`')
            
            container = self.client.containers.run(
                self.image,
                command=f'sh -lc "{escaped_cmd}"',
                volumes={workspace_path: {'bind': '/workspace', 'mode': 'ro'}},
                working_dir='/workspace',
                network_disabled=True,
                mem_limit='256m',
                cpu_period=100000,
                cpu_quota=25000,
                user='1000:1000',
                cap_drop=['ALL'],
                read_only=True,
                detach=False,
                timeout=max(1, min(int(timeout), 120)),
            )
            output = container.logs().decode('utf-8', errors='replace')
            return {'exit_code': 0, 'output': output, 'sandbox': 'docker'}
        except Exception as e:
            logger.error(f'Docker execution failed: {e}')
            raise RuntimeError('Docker执行失败，已阻止回退到宿主机执行')

    def _fallback_execute(self, command: str, timeout: int = 15, workdir: str = None) -> dict:
        allowed_exact_commands = {
            ('git', 'status'): ['git', 'status'],
            ('git', 'status', '-s'): ['git', 'status', '-s'],
            ('git', 'diff'): ['git', 'diff', '--stat'],
            ('git', 'diff', 'HEAD'): ['git', 'diff', 'HEAD', '--stat'],
            ('git', 'log'): ['git', 'log', '--oneline', '-10'],
            ('git', 'log', '--oneline', '-5'): ['git', 'log', '--oneline', '-5'],
            ('git', 'branch'): ['git', 'branch', '-a'],
            ('git', 'branch', '-a'): ['git', 'branch', '-a'],
            ('git', 'remote', '-v'): ['git', 'remote', '-v'],
            ('git', 'show', '--stat'): ['git', 'show', '--stat', '-1'],
            ('git', 'stash', 'list'): ['git', 'stash', 'list'],
            ('ls',): ['ls'],
            ('ls', '-la'): ['ls', '-la'],
            ('ls', '-l'): ['ls', '-l'],
            ('ls', '-R'): ['ls', '-R'],
            ('ls', '-la', '--color=never'): ['ls', '-la', '--color=never'],
            ('find', '.', '-type', 'f'): ['find', '.', '-type', 'f'],
            ('find', '.', '-type', 'd'): ['find', '.', '-type', 'd'],
            ('pwd',): ['pwd'],
            ('env',): ['env'],
            ('date',): ['date'],
            ('whoami',): ['whoami'],
        }

        try:
            cmd_parts = shlex.split(command)
        except ValueError:
            raise RuntimeError('命令解析失败')

        cmd_tuple = tuple(cmd_parts)
        if cmd_tuple in allowed_exact_commands:
            run_cmd = allowed_exact_commands[cmd_tuple]
        elif len(cmd_parts) == 4 and cmd_parts[0] == 'find' and cmd_parts[1] == '.' and cmd_parts[2] == '-name':
            # 允许 find . -name <pattern>，但限制pattern长度，避免滥用
            if len(cmd_parts[3]) > 128:
                raise RuntimeError('find pattern 过长')
            run_cmd = cmd_parts
        else:
            run_cmd = None

        if run_cmd:
            try:
                result = subprocess.run(
                    run_cmd,
                    capture_output=True,
                    text=True,
                    timeout=max(1, min(int(timeout), 30)),
                    cwd=workdir or os.getcwd(),
                )
                return {
                    'exit_code': result.returncode,
                    'output': result.stdout + result.stderr,
                    'fallback': True,
                    'mode': 'safe_only',
                }
            except subprocess.TimeoutExpired:
                return {'exit_code': 124, 'output': '命令超时', 'fallback': True}
            except Exception as e:
                return {'exit_code': 1, 'output': str(e), 'fallback': True}
        
        allowed_examples = [
            'git status', 'git status -s', 'git diff --stat', 'git log --oneline -5',
            'git branch -a', 'ls -la', 'ls -l', 'find . -name "*.py"', 'pwd',
            'env', 'date', 'whoami',
        ]
        raise RuntimeError(
            f'Docker不可用，该命令不允许在降级模式执行。\\n允许命令: {allowed_examples}'
        )