#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高级诊断脚本：分析呼叫670010失败的原因
"""

import time
import logging
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_client.sip_test_client import SIPTestClient

def diagnose_670010_issue():
    """诊断670010呼叫问题"""
    print("=== 高级诊断：分析呼叫670010失败的原因 ===")
    
    # 配置详细日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 创建SIP测试客户端
    sip_client = SIPTestClient(config_path="./config/config.ini")
    
    print("\n1. 检查网络连通性...")
    try:
        import socket
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.settimeout(5)
        test_sock.connect(('192.168.30.66', 5060))
        print("✓ 网络连通性正常")
        test_sock.close()
    except Exception as e:
        print(f"✗ 网络连接问题: {e}")
        return False
    
    print("\n2. 执行注册...")
    register_success = sip_client.register_user(
        username="100010",
        password="1234",
        expires=3600
    )
    
    if not register_success:
        print("✗ 注册失败")
        return False
    
    print("✓ 注册成功")
    
    print("\n3. 检查被叫用户可达性...")
    # 尝试发送OPTIONS请求来检查用户可达性
    try:
        import socket
        options_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        options_sock.settimeout(10)
        
        # 构造OPTIONS请求
        options_message = (
            f"OPTIONS sip:670010@192.168.30.66:5060 SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {sip_client.local_host}:{sip_client.local_port};branch=z9hG4bK{int(time.time())}\r\n"
            f"From: <sip:100010@192.168.30.66:5060>;tag={int(time.time())}\r\n"
            f"To: <sip:670010@192.168.30.66:5060>\r\n"
            f"Call-ID: {int(time.time())}@{sip_client.local_host}\r\n"
            f"CSeq: 1 OPTIONS\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: AutoTestForUG Diagnostic Tool\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        print(f"发送OPTIONS请求到 192.168.30.66:5060")
        options_sock.sendto(options_message.encode('utf-8'), ('192.168.30.66', 5060))
        
        try:
            response_data, addr = options_sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            print(f"收到响应: {response_str[:200]}...")
            
            if '200 OK' in response_str:
                print("✓ OPTIONS请求成功 - 被叫用户可达")
            elif '404 Not Found' in response_str:
                print("✗ 被叫用户不存在")
            elif '480 Temporarily Unavailable' in response_str:
                print("⚠ 被叫用户暂时不可用")
            elif '482 Request Merged' in response_str:
                print("⚠ 检测到请求合并问题")
            else:
                print(f"? 未知响应状态: {response_str[:100]}")
        except socket.timeout:
            print("⚠ OPTIONS请求超时 - 被叫用户可能不可达")
        
        options_sock.close()
    except Exception as e:
        print(f"⚠ OPTIONS请求失败: {e}")
    
    print("\n4. 尝试呼叫其他用户以确认问题范围...")
    # 尝试呼叫其他用户，看是否是670010特有的问题
    other_users = ["670001", "670002", "670011"]
    
    for user in other_users:
        print(f"\n  尝试呼叫 {user}...")
        try:
            call_success = sip_client.make_call(
                caller_uri="sip:100010@192.168.30.66:5060",
                callee_uri=f"sip:{user}@192.168.30.66:5060",
                duration=3  # 短时间通话
            )
            
            if call_success:
                print(f"  ✓ 呼叫 {user} 成功")
            else:
                print(f"  ✗ 呼叫 {user} 失败")
        except Exception as e:
            print(f"  ✗ 呼叫 {user} 异常: {e}")
    
    print("\n5. 分析482错误原因...")
    print("  可能的原因:")
    print("  - 被叫用户670010注册在多个设备上，导致请求合并")
    print("  - 服务器检测到重复的呼叫请求")
    print("  - 被叫用户当前处于忙碌状态")
    print("  - 被叫用户不接受来自该主叫的呼叫")
    
    print("\n6. 建议的解决方案...")
    print("  - 检查670010用户是否在多个设备上注册")
    print("  - 确认670010用户当前状态（是否忙碌或离线）")
    print("  - 验证670010是否配置为接受来自100010的呼叫")
    print("  - 检查SIP服务器日志以获取更详细信息")
    
    print("\n=== 诊断完成 ===")
    return True

if __name__ == "__main__":
    diagnose_670010_issue()