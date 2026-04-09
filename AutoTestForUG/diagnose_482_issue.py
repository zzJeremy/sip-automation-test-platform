#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIP 482 Request Merged 问题诊断工具
用于分析和解决呼叫时出现的482响应问题
"""

import socket
import time
import logging
import hashlib
import random
from urllib.parse import urlparse
import configparser

class SIP482Diagnoser:
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
        
        # 存储认证信息
        self.auth_info = {}
        self.current_username = None
        self.current_password = None
        
    def parse_sip_uri(self, uri):
        """解析SIP URI"""
        if uri.startswith("sip:"):
            uri = uri[4:]
        parts = uri.split('@')
        if len(parts) == 2:
            user = parts[0]
            host_port = parts[1]
        else:
            user = ""
            host_port = parts[0]
            
        if ':' in host_port:
            host, port = host_port.split(':')
            port = int(port)
        else:
            host = host_port
            port = 5060
            
        return user, host, port
        
    def create_unique_branch(self):
        """创建唯一的Branch ID"""
        return f"z9hG4bK{int(time.time())}{random.randint(100000, 999999)}"
        
    def create_from_tag(self):
        """创建From标签"""
        return f"tag{int(time.time())}{random.randint(100000, 999999)}"
        
    def create_call_id(self):
        """创建Call-ID"""
        return f"{int(time.time())}.{hash(str(random.random())) % 1000000}@{self.local_host}"
        
    def send_options_request(self, target_user):
        """发送OPTIONS请求检查用户状态"""
        print(f"=== 发送OPTIONS请求检查用户 {target_user} 的状态 ===")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        try:
            call_id = self.create_call_id()
            branch = self.create_unique_branch()
            from_tag = self.create_from_tag()
            
            options_msg = (
                f"OPTIONS sip:{target_user}@{self.sip_server_host}:{self.sip_server_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.sip_server_port};branch={branch};rport\r\n"
                f"From: <sip:tester@{self.sip_server_host}:{self.sip_server_port}>;tag={from_tag}\r\n"
                f"To: <sip:{target_user}@{self.sip_server_host}:{self.sip_server_port}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 OPTIONS\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: SIP 482 Diagnoser 1.0\r\n"
                f"Accept: application/sdp\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            print(f"发送OPTIONS请求:\n{options_msg}")
            
            sock.sendto(options_msg.encode('utf-8'), (self.sip_server_host, self.sip_server_port))
            
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                
                print(f"收到OPTIONS响应:\n{response_str}")
                
                # 解析响应
                lines = response_str.split('\r\n')
                if lines:
                    status_line = lines[0]
                    print(f"状态行: {status_line}")
                    
                    if '200 OK' in status_line:
                        print(f"✓ 用户 {target_user} 可达")
                        return True
                    else:
                        print(f"✗ 用户 {target_user} 不可达或状态异常")
                        return False
                        
            except socket.timeout:
                print("OPTIONS请求超时，用户可能不可达")
                return False
                
        except Exception as e:
            print(f"发送OPTIONS请求时出错: {e}")
            return False
        finally:
            sock.close()
    
    def send_register_probe(self, username, password, expires=3600):
        """发送探测性注册请求"""
        print(f"=== 发送探测性注册请求检查用户 {username} 的注册状态 ===")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        try:
            call_id = self.create_call_id()
            branch = self.create_unique_branch()
            from_tag = self.create_from_tag()
            
            # 构建REGISTER请求
            register_msg = (
                f"REGISTER sip:{self.sip_server_host}:{self.sip_server_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
                f"From: <sip:{username}@{self.sip_server_host}:{self.sip_server_port}>;tag={from_tag}\r\n"
                f"To: <sip:{username}@{self.sip_server_host}:{self.sip_server_port}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 REGISTER\r\n"
                f"Max-Forwards: 70\r\n"
                f"Contact: <sip:{username}@{self.local_host}:{self.local_port}>\r\n"
                f"Expires: {expires}\r\n"
                f"User-Agent: SIP 482 Diagnoser 1.0\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            print(f"发送探测性REGISTER请求:\n{register_msg}")
            
            sock.sendto(register_msg.encode('utf-8'), (self.sip_server_host, self.sip_server_port))
            
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            print(f"收到REGISTER响应:\n{response_str}")
            
            # 检查是否需要认证
            if '401' in response_str or '407' in response_str:
                print("服务器要求认证，尝试使用提供的凭据进行认证...")
                return self.handle_register_auth(sock, username, password, call_id, branch, from_tag, expires, response_str)
            elif '200 OK' in response_str:
                print(f"✓ 用户 {username} 注册状态正常")
                return True
            else:
                print(f"✗ 用户 {username} 注册状态异常")
                return False
                
        except Exception as e:
            print(f"发送REGISTER请求时出错: {e}")
            return False
        finally:
            sock.close()
    
    def handle_register_auth(self, sock, username, password, call_id, original_branch, from_tag, expires, initial_response):
        """处理注册认证"""
        try:
            # 从初始响应中解析认证头
            response_lines = initial_response.split('\r\n')
            auth_header = None
            
            for line in response_lines:
                if line.startswith('WWW-Authenticate:') or line.startswith('Proxy-Authenticate:'):
                    auth_header = line[len('WWW-Authenticate:'):].strip() if line.startswith('WWW-Authenticate:') else line[len('Proxy-Authenticate:'):].strip()
                    break
            
            if not auth_header:
                print("未找到认证头信息")
                return False
                
            print(f"认证挑战: {auth_header}")
            
            # 解析认证参数
            params = self.parse_auth_header(auth_header)
            
            # 生成认证响应
            response_value = self.calculate_digest_response(
                username=username,
                password=password,
                realm=params.get('realm', ''),
                nonce=params.get('nonce', ''),
                method='REGISTER',
                uri=f"sip:{self.sip_server_host}:{self.sip_server_port}",
                algorithm=params.get('algorithm', 'MD5'),
                qop=params.get('qop', ''),
                nc='00000001',
                cnonce='abcdef1234567890'
            )
            
            # 构建带认证的REGISTER请求
            auth_branch = self.create_unique_branch()
            auth_register_msg = (
                f"REGISTER sip:{self.sip_server_host}:{self.sip_server_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={auth_branch};rport\r\n"
                f"From: <sip:{username}@{self.sip_server_host}:{self.sip_server_port}>;tag={from_tag}\r\n"
                f"To: <sip:{username}@{self.sip_server_host}:{self.sip_server_port}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 2 REGISTER\r\n"
                f"Max-Forwards: 70\r\n"
                f"Contact: <sip:{username}@{self.local_host}:{self.local_port}>\r\n"
                f"Expires: {expires}\r\n"
                f"Authorization: Digest "
                f'username="{username}", '
                f'realm="{params.get("realm", "")}", '
                f'nonce="{params.get("nonce", "")}", '
                f'uri="sip:{self.sip_server_host}:{self.sip_server_port}", '
                f'response="{response_value}", '
                f'algorithm={params.get("algorithm", "MD5")}'
            )
            
            if params.get('qop'):
                auth_register_msg += f', qop={params.get("qop")}, nc=00000001, cnonce="abcdef1234567890"'
            
            auth_register_msg += "\r\n"
            auth_register_msg += "User-Agent: SIP 482 Diagnoser 1.0\r\n"
            auth_register_msg += "Content-Length: 0\r\n"
            auth_register_msg += "\r\n"
            
            print(f"发送带认证的REGISTER请求:\n{auth_register_msg}")
            
            sock.sendto(auth_register_msg.encode('utf-8'), (self.sip_server_host, self.sip_server_port))
            
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            print(f"收到认证后REGISTER响应:\n{response_str}")
            
            if '200 OK' in response_str:
                print(f"✓ 用户 {username} 认证注册成功")
                return True
            else:
                print(f"✗ 用户 {username} 认证注册失败")
                return False
                
        except Exception as e:
            print(f"处理注册认证时出错: {e}")
            return False
    
    def parse_auth_header(self, auth_header):
        """解析认证头"""
        params = {}
        parts = auth_header.split(',')
        
        for part in parts:
            if '=' in part:
                key_val = part.split('=', 1)
                key = key_val[0].strip()
                val = key_val[1].strip().strip('"\'')
                params[key] = val
                
        return params
    
    def calculate_digest_response(self, username, password, realm, nonce, method, uri, algorithm='MD5', qop='', nc='', cnonce=''):
        """计算摘要认证响应值"""
        # 计算 HA1 = MD5(username:realm:password)
        ha1_input = f"{username}:{realm}:{password}"
        ha1 = hashlib.md5(ha1_input.encode()).hexdigest()
        
        # 计算 HA2 = MD5(method:digestURI)
        ha2_input = f"{method}:{uri}"
        ha2 = hashlib.md5(ha2_input.encode()).hexdigest()
        
        # 计算 Response = MD5(HA1:nonce:HA2) 或 MD5(HA1:nonce:nc:cnonce:qop:HA2)
        if qop:
            response_input = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
        else:
            response_input = f"{ha1}:{nonce}:{ha2}"
            
        response = hashlib.md5(response_input.encode()).hexdigest()
        return response
    
    def diagnose_482_issue(self, caller_user="100010", callee_user="670009", password="1234"):
        """全面诊断482问题"""
        print("=== SIP 482 Request Merged 问题诊断 ===")
        print(f"主叫用户: {caller_user}")
        print(f"被叫用户: {callee_user}")
        print(f"服务器: {self.sip_server_host}:{self.sip_server_port}")
        print()
        
        # 1. 检查被叫用户状态
        print("1. 检查被叫用户状态...")
        callee_reachable = self.send_options_request(callee_user)
        print()
        
        # 2. 检查主叫用户注册状态
        print("2. 检查主叫用户注册状态...")
        caller_registered = self.send_register_probe(caller_user, password)
        print()
        
        # 3. 检查被叫用户注册状态
        print("3. 检查被叫用户注册状态...")
        callee_registered = self.send_register_probe(callee_user, password)  # 使用相同密码作为测试
        print()
        
        # 4. 分析482响应的可能原因
        print("4. 482 Request Merged 响应分析:")
        print("   这个响应通常表示:")
        print("   - 被叫用户已注册到多个位置，SIP服务器无法确定向哪个位置发送请求")
        print("   - 存在重复或冲突的请求")
        print("   - 被叫用户的注册信息有冲突")
        print()
        
        # 5. 提供解决方案建议
        print("5. 解决方案建议:")
        print("   A. 检查被叫用户670009是否同时在多个设备上注册")
        print("   B. 确认SIP服务器配置是否允许单用户多设备注册")
        print("   C. 尝试呼叫其他可用用户以确认是否是特定用户问题")
        print("   D. 检查SIP服务器日志获取更多详细信息")
        print("   E. 重启被叫用户设备或注销其所有注册")
        print()
        
        # 6. 状态汇总
        print("6. 状态汇总:")
        print(f"   被叫用户可访问: {'是' if callee_reachable else '否'}")
        print(f"   主叫用户已注册: {'是' if caller_registered else '否'}")
        print(f"   被叫用户已注册: {'是' if callee_registered else '否'}")
        print()
        
        if not callee_reachable:
            print("⚠️  建议首先解决被叫用户可达性问题")
        elif callee_registered and not callee_reachable:
            print("⚠️  用户已注册但不可达，可能存在多设备注册冲突")
        else:
            print("⚠️  需要进一步检查SIP服务器配置")
        
        print("\n=== 诊断完成 ===")
        
        return {
            'callee_reachable': callee_reachable,
            'caller_registered': caller_registered,
            'callee_registered': callee_registered
        }

def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='SIP 482 Request Merged 问题诊断工具')
    parser.add_argument('--mode', choices=['full', 'callee-status', 'caller-status', 'custom'], 
                       default='full', help='诊断模式: full(完整诊断), callee-status(被叫状态), caller-status(主叫状态), custom(自定义)')
    parser.add_argument('--caller', default='100010', help='主叫用户名 (默认: 100010)')
    parser.add_argument('--callee', default='670009', help='被叫用户名 (默认: 670009)')
    parser.add_argument('--password', default='1234', help='密码 (默认: 1234)')
    
    args = parser.parse_args()
    
    diagnoser = SIP482Diagnoser()
    
    if args.mode == 'full':
        print("执行完整诊断 (用户100010 -> 670009)")
        diagnoser.diagnose_482_issue(args.caller, args.callee, args.password)
    elif args.mode == 'callee-status':
        print(f"检查被叫用户 {args.callee} 状态")
        diagnoser.send_options_request(args.callee)
    elif args.mode == 'caller-status':
        print(f"检查主叫用户 {args.caller} 状态")
        diagnoser.send_register_probe(args.caller, args.password)
    elif args.mode == 'custom':
        print(f"执行自定义诊断 ({args.caller} -> {args.callee})")
        diagnoser.diagnose_482_issue(args.caller, args.callee, args.password)

if __name__ == "__main__":
    main()