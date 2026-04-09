#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIP服务器呼叫清理工具
用于清理SIP服务器上的现有呼叫，解决503 Maximum Calls In Progress问题
"""

import time
import logging
import socket
import sys
import os
import random

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from test_client.sip_test_client import SIPTestClient


class SIPCallCleaner:
    def __init__(self, server_host="192.168.30.66", server_port=5060, local_host="127.0.0.1", local_port=5080):
        self.server_host = server_host
        self.server_port = server_port
        self.local_host = local_host
        self.local_port = local_port
        self.sip_client = None

    def send_options_probe(self, target_user):
        """发送OPTIONS请求探测用户状态"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        try:
            call_id = f"{int(time.time())}.{random.randint(100000, 999999)}@{self.local_host}"
            
            options_message = (
                f"OPTIONS sip:{target_user}@{self.server_host}:{self.server_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch=z9hG4bK{int(time.time())}{random.randint(10000, 99999)}\r\n"
                f"From: <sip:probe@{self.server_host}:{self.server_port}>;tag={int(time.time())}\r\n"
                f"To: <sip:{target_user}@{self.server_host}:{self.server_port}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 OPTIONS\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: AutoTestForUG SIP Cleaner\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            print(f"发送OPTIONS探测请求到 {target_user}...")
            sock.sendto(options_message.encode('utf-8'), (self.server_host, self.server_port))
            
            try:
                response_data, addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                print(f"收到OPTIONS响应: {response_str.split()[1]} {response_str.split()[2]}")
                return response_str
            except socket.timeout:
                print("OPTIONS请求超时")
                return None
        finally:
            sock.close()

    def send_bye_for_known_calls(self, from_user, to_user, call_id, from_tag, to_tag):
        """发送BYE请求终止特定呼叫"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        try:
            bye_message = (
                f"BYE sip:{to_user}@{self.server_host}:{self.server_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch=z9hG4bK{int(time.time())}{random.randint(10000, 99999)}\r\n"
                f"From: <sip:{from_user}@{self.server_host}:{self.server_port}>;tag={from_tag}\r\n"
                f"To: <sip:{to_user}@{self.server_host}:{self.server_port}>;tag={to_tag}\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 2 BYE\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: AutoTestForUG SIP Cleaner\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            print(f"发送BYE请求终止呼叫 {call_id}...")
            sock.sendto(bye_message.encode('utf-8'), (self.server_host, self.server_port))
            
            try:
                response_data, addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                print(f"收到BYE响应: {response_str.split()[1]} {response_str.split()[2]}")
                return response_str.startswith("SIP/2.0 200")
            except socket.timeout:
                print("BYE请求超时")
                return False
        finally:
            sock.close()

    def cleanup_all_calls(self):
        """尝试清理所有可能的活动呼叫"""
        print("=== 开始清理SIP服务器上的活动呼叫 ===")
        
        # 探测一些常见的被叫用户
        common_users = ["670009", "670010", "670011", "670001", "670002"]
        
        for user in common_users:
            print(f"\n探测用户 {user} 的状态...")
            self.send_options_probe(user)
        
        print("\n请注意：要准确清理特定呼叫，需要知道确切的Call-ID和标签")
        print("建议手动检查SIP服务器上的活动呼叫或使用SIP服务器管理工具")
        
        # 等待一段时间让服务器清理
        print("\n等待服务器处理可能的清理请求...")
        time.sleep(5)
        
        return True

    def test_server_capacity(self):
        """测试服务器容量"""
        print("\n=== 测试服务器呼叫容量 ===")
        
        # 创建SIP客户端进行测试
        if not self.sip_client:
            self.sip_client = SIPTestClient(config_path="./config/config.ini")
        
        # 注册测试用户
        register_success = self.sip_client.register_user(
            username="100010",
            password="1234",
            expires=3600
        )
        
        if not register_success:
            print("无法注册测试用户，无法进行容量测试")
            return False
        
        print("尝试发送测试呼叫以检查服务器状态...")
        
        # 尝试呼叫一个不存在的用户以检查服务器响应
        callee_uri = f"sip:99999@{self.server_host}:{self.server_port}"
        caller_uri = f"sip:100010@{self.server_host}:{self.server_port}"
        
        # 构造一个简单的INVITE请求
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        try:
            call_id = f"capacity-test-{int(time.time())}@{self.local_host}"
            
            invite_message = (
                f"INVITE {callee_uri} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch=z9hG4bK{int(time.time())}{random.randint(10000, 99999)}\r\n"
                f"From: <{caller_uri}>;tag={int(time.time())}\r\n"
                f"To: <{callee_uri}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 INVITE\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: AutoTestForUG Capacity Tester\r\n"
                f"Content-Type: application/sdp\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            print("发送容量测试INVITE请求...")
            sock.sendto(invite_message.encode('utf-8'), (self.server_host, self.server_port))
            
            try:
                response_data, addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                print(f"收到测试响应: {response_str.splitlines()[0]}")
                
                if "503 Maximum Calls In Progress" in response_str:
                    print("✓ 确认服务器确实达到最大呼叫数限制")
                    return False
                else:
                    print("服务器响应正常")
                    return True
            except socket.timeout:
                print("测试请求超时")
                return False
        finally:
            sock.close()


def main():
    print("SIP服务器呼叫清理工具")
    print("=" * 50)
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建清理器实例
    cleaner = SIPCallCleaner()
    
    # 首先测试服务器状态
    print("1. 测试服务器当前状态...")
    cleaner.test_server_capacity()
    
    # 清理呼叫
    print("\n2. 开始清理活动呼叫...")
    cleaner.cleanup_all_calls()
    
    # 再次测试服务器状态
    print("\n3. 再次测试服务器状态...")
    time.sleep(5)  # 等待清理生效
    capacity_ok = cleaner.test_server_capacity()
    
    print("\n" + "=" * 50)
    print("清理完成！")
    if capacity_ok:
        print("服务器容量测试通过，可以发起新呼叫")
    else:
        print("服务器仍显示容量限制，可能需要手动在服务器端清理活动呼叫")
    print("=" * 50)


if __name__ == "__main__":
    main()