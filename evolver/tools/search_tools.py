"""SearchTools - 搜索工具"""

import os
import re


class SearchTools:
    """搜索工具"""
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

    def search_files(self, pattern: str, root_path: str = None) -> dict:
        """搜索文件"""
        try:
            if not isinstance(pattern, str) or len(pattern) > 200:
                return {"error": "pattern 为空或过长"}
            try:
                compiled_pattern = re.compile(pattern)
            except re.error:
                return {"error": "无效正则表达式"}

            results = []
            search_path = root_path or os.getcwd()
            
            # 验证路径安全性
            safe_path = self._sanitize_path(search_path)
            if not safe_path:
                return {"error": "路径不安全"}
            
            # 限制搜索结果数量
            max_results = 100
            result_count = 0
            
            for root, dirs, files in os.walk(safe_path):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if result_count >= max_results:
                        break
                    file_path = os.path.join(root, file)
                    try:
                        # 验证子路径安全
                        if not self._sanitize_path(file_path):
                            continue
                        if os.path.getsize(file_path) > self.MAX_FILE_SIZE_BYTES:
                            continue
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if compiled_pattern.search(content):
                                # 查找匹配的行
                                lines = content.split('\n')
                                for i, line in enumerate(lines):
                                    if compiled_pattern.search(line):
                                        results.append({
                                            "file": file_path,
                                            "line": i + 1,
                                            "content": line.strip()
                                        })
                                        result_count += 1
                                        break
                    except:
                        continue
                
                if result_count >= max_results:
                    break
            
            return {"results": results, "truncated": result_count >= max_results}
        except Exception as e:
            return {"error": str(e)}
    
    def _sanitize_path(self, path: str) -> str:
        """验证路径安全性"""
        safe_path = os.path.realpath(os.path.abspath(os.path.normpath(path)))
        current_dir = os.path.realpath(os.path.abspath(os.getcwd()))
        try:
            if os.path.commonpath([safe_path, current_dir]) != current_dir:
                return None
        except ValueError:
            return None
        return safe_path
