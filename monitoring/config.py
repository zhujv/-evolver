# 监控与维护配置

import logging
import os
from logging.handlers import RotatingFileHandler

# 日志配置
def setup_logging():
    """设置日志配置"""
    # 创建日志目录
    log_dir = os.environ.get('EVOLVER_LOG_DIR', os.path.join(os.path.expanduser('~'), '.evolver', 'logs'))
    os.makedirs(log_dir, exist_ok=True)
    
    # 主日志文件
    log_file = os.path.join(log_dir, 'evolver.log')
    
    # 配置根日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # 配置特定模块的日志
    logging.getLogger('evolver.agent').setLevel(logging.INFO)
    logging.getLogger('evolver.memory').setLevel(logging.INFO)
    logging.getLogger('evolver.tools').setLevel(logging.INFO)
    logging.getLogger('evolver.providers').setLevel(logging.INFO)

# 性能监控配置
PERFORMANCE_MONITORING = {
    'enabled': True,
    'metrics': [
        'response_time',
        'request_count',
        'error_rate',
        'memory_usage',
        'cpu_usage'
    ],
    'interval': 60,  # 监控间隔（秒）
    'history_size': 1000  # 历史数据大小
}

# 健康检查配置
HEALTH_CHECK = {
    'enabled': True,
    'interval': 30,  # 健康检查间隔（秒）
    'timeout': 10,  # 检查超时（秒）
    'max_failures': 3,  # 最大失败次数
    'auto_restart': True  # 自动重启
}

# 告警配置
ALERTS = {
    'enabled': True,
    'thresholds': {
        'response_time': 5000,  # 响应时间阈值（毫秒）
        'error_rate': 0.1,  # 错误率阈值
        'memory_usage': 80,  # 内存使用率阈值（%）
        'cpu_usage': 80  # CPU使用率阈值（%）
    },
    'notification_channels': [
        'console'  # 可扩展为 email、webhook 等
    ]
}
