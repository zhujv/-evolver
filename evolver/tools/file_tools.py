"""FileTools - 文件操作工具"""

import os
import re
from glob import glob


class FileTools:
    """文件操作工具"""
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

    def read_file(self, path: str, offset: int = None, limit: int = None) -> dict:
        """读取文件"""
        try:
            # 验证路径安全性
            safe_path = self._sanitize_path(path)
            if not safe_path:
                return {"error": "路径不安全"}
            
            # 检查文件是否存在
            if not os.path.exists(safe_path):
                return {"error": "文件不存在"}
            
            # 检查是否是文件
            if not os.path.isfile(safe_path):
                return {"error": "路径不是文件"}
            if os.path.getsize(safe_path) > self.MAX_FILE_SIZE_BYTES:
                return {"error": "文件过大，拒绝读取"}
            
            with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                
            if offset is not None:
                lines = lines[offset:]
            if limit is not None:
                lines = lines[:limit]
            
            content = ''.join(lines)
            return {"content": content}
        except Exception as e:
            return {"error": str(e)}

    def _sanitize_path(self, path: str) -> str:
        """验证路径安全性"""
        # 规范化路径，并解析符号链接，避免通过软链接绕过限制
        safe_path = os.path.realpath(os.path.abspath(os.path.normpath(path)))
        current_dir = os.path.realpath(os.path.abspath(os.getcwd()))
        try:
            # 使用commonpath避免简单startswith前缀绕过（如 /app 与 /app_evil）
            if os.path.commonpath([safe_path, current_dir]) != current_dir:
                return None
        except ValueError:
            return None
        return safe_path

    def write_file(self, path: str, content: str) -> dict:
        """写入文件"""
        try:
            # 验证路径安全性
            safe_path = self._sanitize_path(path)
            if not safe_path:
                return {"error": "路径不安全"}
            
            # 确保目录存在
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            
            # 检查文件是否存在，如果存在则检查权限
            if os.path.exists(safe_path) and not os.access(safe_path, os.W_OK):
                return {"error": "没有写入权限"}

            if len(content.encode('utf-8')) > self.MAX_FILE_SIZE_BYTES:
                return {"error": "内容过大，拒绝写入"}
            
            with open(safe_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def patch(self, path: str, oldString: str, newString: str) -> dict:
        """补丁文件"""
        try:
            # 验证路径安全性
            safe_path = self._sanitize_path(path)
            if not safe_path:
                return {"error": "路径不安全"}
            
            # 检查文件是否存在
            if not os.path.exists(safe_path):
                return {"error": "文件不存在"}
            
            # 检查是否是文件
            if not os.path.isfile(safe_path):
                return {"error": "路径不是文件"}
            
            # 检查文件是否可读写
            if not os.access(safe_path, os.R_OK):
                return {"error": "没有读取权限"}
            if not os.access(safe_path, os.W_OK):
                return {"error": "没有写入权限"}
            
            with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            if oldString not in content:
                return {"error": "旧字符串不存在"}
            
            new_content = content.replace(oldString, newString)
            if len(new_content.encode('utf-8')) > self.MAX_FILE_SIZE_BYTES:
                return {"error": "补丁后内容过大，拒绝写入"}
            
            with open(safe_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(new_content)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def grep(self, pattern: str, path: str = None, include: str = None) -> dict:
        """搜索文件"""
        try:
            if not isinstance(pattern, str) or len(pattern) > 200:
                return {"error": "pattern 为空或过长"}
            try:
                compiled_pattern = re.compile(pattern)
            except re.error:
                return {"error": "无效正则表达式"}

            results = []
            search_path = path or os.getcwd()
            
            # 验证路径安全性
            safe_path = self._sanitize_path(search_path)
            if not safe_path:
                return {"error": "路径不安全"}
            
            # 检查路径是否存在
            if not os.path.exists(safe_path):
                return {"error": "路径不存在"}
            
            # 检查是否是目录
            if not os.path.isdir(safe_path):
                return {"error": "路径不是目录"}
            
            for root, dirs, files in os.walk(safe_path):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if include and not file.endswith(include):
                        continue
                    
                    file_path = os.path.join(root, file)
                    try:
                        if self._sanitize_path(file_path) is None:
                            continue
                        if os.path.getsize(file_path) > self.MAX_FILE_SIZE_BYTES:
                            continue
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines):
                                if compiled_pattern.search(line):
                                    results.append({
                                        "file": file_path,
                                        "line": i + 1,
                                        "content": line.strip()
                                    })
                    except:
                        continue
            
            return {"results": results}
        except Exception as e:
            return {"error": str(e)}

    def glob(self, pattern: str) -> dict:
        """文件匹配"""
        try:
            if not isinstance(pattern, str) or len(pattern) > 200:
                return {"error": "pattern 为空或过长"}
            files = glob(pattern, recursive=True)
            
            # 过滤不安全的文件路径
            safe_files = []
            for file in files:
                safe_path = self._sanitize_path(file)
                if safe_path:
                    safe_files.append(safe_path)
            
            return {"files": safe_files}
        except Exception as e:
            return {"error": str(e)}
