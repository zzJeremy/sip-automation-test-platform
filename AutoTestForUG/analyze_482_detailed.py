#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIP 482 Request Merged 详细分析工具
用于深入分析和解决呼叫时出现的482响应问题
"""

import socket
import time
import logging
import hashlib
import random
from urllib.parse import urlparse
import configparser

class SIP482DetailedAnalyzer:
    def __init__(self, config_path="./config/config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        self.sip_server_host = self.config.get('TEST_CLIENT', 'sip_server_host', fallback='127.0.0.1')
        self.sip_server_port = int(self.config.get('TEST_CLIENT', 'sip_server_port', fallback=5060))
        self.local_host = self.config.get('TEST_CLIENT', 'local_host', fallback='127.0.0.1')
        self.local_port = int(self.config.get('TEST_CLIENT', 'local_port', fallback=5080))
        
        # 设置日志
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def create_unique_branch(self):
        """创建唯一的Branch ID"""
        return f"z9hG4bK{int(time.time())}{random.randint(100000, 999999)}"
        
    def create_from_tag(self):
        """创建From标签"""
        return f"tag{int(time.time())}{random.randint(100000, 999999)}"
        
    def create_call_id(self):
        """创建Call-ID"""
        return f"{int(time.time())}.{hash(str(random.random())) % 1000000}@{self.local_host}"
    
    def send_invite_with_unique_params(self, caller_user, callee_user, password, test_num=1):
        """发送带有唯一参数的INVITE请求以测试482问题"""
        print(f"=== 测试 {test_num}: 发送带有唯一参数的INVITE请求 ===")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        try:
            call_id = self.create_call_id()
            branch = self.create_unique_branch()
            from_tag = self.create_from_tag()
            
            invite_msg = (
                f"INVITE sip:{callee_user}@{self.sip_server_host}:{self.sip_server_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
                f"From: <sip:{caller_user}@{self.sip_server_host}:{self.sip_server_port}>;tag={from_tag}\r\n"
                f"To: <sip:{callee_user}@{self.sip_server_host}:{self.sip_server_port}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 INVITE\r\n"
                f"Max-Forwards: 70\r\n"
                f"Contact: <sip:{caller_user}@{self.local_host}:{self.local_port}>\r\n"
                f"Content-Type: application/sdp\r\n"
                f"User-Agent: SIP 482 Analyzer Test {test_num}\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            print(f"发送INVITE请求:\n{invite_msg}")
            
            sock.sendto(invite_msg.encode('utf-8'), (self.sip_server_host, self.sip_server_port))
            
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                
                print(f"收到响应:\n{response_str}")
                
                # 检查响应状态
                lines = response_str.split('\r\n')
                if lines:
                    status_line = lines[0]
                    print(f"状态行: {status_line}")
                    
                    if '482' in status_line:
                        print(f"⚠️  收到482响应 - Request Merged/Loop Detected")
                        return "482_LOOP_DETECTED"
                    elif '200 OK' in status_line:
                        print(f"✅ 收到200 OK响应")
                        return "200_OK"
                    elif '180' in status_line or '183' in status_line:
                        print(f"响铃中...")
                        return "RINGING"
                    elif '407' in status_line or '401' in status_line:
                        print(f"需要认证")
                        return "AUTH_REQUIRED"
                    else:
                        print(f"其他响应: {status_line}")
                        return status_line
            except socket.timeout:
                print("请求超时")
                return "TIMEOUT"
                
        except Exception as e:
            print(f"发送INVITE请求时出错: {e}")
            return f"ERROR: {e}"
        finally:
            sock.close()
    
    def send_multiple_invites(self, caller_user, callee_user, password, num_requests=3):
        """发送多个INVITE请求以重现482问题"""
        print(f"=== 发送 {num_requests} 个连续的INVITE请求以测试482问题 ===")
        
        results = []
        for i in range(num_requests):
            print(f"\n--- 请求 {i+1}/{num_requests} ---")
            result = self.send_invite_with_unique_params(caller_user, callee_user, password, i+1)
            results.append(result)
            
            # 在请求之间添加短暂延迟
            time.sleep(2)
        
        print(f"\n=== 结果汇总 ===")
        for i, result in enumerate(results, 1):
            print(f"请求 {i}: {result}")
        
        return results
    
    def check_registration_duplicates(self, user, password):
        """检查用户是否存在重复注册"""
        print(f"=== 检查用户 {user} 是否存在重复注册 ===")
        
        # 发送OPTIONS请求，服务器可能会返回所有注册的位置信息
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        try:
            call_id = self.create_call_id()
            branch = self.create_unique_branch()
            from_tag = self.create_from_tag()
            
            options_msg = (
                f"OPTIONS sip:{user}@{self.sip_server_host}:{self.sip_server_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
                f"From: <sip:analyzer@{self.sip_server_host}:{self.sip_server_port}>;tag={from_tag}\r\n"
                f"To: <sip:{user}@{self.sip_server_host}:{self.sip_server_port}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 OPTIONS\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: SIP 482 Duplicate Checker\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            print(f"发送OPTIONS请求检查重复注册:\n{options_msg}")
            
            sock.sendto(options_msg.encode('utf-8'), (self.sip_server_host, self.sip_server_port))
            
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                
                print(f"收到OPTIONS响应:\n{response_str}")
                
                # 分析响应中是否有多个Contact头或其他指示重复注册的信息
                lines = response_str.split('\r\n')
                contact_headers = [line for line in lines if line.startswith('Contact:')]
                
                print(f"发现 {len(contact_headers)} 个Contact头")
                for i, contact in enumerate(contact_headers, 1):
                    print(f"  Contact {i}: {contact}")
                
                if len(contact_headers) > 1:
                    print("⚠️  检测到多个Contact头，可能存在重复注册")
                    return True
                else:
                    print("未检测到明显的重复注册")
                    return False
                    
            except socket.timeout:
                print("OPTIONS请求超时")
                return False
                
        except Exception as e:
            print(f"检查重复注册时出错: {e}")
            return False
        finally:
            sock.close()
    
    def analyze_482_causes(self, caller_user="100010", callee_user="670009", password="1234"):
        """全面分析482错误的原因"""
        print("=== SIP 482 Request Merged 详细分析 ===")
        print(f"主叫用户: {caller_user}")
        print(f"被叫用户: {callee_user}")
        print(f"服务器: {self.sip_server_host}:{self.sip_server_port}")
        print()
        
        # 1. 检查重复注册
        print("1. 检查被叫用户是否存在重复注册...")
        has_duplicate_reg = self.check_registration_duplicates(callee_user, password)
        print()
        
        # 2. 尝试发送多个INVITE请求以重现问题
        print("2. 发送多个INVITE请求以测试482问题...")
        invite_results = self.send_multiple_invites(caller_user, callee_user, password, 3)
        print()
        
        # 3. 分析结果
        print("3. 结果分析:")
        print(f"   被叫用户重复注册: {'是' if has_duplicate_reg else '否'}")
        
        # 统计INVITE请求结果
        result_counts = {}
        for result in invite_results:
            result_counts[result] = result_counts.get(result, 0) + 1
        
        print("   INVITE请求结果统计:")
        for result, count in result_counts.items():
            print(f"     - {result}: {count} 次")
        
        # 4. 482错误可能原因分析
        print("\n4. 482错误可能原因分析:")
        
        if has_duplicate_reg:
            print("   - 被叫用户在多个位置注册，服务器无法确定向哪个位置发送请求")
        
        loop_detected_count = sum(1 for r in invite_results if "482" in r)
        if loop_detected_count > 0:
            print("   - 服务器检测到请求循环或重复请求")
        
        if len(invite_results) > 1 and invite_results[0] != invite_results[1]:
            print("   - 多次请求结果不一致，可能与服务器状态有关")
        
        # 5. 提供解决方案建议
        print("\n5. 解决方案建议:")
        print("   A. 清除被叫用户的重复注册:")
        print("      - 向所有注册位置发送EXPIRES=0的REGISTER请求注销")
        print("      - 或重启被叫用户设备")
        print()
        print("   B. 修改呼叫流程以避免触发循环检测:")
        print("      - 确保每次呼叫使用唯一的Call-ID和分支参数")
        print("      - 在发送新请求前等待足够的间隔时间")
        print()
        print("   C. 检查SIP服务器配置:")
        print("      - 查看FreeSWITCH的loop-detection设置")
        print("      - 检查路由规则是否可能导致循环")
        print()
        print("   D. 联系SIP服务器管理员确认是否有特殊配置")
        
        print("\n=== 分析完成 ===")
        
        return {
            'duplicate_registration': has_duplicate_reg,
            'invite_results': invite_results,
            'loop_detected_count': loop_detected_count
        }

def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='SIP 482 Request Merged 详细分析工具')
    parser.add_argument('--caller', default='100010', help='主叫用户名 (默认: 100010)')
    parser.add_argument('--callee', default='670009', help='被叫用户名 (默认: 670009)')
    parser.add_argument('--password', default='1234', help='密码 (默认: 1234)')
    
    args = parser.parse_args()
    
    analyzer = SIP482DetailedAnalyzer()
    analyzer.analyze_482_causes(args.caller, args.callee, args.password)

if __name__ == "__main__":
    main()