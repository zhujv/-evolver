# 监控模块初始化

from .config import setup_logging
from .monitor import start_monitor
from .health_check import start_health_check

def init_monitoring():
    """初始化监控系统"""
    # 设置日志
    setup_logging()
    
    # 启动监控
    start_monitor()
    
    # 启动健康检查
    start_health_check()
    
    print("监控系统已初始化")

if __name__ == '__main__':
    init_monitoring()
