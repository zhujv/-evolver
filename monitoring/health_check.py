# 健康检查脚本

import time
import requests
import logging
import os

logger = logging.getLogger(__name__)

class HealthChecker:
    """健康检查器"""
    
    def __init__(self, config):
        self.config = config
        self.failure_count = 0
    
    def check_health(self):
        """检查系统健康状态"""
        url = f"http://{os.environ.get('EVOLVER_HTTP_HOST', '127.0.0.1')}:{os.environ.get('EVOLVER_PORT', '16888')}/health"
        
        try:
            response = requests.get(url, timeout=self.config.get('timeout', 10))
            response.raise_for_status()
            
            # 重置失败计数
            self.failure_count = 0
            
            # 解析响应
            health_data = response.json()
            logger.info(f"健康检查通过: {health_data}")
            
            return True
            
        except Exception as e:
            self.failure_count += 1
            logger.error(f"健康检查失败: {e}")
            
            # 检查是否达到最大失败次数
            if self.failure_count >= self.config.get('max_failures', 3):
                logger.warning(f"连续失败 {self.failure_count} 次，达到阈值")
                
                # 自动重启
                if self.config.get('auto_restart', True):
                    self.restart_service()
            
            return False
    
    def restart_service(self):
        """重启服务"""
        logger.warning("尝试重启服务...")
        
        # 这里可以实现服务重启逻辑
        # 例如调用系统命令或发送重启请求
        
        # 重置失败计数
        self.failure_count = 0
    
    def run(self):
        """运行健康检查"""
        interval = self.config.get('interval', 30)
        
        while True:
            try:
                self.check_health()
            except Exception as e:
                logger.error(f"健康检查错误: {e}")
            
            time.sleep(interval)

def start_health_check():
    """启动健康检查"""
    from .config import HEALTH_CHECK
    
    if not HEALTH_CHECK.get('enabled', True):
        logger.info('健康检查已禁用')
        return
    
    config = {
        'interval': HEALTH_CHECK.get('interval', 30),
        'timeout': HEALTH_CHECK.get('timeout', 10),
        'max_failures': HEALTH_CHECK.get('max_failures', 3),
        'auto_restart': HEALTH_CHECK.get('auto_restart', True)
    }
    
    checker = HealthChecker(config)
    
    # 在后台线程中运行
    import threading
    checker_thread = threading.Thread(target=checker.run, daemon=True)
    checker_thread.start()
    
    logger.info('健康检查已启动')

if __name__ == '__main__':
    from .config import setup_logging
    setup_logging()
    start_health_check()
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info('健康检查已停止')
