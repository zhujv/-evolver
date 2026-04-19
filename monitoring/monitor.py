# 监控脚本

import time
import psutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, config):
        self.config = config
        self.metrics = []
        self.start_time = time.time()
    
    def collect_metrics(self):
        """收集系统指标"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time() - self.start_time,
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_sent': psutil.net_io_counters().bytes_sent,
            'network_recv': psutil.net_io_counters().bytes_recv
        }
        
        self.metrics.append(metrics)
        
        # 限制历史数据大小
        if len(self.metrics) > self.config.get('history_size', 1000):
            self.metrics = self.metrics[-self.config.get('history_size', 1000):]
        
        return metrics
    
    def check_thresholds(self, metrics):
        """检查阈值"""
        alerts = []
        thresholds = self.config.get('thresholds', {})
        
        if metrics['cpu_usage'] > thresholds.get('cpu_usage', 80):
            alerts.append(f'CPU使用率过高: {metrics["cpu_usage"]:.2f}%')
        
        if metrics['memory_usage'] > thresholds.get('memory_usage', 80):
            alerts.append(f'内存使用率过高: {metrics["memory_usage"]:.2f}%')
        
        return alerts
    
    def run(self):
        """运行监控"""
        interval = self.config.get('interval', 60)
        
        while True:
            try:
                metrics = self.collect_metrics()
                alerts = self.check_thresholds(metrics)
                
                # 记录指标
                logger.info(f"系统指标: CPU={metrics['cpu_usage']:.2f}%, 内存={metrics['memory_usage']:.2f}%")
                
                # 发送告警
                for alert in alerts:
                    logger.warning(f"告警: {alert}")
                    
            except Exception as e:
                logger.error(f"监控错误: {e}")
            
            time.sleep(interval)

def start_monitor():
    """启动监控"""
    from .config import PERFORMANCE_MONITORING, ALERTS
    
    if not PERFORMANCE_MONITORING.get('enabled', True):
        logger.info('性能监控已禁用')
        return
    
    config = {
        'interval': PERFORMANCE_MONITORING.get('interval', 60),
        'history_size': PERFORMANCE_MONITORING.get('history_size', 1000),
        'thresholds': ALERTS.get('thresholds', {})
    }
    
    monitor = SystemMonitor(config)
    
    # 在后台线程中运行
    import threading
    monitor_thread = threading.Thread(target=monitor.run, daemon=True)
    monitor_thread.start()
    
    logger.info('系统监控已启动')

if __name__ == '__main__':
    from .config import setup_logging
    setup_logging()
    start_monitor()
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info('监控已停止')
