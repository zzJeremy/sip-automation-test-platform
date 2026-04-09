#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试SIP代理认证过程的工具
用于分析407 Proxy Authentication Required的处理过程
"""

import hashlib
import re
import time
import socket
import logging
import sys
import os
import random
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# 直接从sip_test_client.py复制SIPMessageBuilder类的定义
class SIPMessageBuilder:
    """
    SIP消息构造器类
    用于安全、标准化地构造SIP消息
    """
    
    @staticmethod
    def generate_branch() -> str:
        """生成唯一的branch ID"""
        return f"z9hG4bK{int(time.time() * 1000000)}{random.randint(1000, 9999)}"

    @staticmethod
    def generate_call_id() -> str:
        """生成唯一的Call-ID"""
        return f"{int(time.time())}.{random.randint(10000, 99999)}"

    @staticmethod
    def generate_tag() -> str:
        """生成唯一的tag"""
        return f"tag{int(time.time() * 1000)}"

    @staticmethod
    def validate_uri(uri: str) -> bool:
        """验证SIP URI格式"""
        sip_uri_pattern = r'^sip:[a-zA-Z0-9_.!~*\'();:&=+$,-]+@([a-zA-Z0-9.-]+|\[[0-9a-fA-F:.]+\])(:[0-9]+)?$'
        return bool(re.match(sip_uri_pattern, uri))

    @staticmethod
    def validate_message_format(message: str) -> Dict[str, Any]:
        """验证SIP消息格式"""
        errors = []
        
        # 检查基本SIP消息结构
        lines = message.strip().split('\r\n')
        
        # 检查第一行是否包含SIP协议标识
        if not lines[0].upper().startswith(('INVITE', 'REGISTER', 'ACK', 'BYE', 'OPTIONS', 'SIP/')):
            errors.append("消息第一行缺少有效的SIP方法或响应")
        
        # 检查必需的头部
        headers = [line for line in lines if ':' in line and not line.startswith(' ')]
        header_names = [line.split(':')[0].strip().lower() for line in headers]
        
        required_headers = ['via', 'from', 'to', 'call-id', 'cseq']
        for req_header in required_headers:
            if req_header not in header_names:
                errors.append(f"缺少必需的头部字段: {req_header}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    @staticmethod
    def create_invite_message(caller_uri: str, callee_uri: str, local_host: str, 
                            local_port: int, server_host: str, server_port: int, 
                            call_id: str) -> str:
        """创建INVITE请求消息"""
        branch = SIPMessageBuilder.generate_branch()
        from_tag = SIPMessageBuilder.generate_tag()
        
        # 简化的SDP内容
        sdp_content = f"""v=0
