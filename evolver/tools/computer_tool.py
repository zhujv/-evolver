"""ComputerTool - 电脑操作工具"""

import os
import webbrowser
import subprocess
import platform
import socket
import uuid
from typing import Dict, List, Optional


class ComputerTool:
    """电脑操作工具 - 支持打开浏览器、应用程序、文件等"""

    def __init__(self):
        self.system = platform.system()
        self._init_browser_paths()

    def _init_browser_paths(self):
        """初始化浏览器路径"""
        self.browser_paths = {}

        if self.system == "Windows":
            self.browser_paths = {
                "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "edge": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                "firefox": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            }
        elif self.system == "Darwin":
            self.browser_paths = {
                "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "safari": "/Applications/Safari.app/Contents/MacOS/Safari",
                "firefox": "/Applications/Firefox.app/Contents/MacOS/firefox",
            }
        else:
            self.browser_paths = {
                "firefox": "firefox",
                "chrome": "google-chrome",
            }

    def open_url(self, url: str, browser: str = None) -> Dict:
        """打开URL链接"""
        try:
            if not url:
                return {"error": "URL不能为空"}

            if not url.startswith(("http://", "https://", "file://")):
                url = "https://" + url

            if browser and browser.lower() in self.browser_paths:
                browser_path = self.browser_paths[browser.lower()]
                if os.path.exists(browser_path):
                    if self.system == "Windows":
                        subprocess.Popen([browser_path, url], shell=False)
                    else:
                        subprocess.Popen(["open", "-a", browser_path, url])
                    return {"success": True, "message": f"使用 {browser} 打开: {url}"}
                else:
                    return {"error": f"未找到 {browser}，将使用默认浏览器"}

            webbrowser.open(url)
            return {"success": True, "message": f"已在默认浏览器打开: {url}"}

        except Exception as e:
            return {"error": f"打开URL失败: {str(e)}"}

    def open_browser(self, url: str = None, browser: str = "default") -> Dict:
        """打开浏览器"""
        if url is None:
            url = "https://www.google.com"

        return self.open_url(url, browser)

    def open_file(self, path: str) -> Dict:
        """打开文件（使用默认应用程序）"""
        try:
            if not path:
                return {"error": "文件路径不能为空"}

            abs_path = os.path.abspath(path)

            if not os.path.exists(abs_path):
                return {"error": f"文件不存在: {abs_path}"}

            if self.system == "Windows":
                os.startfile(abs_path)
            elif self.system == "Darwin":
                subprocess.run(["open", abs_path])
            else:
                subprocess.run(["xdg-open", abs_path])

            return {"success": True, "message": f"已打开: {abs_path}"}

        except Exception as e:
            return {"error": f"打开文件失败: {str(e)}"}

    def open_folder(self, path: str = None) -> Dict:
        """打开文件夹"""
        try:
            if path is None:
                path = os.getcwd()

            abs_path = os.path.abspath(path)

            if not os.path.exists(abs_path):
                return {"error": f"文件夹不存在: {abs_path}"}

            if self.system == "Windows":
                os.startfile(abs_path)
            elif self.system == "Darwin":
                subprocess.run(["open", abs_path])
            else:
                subprocess.run(["xdg-open", abs_path])

            return {"success": True, "message": f"已打开文件夹: {abs_path}"}

        except Exception as e:
            return {"error": f"打开文件夹失败: {str(e)}"}

    def open_app(self, app_name: str) -> Dict:
        """打开应用程序"""
        try:
            if not app_name:
                return {"error": "应用程序名称不能为空"}

            if self.system == "Windows":
                try:
                    result = subprocess.run(
                        ["where", app_name],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        app_path = result.stdout.strip().split("\n")[0]
                        subprocess.Popen([app_path], shell=False)
                        return {"success": True, "message": f"已启动: {app_name}"}

                    subprocess.Popen(
                        ["cmd", "/c", "start", "", app_name],
                        shell=True
                    )
                    return {"success": True, "message": f"已启动: {app_name}"}

                except Exception as e:
                    return {"error": f"启动应用失败: {str(e)}"}

            elif self.system == "Darwin":
                subprocess.run(["open", "-a", app_name])
                return {"success": True, "message": f"已启动: {app_name}"}

            else:
                subprocess.run([app_name])
                return {"success": True, "message": f"已启动: {app_name}"}

        except Exception as e:
            return {"error": f"启动应用失败: {str(e)}"}

    def take_screenshot(self, save_path: str = None) -> Dict:
        """截图功能"""
        try:
            from PIL import Image, ImageGrab

            if save_path is None:
                save_path = os.path.join(os.getcwd(), f"screenshot_{int(time.time())}.png")

            screenshot = ImageGrab.grab()
            screenshot.save(save_path)

            return {"success": True, "message": f"截图已保存: {save_path}"}

        except ImportError:
            return {"error": "需要安装 Pillow 库: pip install pillow"}
        except Exception as e:
            return {"error": f"截图失败: {str(e)}"}

    def get_system_info(self) -> Dict:
        """获取系统信息"""
        try:
            info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_count": os.cpu_count(),
                "memory_total": psutil.virtual_memory().total if "psutil" in dir() else "unknown",
                "hostname": socket.gethostname(),
                "ip_address": socket.gethostbyname(socket.gethostname()),
            }

            if self.system == "Windows":
                info["username"] = os.environ.get("USERNAME", "unknown")
            else:
                info["username"] = os.environ.get("USER", "unknown")

            return {"success": True, "info": info}

        except Exception as e:
            return {"error": f"获取系统信息失败: {str(e)}"}

    def list_browsers(self) -> Dict:
        """列出可用的浏览器"""
        available = {}

        for name, path in self.browser_paths.items():
            if os.path.exists(path):
                available[name] = path

        if not available:
            available["default"] = "system default browser"

        return {"success": True, "browsers": available}

    def search_web(self, query: str, engine: str = "google") -> Dict:
        """网页搜索"""
        if not query:
            return {"error": "搜索关键词不能为空"}

        engines = {
            "google": "https://www.google.com/search?q=",
            "bing": "https://www.bing.com/search?q=",
            "baidu": "https://www.baidu.com/s?wd=",
            "duckduckgo": "https://duckduckgo.com/?q=",
        }

        if engine.lower() not in engines:
            engine = "google"

        url = engines[engine.lower()] + urllib.parse.quote(query)

        return self.open_url(url)

    def execute_command(self, command: str) -> Dict:
        """执行系统命令"""
        try:
            if not command:
                return {"error": "命令不能为空"}

            dangerous_commands = ["rm -rf", "del /f /q", "format", "mkfs", "> /dev/null"]
            for dangerous in dangerous_commands:
                if dangerous in command.lower():
                    return {"error": f"危险命令被拒绝: {dangerous}"}

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout if result.stdout else result.stderr

            if len(output) > 1000:
                output = output[:500] + "\n... [输出截断] ...\n" + output[-500:]

            return {
                "success": True,
                "returncode": result.returncode,
                "output": output
            }

        except subprocess.TimeoutExpired:
            return {"error": "命令执行超时（30秒）"}
        except Exception as e:
            return {"error": f"命令执行失败: {str(e)}"}

    def get_clipboard(self) -> Dict:
        """获取剪贴板内容"""
        try:
            import pyperclip
            content = pyperclip.paste()
            return {"success": True, "content": content}
        except ImportError:
            try:
                import subprocess
                if self.system == "Windows":
                    result = subprocess.run(
                        ["powershell", "-command", "Get-Clipboard"],
                        capture_output=True,
                        text=True
                    )
                    return {"success": True, "content": result.stdout.strip()}
                else:
                    result = subprocess.run(
                        ["pbpaste"],
                        capture_output=True,
                        text=True
                    )
                    return {"success": True, "content": result.stdout.strip()}
            except:
                return {"error": "无法获取剪贴板内容"}
        except Exception as e:
            return {"error": f"获取剪贴板失败: {str(e)}"}

    def set_clipboard(self, content: str) -> Dict:
        """设置剪贴板内容"""
        try:
            import pyperclip
            pyperclip.copy(content)
            return {"success": True, "message": "剪贴板内容已设置"}
        except ImportError:
            try:
                if self.system == "Windows":
                    subprocess.run(
                        ["powershell", "-command", f"Set-Clipboard -Value '{content}'"],
                        capture_output=True
                    )
                else:
                    subprocess.run(["pbcopy"], input=content.encode(), check=True)
                return {"success": True, "message": "剪贴板内容已设置"}
            except:
                return {"error": "无法设置剪贴板内容"}
        except Exception as e:
            return {"error": f"设置剪贴板失败: {str(e)}"}


import urllib.parse
import time

computer_tool = ComputerTool()


if __name__ == "__main__":
    tool = ComputerTool()

    print("=== 电脑操作工具测试 ===\n")

    print("1. 系统信息:")
    print(tool.get_system_info())

    print("\n2. 可用浏览器:")
    print(tool.list_browsers())

    print("\n3. 打开文件夹测试:")
    print(tool.open_folder())
