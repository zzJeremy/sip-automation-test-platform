import requests
import json
import time
import threading

# 测试在执行过程中访问API是否会导致服务器内部错误
base_url = "http://localhost:5000"

def create_long_running_execution():
    """创建一个长时间运行的执行任务"""
    try:
        # 创建一个执行任务，让它运行较长时间
        response = requests.post(
            f"{base_url}/api/executions",
            json={
                "suiteIds": [], 
                "concurrentCount": 1, 
                "environment": "test"
            },
            timeout=10
        )
        print(f"创建执行任务: {response.status_code}")
        if response.status_code == 201:
            execution_data = response.json()
            execution_id = execution_data['id']
            print(f"执行ID: {execution_id}")
            return execution_id
        return None
    except Exception as e:
        print(f"创建执行任务失败: {e}")
        return None

def poll_execution_status(execution_id):
    """轮询执行状态"""
    for i in range(10):  # 轮询10次
        try:
            response = requests.get(f"{base_url}/api/executions/{execution_id}/status", timeout=5)
            print(f"执行状态查询 {i+1}: {response.status_code}")
            if response.status_code == 200:
                print(f"  状态: {response.json()}")
        except Exception as e:
            print(f"执行状态查询 {i+1} 失败: {e}")
        time.sleep(0.5)

def test_concurrent_api_calls():
    """测试并发API调用"""
    # 获取仪表板统计信息
    try:
        response = requests.get(f"{base_url}/api/dashboard/stats", timeout=5)
        print(f"仪表板统计: {response.status_code}")
    except Exception as e:
        print(f"仪表板统计失败: {e}")
    
    # 获取执行列表
    try:
        response = requests.get(f"{base_url}/api/executions", timeout=5)
        print(f"执行列表: {response.status_code}")
        if response.status_code == 200:
            print(f"  执行数: {len(response.json())}")
    except Exception as e:
        print(f"执行列表失败: {e}")

def run_concurrent_tests():
    """运行并发测试"""
    print("开始创建执行任务...")
    execution_id = create_long_running_execution()
    
    if execution_id:
        print(f"\n开始并发测试，执行ID: {execution_id}")
        
        # 创建多个线程来模拟并发访问
        threads = []
        
        # 线程1: 轮询执行状态
        t1 = threading.Thread(target=poll_execution_status, args=(execution_id,))
        threads.append(t1)
        
        # 线程2-4: 并发API调用
        for i in range(3):
            t = threading.Thread(target=test_concurrent_api_calls)
            threads.append(t)
        
        # 启动所有线程
        for t in threads:
            t.start()
            time.sleep(0.2)  # 错开启动时间
        
        # 等待所有线程完成
        for t in threads:
            t.join()
    
    print("\n并发测试完成")

if __name__ == "__main__":
    run_concurrent_tests()