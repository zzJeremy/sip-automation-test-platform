#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIP呼叫测试执行脚本
此脚本将启动本地SIP服务器并在其上执行呼叫测试
"""

import subprocess
import sys
import os
import threading
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def start_sip_server():
    """启动SIP服务器的函数"""
    server_script = str(project_root / "start_local_sip_server.py")
    
    # 启动SIP服务器进程
    process = subprocess.Popen([sys.executable, server_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # 等待服务器启动
    time.sleep(3)
    
    return process


def run_call_test():
    """运行呼叫测试"""
    test_script = str(project_root / "execute_simple_call.py")
    
    # 执行呼叫测试
    result = subprocess.run([sys.executable, test_script], capture_output=True, text=True)
    
    print("呼叫测试输出:")
    print(result.stdout)
    if result.stderr:
        print("错误信息:")
        print(result.stderr)
    
    return result.returncode == 0


def main():
    """主函数 - 执行完整的呼叫测试流程"""
    print("=" * 60)
    print("SIP呼叫测试执行器")
    print("=" * 60)
    
    print("\n1. 启动本地SIP服务器...")
    server_process = start_sip_server()
    
    if server_process.poll() is not None:
        print("无法启动SIP服务器")
        return False
    
    print("SIP服务器已启动")
    
    try:
        print("\n2. 等待服务器完全就绪...")
        time.sleep(3)
        
        print("\n3. 执行呼叫测试...")
        test_success = run_call_test()
        
        if test_success:
            print("\n✓ 呼叫测试执行成功!")
        else:
            print("\n✗ 呼叫测试执行失败!")
            
        return test_success
        
    finally:
        print("\n4. 停止SIP服务器...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        
        print("SIP服务器已停止")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)