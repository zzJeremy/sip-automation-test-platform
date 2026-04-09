#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析SIP呼叫问题的脚本
"""

import time
import logging
from test_client.sip_test_client import SIPTestClient

def analyze_call_issue():
    """分析呼叫问题"""
    print("=== 分析SIP呼叫问题 ===")
    print("问题：用户100010无法成功呼叫670009")
    print("现象：收到482 Request merged响应")
    print()
    
    # 设置详细日志
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 创建SIP测试客户端
    sip_client = SIPTestClient(config_path="./config/config.ini")
    
    # 执行注册
    print("1. 执行注册...")
    register_success = sip_client.register_user(
        username="100010",
        password="1234",
        expires=3600
    )
    
    if not register_success:
        print("注册失败，停止测试")
        return
    
    print("注册成功")
    print()
    
    # 分析SIP服务器状态
    print("2. 分析SIP服务器状态...")
    print(f"   服务器: {sip_client.sip_server_host}:{sip_client.sip_server_port}")
    print(f"   本地地址: {sip_client.local_host}:{sip_client.local_port}")
    print()
    
    # 尝试检查被叫用户状态
    print("3. 尝试检查被叫用户670009的状态...")
    
    # 尝试OPTIONS请求检查用户可达性
    try:
        # 直接使用底层方法发送OPTIONS请求
        import socket
        
        # 创建OPTIONS消息
        call_id = f"{int(time.time())}.{hash('options_check') % 1000000}"
        branch = f"z9hG4bK{int(time.time())}{hash('options') % 1000000}"
        from_tag = f"tag{int(time.time())}{hash('from') % 1000000}"
        
        options_msg = (
            f"OPTIONS sip:670009@{sip_client.sip_server_host}:{sip_client.sip_server_port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {sip_client.local_host}:{sip_client.local_port};branch={branch};rport\r\n"
            f"From: <sip:test@{sip_client.sip_server_host}:{sip_client.sip_server_port}>;tag={from_tag}\r\n"
            f"To: <sip:670009@{sip_client.sip_server_host}:{sip_client.sip_server_port}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 OPTIONS\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: AutoTestForUG SIP Client 1.0\r\n"
            f"Accept: application/sdp\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        print(f"发送OPTIONS请求检查用户670009的可达性...")
        print(f"OPTIONS消息:\n{options_msg}")
        
        # 发送OPTIONS请求
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        sock.sendto(options_msg.encode('utf-8'), 
                   (sip_client.sip_server_host, sip_client.sip_server_port))
        
        try:
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            print(f"收到OPTIONS响应:\n{response_str}")
            
            # 解析响应
            lines = response_str.split('\r\n')
            if lines:
                status_line = lines[0]
                print(f"状态行: {status_line}")
                
        except socket.timeout:
            print("OPTIONS请求超时，用户可能不可达")
        
        sock.close()
        
    except Exception as e:
        print(f"发送OPTIONS请求时出错: {e}")
    
    print()
    
    # 分析482响应的可能原因
    print("4. 分析482 Request merged响应的可能原因:")
    print("   - 被叫用户670009当前处于忙碌状态")
    print("   - 被叫用户670009当前已登录多个设备，产生冲突")
    print("   - 被叫用户670009当前不可用或未注册")
    print("   - 网络问题导致请求重复发送")
    print("   - SIP服务器配置问题")
    print()
    
    # 提供解决方案建议
    print("5. 解决方案建议:")
    print("   - 检查被叫用户670009是否已正确注册到SIP服务器")
    print("   - 确认被叫用户670009当前状态（是否忙碌或离线）")
    print("   - 尝试联系其他可用的被叫用户进行测试")
    print("   - 检查SIP服务器日志以获取更多信息")
    print()
    
    # 检查配置
    print("6. 当前配置检查:")
    print(f"   主叫用户: 100010")
    print(f"   被叫用户: 670009")
    print(f"   服务器: {sip_client.sip_server_host}:{sip_client.sip_server_port}")
    print(f"   当前活动呼叫: {len(sip_client.active_calls)}")
    for call_id, call_info in sip_client.active_calls.items():
        print(f"     - {call_id}: {call_info}")
    print()
    
    print("=== 分析完成 ===")

def test_alternative_user():
    """尝试呼叫其他用户以确定问题范围"""
    print("=== 尝试呼叫其他用户 ===")
    
    sip_client = SIPTestClient(config_path="./config/config.ini")
    
    # 注册用户
    register_success = sip_client.register_user(
        username="100010",
        password="1234",
        expires=3600
    )
    
    if not register_success:
        print("注册失败")
        return
    
    print("注册成功，尝试呼叫其他用户...")
    
    # 尝试呼叫其他可能存在的用户
    alternative_users = ["670001", "670002", "670008", "670010"]
    
    for user in alternative_users:
        print(f"\n尝试呼叫用户: {user}")
        callee_uri = f"sip:{user}@{sip_client.sip_server_host}:{sip_client.sip_server_port}"
        caller_uri = f"sip:100010@{sip_client.sip_server_host}:{sip_client.sip_server_port}"
        
        # 使用较低的超时时间快速测试
        import socket
        import time
        
        # 创建INVITE消息
        call_id = f"{int(time.time())}.{hash(user) % 1000000}"
        branch = f"z9hG4bK{int(time.time())}{hash(user) % 1000000}"
        from_tag = f"tag{int(time.time())}{hash(user) % 1000000}"
        
        invite_msg = (
            f"INVITE {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {sip_client.local_host}:{sip_client.local_port};branch={branch};rport\r\n"
            f"From: <{caller_uri}>;tag={from_tag}\r\n"
            f"To: <{callee_uri}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: AutoTestForUG SIP Client 1.0\r\n"
            f"Contact: <{caller_uri}>\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        # 发送INVITE请求
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)  # 较短的超时时间
        
        try:
            sock.sendto(invite_msg.encode('utf-8'), 
                       (sip_client.sip_server_host, sip_client.sip_server_port))
            
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                
                # 解析响应
                lines = response_str.split('\r\n')
                if lines:
                    status_line = lines[0]
                    print(f"   响应: {status_line}")
                    
                    # 检查响应类型
                    if "200 OK" in status_line:
                        print(f"   ✓ 用户 {user} 响应正常")
                    elif "180" in status_line or "183" in status_line:
                        print(f"   ✓ 用户 {user} 正在振铃")
                    elif "486" in status_line:
                        print(f"   ✗ 用户 {user} 忙碌 (Busy Here)")
                    elif "404" in status_line:
                        print(f"   ✗ 用户 {user} 不存在 (Not Found)")
                    elif "482" in status_line:
                        print(f"   ✗ 用户 {user} 请求合并 (Request Merged)")
                    elif "408" in status_line:
                        print(f"   ? 用户 {user} 请求超时")
                    else:
                        print(f"   ? 用户 {user} 其他响应: {status_line}")
                        
            except socket.timeout:
                print(f"   ? 用户 {user} 无响应 (超时)")
                
        except Exception as e:
            print(f"   ? 用户 {user} 发生错误: {e}")
        finally:
            sock.close()

if __name__ == "__main__":
    print("选择分析模式:")
    print("1. 详细分析呼叫问题")
    print("2. 测试其他用户")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "2":
        test_alternative_user()
    else:
        analyze_call_issue()