o=- {int(time.time())} {int(time.time())} IN IP4 {local_host}
s=-
c=IN IP4 {local_host}
t=0 0
m=audio {local_port+10000} RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=sendrecv
"""
        
        # 计算Content-Length
        content_length = len(sdp_content.encode('utf-8'))
        
        # 构建INVITE请求
        message = (
            f"INVITE {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_host}:{local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: <{caller_uri}>;tag={from_tag}\r\n"
            f"To: <{callee_uri}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Contact: <{caller_uri}>\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {content_length}\r\n"
            f"\r\n{sdp_content}"
        )
        
        return message

    @staticmethod
    def parse_response(response: str) -> Dict[str, Any]:
        """解析SIP响应消息"""
        lines = response.strip().split('\r\n')
        
        # 解析状态行
        status_line = lines[0]
        if status_line.startswith('SIP/'):
            parts = status_line.split(' ', 2)
            if len(parts) >= 3:
                sip_version = parts[0]
                status_code = parts[1]
                reason = parts[2]
            else:
                return {"error": "无法解析状态行"}
        else:
            return {"error": "不是有效的SIP响应"}

        # 解析头部
        headers = {}
        body_start = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "":
                body_start = i
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()

        # 提取主体
        body = ""
        if body_start != -1 and body_start + 1 < len(lines):
            body = '\n'.join(lines[body_start + 1:])

        return {
            "version": sip_version,
            "status_code": status_code,
            "reason": reason,
            "headers": headers,
            "body": body
        }


# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class SIPProxyAuthDebugger:
    def __init__(self, server_host, server_port, local_host="127.0.0.1", local_port=5080):
        self.server_host = server_host
        self.server_port = server_port
        self.local_host = local_host
        self.local_port = local_port

    def debug_auth_process(self, username, password, callee_uri):
        """
        调试认证过程
        """
        print(f"=== 开始调试SIP代理认证过程 ===")
        print(f"用户名: {username}")
        print(f"密码: {password}")
        print(f"被叫: {callee_uri}")
        print(f"服务器: {self.server_host}:{self.server_port}")
        print()

        # 创建UDP套接字
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(15)

        try:
            # 构建初始INVITE请求
            call_id = SIPMessageBuilder.generate_call_id()
            invite_message = SIPMessageBuilder.create_invite_message(
                caller_uri=f"sip:{username}@{self.server_host}:{self.server_port}",
                callee_uri=callee_uri,
                local_host=self.local_host,
                local_port=self.local_port,
                server_host=self.server_host,
                server_port=self.server_port,
                call_id=call_id
            )

            print("发送初始INVITE请求...")
            print("=" * 50)
            print(invite_message)
            print("=" * 50)
            
            # 发送INVITE请求
            sock.sendto(invite_message.encode('utf-8'), (self.server_host, self.server_port))

            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            print("收到初始响应...")
            print("=" * 50)
            print(response_str)
            print("=" * 50)

            # 解析响应
            parsed_response = SIPMessageBuilder.parse_response(response_str)
            print(f"解析响应结果: {parsed_response}")

            # 如果收到407，开始调试认证过程
            if parsed_response.get('status_code') == '407':
                print("\n" + "="*60)
                print("检测到407 Proxy Authentication Required，开始调试认证过程")
                print("="*60)
                
                # 提取认证头
                headers = parsed_response.get('headers', {})
                auth_header = headers.get('Proxy-Authenticate')
                
                if auth_header:
                    print(f"Proxy-Authenticate头: {auth_header}")
                    
                    # 解析认证参数
                    auth_params = self.parse_auth_header(auth_header)
                    print(f"解析的认证参数: {auth_params}")
                    
                    # 尝试生成认证响应
                    response_value = self.calculate_response(
                        username=username,
                        password=password,
                        realm=auth_params.get('realm'),
                        nonce=auth_params.get('nonce'),
                        method='INVITE',
                        uri=callee_uri,
                        algorithm=auth_params.get('algorithm', 'MD5'),
                        qop=auth_params.get('qop', ''),
                        nc='00000001',  # 第一次尝试
                        cnonce='abcdef1234567890'  # 示例客户端随机数
                    )
                    
                    print(f"计算出的响应值: {response_value}")
                    
                    # 构建带认证的INVITE请求
                    authenticated_invite = self.create_authenticated_invite_with_proxy_auth(
                        caller_uri=f"sip:{username}@{self.server_host}:{self.server_port}",
                        callee_uri=callee_uri,
                        local_host=self.local_host,
                        local_port=self.local_port,
                        server_host=self.server_host,
                        server_port=self.server_port,
                        call_id=call_id,
                        auth_params=auth_params,
                        response=response_value,
                        nc='00000001',
                        cnonce='abcdef1234567890'
                    )
                    
                    print("\n构建的带认证INVITE请求:")
                    print("=" * 50)
                    print(authenticated_invite)
                    print("=" * 50)
                    
                    # 发送带认证的请求
                    print("发送带认证的INVITE请求...")
                    sock.sendto(authenticated_invite.encode('utf-8'), (self.server_host, self.server_port))

                    # 接收认证后的响应
                    try:
                        response_data, server_addr = sock.recvfrom(4096)
                        response_str = response_data.decode('utf-8')
                        
                        print("收到认证后响应...")
                        print("=" * 50)
                        print(response_str)
                        print("=" * 50)

                        # 解析认证后的响应
                        final_parsed_response = SIPMessageBuilder.parse_response(response_str)
                        print(f"认证后响应解析: {final_parsed_response}")
                        
                        if final_parsed_response.get('status_code') == '407':
                            print("\n⚠️  注意：仍然收到407响应，可能的原因：")
                            print("   1. 凭据不正确")
                            print("   2. 服务器需要特定的认证算法或参数")
                            print("   3. 用户在服务器上未正确配置")
                            print("   4. 服务器配置问题")
                        else:
                            print(f"\n✅ 认证成功，收到状态码: {final_parsed_response.get('status_code')}")
                            
                    except socket.timeout:
                        print("❌ 认证请求超时")
                else:
                    print("❌ 未找到Proxy-Authenticate头")
            else:
                print(f"❌ 未收到407响应，而是收到了: {parsed_response.get('status_code')}")

        except Exception as e:
            print(f"❌ 调试过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            sock.close()
            print("\n=== 调试完成 ===")

    def parse_auth_header(self, auth_header):
        """
        解析认证头信息
        """
        auth_params = {}
        
        # 提取认证参数
        patterns = [
            r'realm="([^"]+)"',
            r'nonce="([^"]+)"',
            r'opaque="([^"]*)"',  # 可选参数
            r'algorithm=([A-Z0-9]+)',
            r'qop="([^"]+)"'  # 质询选项
        ]
        
        for pattern in patterns:
            match = re.search(pattern, auth_header, re.IGNORECASE)
            if match:
                if 'realm' in pattern:
                    auth_params['realm'] = match.group(1)
                elif 'nonce' in pattern:
                    auth_params['nonce'] = match.group(1)
                elif 'opaque' in pattern:
                    auth_params['opaque'] = match.group(1) if match.group(1) else ''
                elif 'algorithm' in pattern:
                    auth_params['algorithm'] = match.group(1)
                elif 'qop' in pattern:
                    auth_params['qop'] = match.group(1)
        
        return auth_params

    def calculate_response(self, username, password, realm, nonce, method, uri, 
                          algorithm='MD5', qop='', nc='', cnonce=''):
        """
        计算SIP摘要认证的响应值
        """
        # HA1 = MD5(username:realm:password)
        ha1_input = f"{username}:{realm}:{password}"
        ha1 = hashlib.md5(ha1_input.encode()).hexdigest()
        
        if qop and qop.lower() == 'auth':
            # HA2 = MD5(method:digestURI)
            ha2_input = f"{method}:{uri}"
            ha2 = hashlib.md5(ha2_input.encode()).hexdigest()
            
            # Response = MD5(HA1:nonce:nonceCount:cnonce:qop:HA2)
            response_input = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
        else:
            # Response = MD5(HA1:nonce:HA2)
            ha2_input = f"{method}:{uri}"
            ha2 = hashlib.md5(ha2_input.encode()).hexdigest()
            response_input = f"{ha1}:{nonce}:{ha2}"
        
        response = hashlib.md5(response_input.encode()).hexdigest()
        return response

    def create_authenticated_invite_with_proxy_auth(self, caller_uri, callee_uri, local_host, 
                                                   local_port, server_host, server_port, 
                                                   call_id, auth_params, response, nc, cnonce):
        """
        创建带代理认证的INVITE请求
        """
        import random
        
        # 生成必要参数
        branch = SIPMessageBuilder.generate_branch()
        from_tag = SIPMessageBuilder.generate_tag()
        to_tag = SIPMessageBuilder.generate_tag()
        
        # 获取用户名
        username = caller_uri.split('@')[0].replace('sip:', '')
        realm = auth_params['realm']
        nonce = auth_params['nonce']
        algorithm = auth_params.get('algorithm', 'MD5')
        opaque = auth_params.get('opaque', '')
        qop = auth_params.get('qop', '')
        
        # 构建Authorization头
        auth_parts = [
            f'username="{username}"',
            f'realm="{realm}"',
            f'nonce="{nonce}"',
            f'uri="{callee_uri}"',
            f'response="{response}"',
            f'algorithm={algorithm}'
        ]
        
        if qop:
            auth_parts.extend([
                f'qop={qop}',
                f'nc={nc}',
                f'cnonce="{cnonce}"'
            ])
        
        if opaque:
            auth_parts.append(f'opaque="{opaque}"')
        
        auth_header = 'Proxy-Authorization: Digest ' + ', '.join(auth_parts)
        
        # 构建完整的消息
        message_lines = [
            f"INVITE {callee_uri} SIP/2.0",
            f"Via: SIP/2.0/UDP {local_host}:{local_port};branch={branch};rport",
            f"Max-Forwards: 70",
            f"From: <{caller_uri}>;tag={from_tag}",
            f"To: <{callee_uri}>",
            f"Call-ID: {call_id}",
            f"CSeq: 1 INVITE",
            auth_header,  # 这里使用Proxy-Authorization而不是Authorization
            f"Contact: <{caller_uri}>",
            f"Content-Type: application/sdp",
            f"Content-Length: 0",
            "",
            ""  # 空行结束头部
        ]
        
        return '\r\n'.join(message_lines)


def main():
    # 测试特定场景
    debugger = SIPProxyAuthDebugger(
        server_host="192.168.30.66",
        server_port=5060
    )
    
    debugger.debug_auth_process(
        username="100010",
        password="1234",
        callee_uri="sip:670009@192.168.30.66:5060"
    )


if __name__ == "__main__":
    main()