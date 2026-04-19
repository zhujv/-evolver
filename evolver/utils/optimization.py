import time
import json
import logging
import asyncio
from typing import List, Dict, Optional, Any
from collections import deque

logger = logging.getLogger(__name__)


class RequestQueue:
    """请求队列，用于管理并发请求"""
    
    def __init__(self, max_concurrent: int = 8):
        """初始化请求队列
        
        Args:
            max_concurrent: 最大并发请求数
        """
        self.max_concurrent = max_concurrent
        self.queue = deque()
        self.running = 0
        self.lock = asyncio.Lock()
        self.processing = False
    
    async def add_request(self, request_func, *args, **kwargs):
        """添加请求到队列并返回结果
        
        Args:
            request_func: 请求处理函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            请求处理结果
        """
        # 创建future对象用于返回结果
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        # 将请求添加到队列
        await self.lock.acquire()
        self.queue.append((request_func, args, kwargs, future))
        self.lock.release()
        
        # 开始处理队列
        await self._process_queue()
        
        # 等待结果
        result = await future
        
        # 检查结果是否为字典，如果是，直接返回
        if isinstance(result, dict):
            logger.info(f"返回字典结果: {result}")
            return result
        
        # 检查结果是否为协程对象，如果是，等待它
        while asyncio.iscoroutine(result):
            logger.info("结果是协程对象，等待执行")
            result = await result
            
            # 检查结果是否为字典，如果是，直接返回
            if isinstance(result, dict):
                logger.info(f"返回字典结果: {result}")
                return result
            
            # 检查结果是否不再是协程对象
            if not asyncio.iscoroutine(result):
                break
        
        # 再次检查结果是否为字典
        if isinstance(result, dict):
            logger.info(f"返回字典结果: {result}")
            return result
        
        # 否则，返回一个错误信息
        logger.info(f"返回错误信息: {type(result)}")
        return {"error": f"Invalid result type: {type(result)}"}

    
    async def _process_queue(self):
        """处理队列中的请求"""
        await self.lock.acquire()
        
        # 如果已经在处理或队列为空，直接返回
        if self.processing or not self.queue:
            self.lock.release()
            return
        
        # 标记为正在处理
        self.processing = True
        self.lock.release()
        
        try:
            while True:
                await self.lock.acquire()
                
                # 检查是否有请求且未达到最大并发数
                if not self.queue or self.running >= self.max_concurrent:
                    self.processing = False
                    self.lock.release()
                    break
                
                # 取出一个请求
                request_func, args, kwargs, future = self.queue.popleft()
                self.running += 1
                self.lock.release()
                
                # 异步执行请求
                asyncio.create_task(self._execute_request(request_func, args, kwargs, future))
                
                # 短暂暂停，避免CPU占用过高
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"处理请求队列时出错: {e}")
            await self.lock.acquire()
            self.processing = False
            self.lock.release()
    
    async def _execute_request(self, request_func, args, kwargs, future):
        """执行单个请求
        
        Args:
            request_func: 请求处理函数
            args: 位置参数
            kwargs: 关键字参数
            future: 用于返回结果的future
        """
        try:
            # 执行请求
            logger.info(f"执行请求: {request_func.__name__ if hasattr(request_func, '__name__') else str(request_func)}")
            logger.info(f"参数: args={args}, kwargs={kwargs}")
            logger.info(f"请求函数类型: {type(request_func)}")
            
            # 检查函数是否为异步函数
            is_async = asyncio.iscoroutinefunction(request_func)
            logger.info(f"是否为异步函数: {is_async}")
            
            if is_async:
                logger.info("执行异步函数")
                result = await request_func(*args, **kwargs)
                logger.info(f"异步函数执行结果: {result}")
                logger.info(f"异步函数执行结果类型: {type(result)}")
            else:
                # 对于非异步函数，直接调用
                logger.info("执行同步函数")
                result = request_func(*args, **kwargs)
                logger.info(f"同步函数执行结果: {result}")
                logger.info(f"同步函数执行结果类型: {type(result)}")
            
            # 检查结果是否为协程对象，如果是，等待它
            while asyncio.iscoroutine(result):
                logger.info("结果是协程对象，等待执行")
                result = await result
                logger.info(f"协程对象执行结果: {result}")
                logger.info(f"协程对象执行结果类型: {type(result)}")
                
                # 确保结果不是字典，避免"object dict can't be used in 'await' expression"错误
                if isinstance(result, dict):
                    break
            
            # 检查结果是否为字典，如果不是，转换为字典
            if not isinstance(result, dict):
                logger.info(f"结果不是字典，转换为字典: {result}")
                result = {"error": f"Invalid result type: {type(result)}"}
            
            logger.info(f"最终请求执行结果: {result}")
            logger.info(f"最终请求执行结果类型: {type(result)}")
            future.set_result(result)
        except Exception as e:
            logger.error(f"执行请求时出错: {e}")
            logger.error(f"错误类型: {type(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 捕获异常并返回错误信息，而不是设置异常
            error_result = {"error": str(e)}
            future.set_result(error_result)
        finally:
            # 减少运行计数并重新处理队列
            await self.lock.acquire()
            self.running -= 1
            self.lock.release()
            await self._process_queue()


class ResponseCache:
    """响应缓存，用于缓存常见请求的响应"""
    
    def __init__(self, max_size: int = 500, ttl: int = 14400):
        """初始化响应缓存
        
        Args:
            max_size: 缓存最大容量
            ttl: 缓存过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_order = deque()
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的响应，如果不存在或已过期则返回None
        """
        await self.lock.acquire()
        try:
            if key in self.cache:
                value, timestamp = self.cache[key]
                # 检查是否过期
                if time.time() - timestamp < self.ttl:
                    # 更新访问顺序
                    if key in self.access_order:
                        self.access_order.remove(key)
                    self.access_order.append(key)
                    return value
                else:
                    # 移除过期缓存
                    del self.cache[key]
                    if key in self.access_order:
                        self.access_order.remove(key)
        finally:
            self.lock.release()
        return None
    
    async def set(self, key: str, value: Any):
        """设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        await self.lock.acquire()
        try:
            # 如果缓存已满，移除最久未使用的项
            if len(self.cache) >= self.max_size:
                oldest_key = self.access_order.popleft()
                if oldest_key in self.cache:
                    del self.cache[oldest_key]
            
            # 设置缓存
            self.cache[key] = (value, time.time())
            
            # 更新访问顺序
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
        finally:
            self.lock.release()
    
    async def clear(self):
        """清空缓存"""
        await self.lock.acquire()
        try:
            self.cache.clear()
            self.access_order.clear()
        finally:
            self.lock.release()


class RateLimiter:
    """速率限制器，用于控制请求速率"""
    
    def __init__(self, max_calls: int, period: int):
        """初始化速率限制器
        
        Args:
            max_calls: 时间窗口内最大调用次数
            period: 时间窗口大小（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """获取调用许可
        
        等待直到可以进行下一次调用
        """
        await self.lock.acquire()
        try:
            now = time.time()
            
            # 移除过期的调用记录
            while self.calls and now - self.calls[0] > self.period:
                self.calls.popleft()
            
            # 如果达到速率限制，等待
            if len(self.calls) >= self.max_calls:
                wait_time = self.period - (now - self.calls[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            # 记录本次调用
            self.calls.append(time.time())
        finally:
            self.lock.release()
