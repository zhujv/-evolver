#!/usr/bin/env python3
"""简单压力测试脚本"""

import time
import json
import urllib.request
import urllib.error
import threading

class StressTest:
    """压力测试类"""
    
    def __init__(self, base_url, concurrency=10, total_requests=100):
        """初始化压力测试
        
        Args:
            base_url: 测试的基础URL
            concurrency: 并发数
            total_requests: 总请求数
        """
        self.base_url = base_url
        self.concurrency = concurrency
        self.total_requests = total_requests
        self.results = []
        self.lock = threading.Lock()
        self.semaphore = threading.Semaphore(concurrency)
    
    def make_request(self, method, params, request_id):
        """发送单个请求"""
        with self.semaphore:
            start_time = time.time()
            try:
                data = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": request_id
                }
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                req = urllib.request.Request(
                    self.base_url,
                    data=json.dumps(data).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # 转换为毫秒
                    status = response.status
                    
                    if status == 200:
                        try:
                            result = json.loads(response.read().decode('utf-8'))
                            if 'error' in result:
                                success = False
                                error = result['error'].get('message', 'Unknown error')
                            else:
                                success = True
                                error = None
                        except json.JSONDecodeError:
                            success = False
                            error = 'JSON decode error'
                    else:
                        success = False
                        error = f'HTTP error {status}'
                        
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                success = False
                error = str(e)
            
            with self.lock:
                self.results.append({
                    'request_id': request_id,
                    'success': success,
                    'response_time': response_time,
                    'error': error
                })
    
    def run(self, method, params):
        """运行测试"""
        print(f"开始测试 {method} API...")
        print(f"并发数: {self.concurrency}")
        print(f"总请求数: {self.total_requests}")
        
        start_time = time.time()
        threads = []
        
        for i in range(self.total_requests):
            thread = threading.Thread(
                target=self.make_request,
                args=(method, params, i)
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 分析结果
        self.analyze_results(total_time)
    
    def analyze_results(self, total_time):
        """分析测试结果"""
        total = len(self.results)
        success_count = sum(1 for r in self.results if r['success'])
        failure_count = total - success_count
        
        if success_count > 0:
            response_times = [r['response_time'] for r in self.results if r['success']]
            avg_response_time = sum(response_times) / success_count
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # 计算95%和99%响应时间
            response_times.sort()
            p95_index = int(len(response_times) * 0.95)
            p99_index = int(len(response_times) * 0.99)
            p95_response_time = response_times[p95_index] if p95_index < len(response_times) else 0
            p99_response_time = response_times[p99_index] if p99_index < len(response_times) else 0
        else:
            avg_response_time = 0
            min_response_time = 0
            max_response_time = 0
            p95_response_time = 0
            p99_response_time = 0
        
        success_rate = (success_count / total) * 100 if total > 0 else 0
        qps = total / total_time if total_time > 0 else 0
        
        print(f"\n测试结果:")
        print(f"总请求数: {total}")
        print(f"成功数: {success_count}")
        print(f"失败数: {failure_count}")
        print(f"成功率: {success_rate:.2f}%")
        print(f"总耗时: {total_time:.2f} 秒")
        print(f"QPS: {qps:.2f}")
        print(f"平均响应时间: {avg_response_time:.2f} ms")
        print(f"最小响应时间: {min_response_time:.2f} ms")
        print(f"最大响应时间: {max_response_time:.2f} ms")
        print(f"95%响应时间: {p95_response_time:.2f} ms")
        print(f"99%响应时间: {p99_response_time:.2f} ms")
        
        # 打印失败的请求
        if failure_count > 0:
            print("\n失败的请求:")
            for r in self.results[:5]:  # 只显示前5个失败的请求
                if not r['success']:
                    print(f"  请求 {r['request_id']}: {r['error']}")
            if failure_count > 5:
                print(f"  ... 还有 {failure_count - 5} 个失败的请求")


def main():
    """主函数"""
    base_url = "http://localhost:16888"
    
    # 测试健康检查API
    print("=== 健康检查API压力测试 ===")
    test = StressTest(base_url, concurrency=20, total_requests=100)
    test.run("health", {})
    
    # 测试项目列表API
    print("\n=== 项目列表API压力测试 ===")
    test = StressTest(base_url, concurrency=15, total_requests=80)
    test.run("list_projects", {})
    
    # 测试聊天API
    print("\n=== 聊天API压力测试 ===")
    test = StressTest(base_url, concurrency=10, total_requests=50)
    test.run("chat", {
        "message": "你好，这是一个压力测试消息",
        "session_id": "test_session"
    })


if __name__ == "__main__":
    main()
