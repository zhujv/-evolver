#!/usr/bin/env python3
"""压力测试脚本"""

import asyncio
import time
import json
import aiohttp

async def stress_test():
    """执行压力测试"""
    print("开始压力测试...")
    
    # 测试配置
    base_url = "http://localhost:16888"
    test_cases = [
        {
            "name": "聊天API压力测试",
            "method": "chat",
            "params": {
                "message": "你好，这是一个压力测试消息",
                "session_id": "test_session"
            },
            "concurrency": 10,
            "requests": 50
        },
        {
            "name": "项目列表API压力测试",
            "method": "list_projects",
            "params": {},
            "concurrency": 20,
            "requests": 100
        },
        {
            "name": "健康检查API压力测试",
            "method": "health",
            "params": {},
            "concurrency": 50,
            "requests": 200
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")
        print(f"并发数: {test_case['concurrency']}")
        print(f"总请求数: {test_case['requests']}")
        
        # 执行测试
        results = await run_test(
            base_url,
            test_case['method'],
            test_case['params'],
            test_case['concurrency'],
            test_case['requests']
        )
        
        # 分析结果
        analyze_results(results)

async def run_test(base_url, method, params, concurrency, total_requests):
    """运行测试"""
    results = []
    semaphore = asyncio.Semaphore(concurrency)
    
    async def make_request(session, request_id):
        """发送单个请求"""
        async with semaphore:
            start_time = time.time()
            try:
                data = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": request_id
                }
                
                async with session.post(base_url, json=data, timeout=30) as response:
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # 转换为毫秒
                    status = response.status
                    
                    if status == 200:
                        try:
                            result = await response.json()
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
                        
                    results.append({
                        'request_id': request_id,
                        'success': success,
                        'response_time': response_time,
                        'error': error
                    })
                    
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                results.append({
                    'request_id': request_id,
                    'success': False,
                    'response_time': response_time,
                    'error': str(e)
                })
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(total_requests):
            task = asyncio.create_task(make_request(session, i))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
    
    return results


def analyze_results(results):
    """分析测试结果"""
    total = len(results)
    success_count = sum(1 for r in results if r['success'])
    failure_count = total - success_count
    
    if success_count > 0:
        response_times = [r['response_time'] for r in results if r['success']]
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
    
    print(f"总请求数: {total}")
    print(f"成功数: {success_count}")
    print(f"失败数: {failure_count}")
    print(f"成功率: {success_rate:.2f}%")
    print(f"平均响应时间: {avg_response_time:.2f} ms")
    print(f"最小响应时间: {min_response_time:.2f} ms")
    print(f"最大响应时间: {max_response_time:.2f} ms")
    print(f"95%响应时间: {p95_response_time:.2f} ms")
    print(f"99%响应时间: {p99_response_time:.2f} ms")
    
    # 打印失败的请求
    if failure_count > 0:
        print("\n失败的请求:")
        for r in results[:5]:  # 只显示前5个失败的请求
            if not r['success']:
                print(f"  请求 {r['request_id']}: {r['error']}")
        if failure_count > 5:
            print(f"  ... 还有 {failure_count - 5} 个失败的请求")


if __name__ == "__main__":
    asyncio.run(stress_test())
