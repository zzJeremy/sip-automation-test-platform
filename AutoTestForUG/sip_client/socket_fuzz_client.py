"""
Socket Fuzz客户端
专注于畸形报文和安全性测试
"""
import socket
import random
import string
import time
import threading
from typing import Dict, Any
import logging
from .socket_client_adapter import SocketSIPClientAdapter


class SocketFuzzClient(SocketSIPClientAdapter):
    """
    Socket Fuzz客户端
    专注于畸形报文和安全性测试
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # 初始化基类
        super().__init__(config)
        
        # 确保必要的属性已设置
        self.config = config or {}
        self.sip_server_host = self.config.get('sip_server_host', '127.0.0.1')
        self.sip_server_port = self.config.get('sip_server_port', 5060)
        self.local_host = self.config.get('local_host', '127.0.0.1')
        self.local_port = self.config.get('local_port', 5080)
        
        self.fuzz_methods = [
            self._fuzz_malformed_headers,
            self._fuzz_invalid_values,
            self._fuzz_buffer_overflow,
            self._fuzz_encoding_issues,
            self._fuzz_protocol_violations
        ]
        self.logger = logging.getLogger(__name__)
    
    def _generate_fuzz_string(self, length: int = 100) -> str:
        """生成随机模糊测试字符串"""
        chars = string.ascii_letters + string.digits + string.punctuation + " \t\n\r"
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _fuzz_malformed_headers(self, sip_message: str) -> str:
        """生成畸形头域的SIP消息"""
        # 添加非法头域或格式错误的头域
        fuzzed_message = sip_message
        malformed_headers = [
            "Malformed-Header: without proper structure\r\n",
            "Bad-Header: \r\n",  # 空值
            "Another-Bad-Header: value without ending",  # 不完整的头域
            "Invalid-Header: \x00\x01\x02",  # 包含控制字符
        ]
        
        # 随机选择一个畸形头域添加到消息中
        if random.choice([True, False]):
            fuzzed_message = fuzzed_message.replace(
                "\r\n\r\n", 
                f"\r\n{random.choice(malformed_headers)}\r\n"
            )
        
        return fuzzed_message
    
    def _fuzz_invalid_values(self, sip_message: str) -> str:
        """生成包含无效值的SIP消息"""
        # 替换一些关键字段为无效值
        invalid_values = [
            "sip:../../../etc/passwd@evil.com",
            "sip:;@example.com",  # 空用户名
            "sip:user@127.0.0.1:99999",  # 非法端口
            "SIP/9.9",  # 非法协议版本
        ]
        
        fuzzed_message = sip_message
        if random.choice([True, False]):
            # 随机替换To或From字段
            if "To:" in fuzzed_message:
                fuzzed_message = fuzzed_message.replace(
                    "To:", f"To: <{random.choice(invalid_values)}>;tag=12345\r\nTo:", 1
                )
        
        return fuzzed_message
    
    def _fuzz_buffer_overflow(self, sip_message: str) -> str:
        """生成可能导致缓冲区溢出的SIP消息"""
        # 创建超长字符串
        overflow_str = "A" * random.randint(1000, 10000)
        fuzzed_message = sip_message.replace(
            "\r\n\r\n", 
            f"\r\nOverflow-Test: {overflow_str}\r\n\r\n"
        )
        return fuzzed_message
    
    def _fuzz_encoding_issues(self, sip_message: str) -> str:
        """生成包含编码问题的SIP消息"""
        # 添加可能导致编码问题的字符
        encoding_issues = [
            "\ufffd",  # 替换字符
            "\ud800\udc00",  # 代理对
            "\x80\x81\x82",  # 无效UTF-8序列
            "\xc0\x80",  # 过长UTF-8编码
        ]
        
        fuzzed_str = random.choice(encoding_issues)
        fuzzed_message = sip_message.replace(
            "\r\n\r\n", 
            f"\r\nEncoding-Test: {fuzzed_str}\r\n\r\n"
        )
        return fuzzed_message
    
    def _fuzz_protocol_violations(self, sip_message: str) -> str:
        """生成违反协议的SIP消息"""
        # 修改SIP消息以违反协议
        violations = [
            lambda msg: msg.replace("SIP/2.0", "SIP/1.0"),  # 错误协议版本
            lambda msg: msg.replace("INVITE", "INVALIDMETHOD"),  # 无效方法
            lambda msg: msg.replace("UDP", "INVALIDPROTO"),  # 无效传输协议
            lambda msg: msg.replace("Content-Length:", "Content-Length: -1"),  # 负数长度
        ]
        
        if random.choice([True, False]):
            fuzzed_message = random.choice(violations)(sip_message)
        else:
            fuzzed_message = sip_message
        
        return fuzzed_message
    
    def _apply_fuzzing(self, sip_message: str) -> str:
        """应用模糊测试技术到SIP消息"""
        fuzzed_message = sip_message
        # 随机选择几种模糊技术并应用
        selected_methods = random.sample(self.fuzz_methods, random.randint(1, 3))
        
        for method in selected_methods:
            fuzzed_message = method(fuzzed_message)
        
        return fuzzed_message

    def register(self, username: str, password: str, expires: int = 3600) -> bool:
        """执行模糊测试注册"""
        try:
            # 构建基础注册消息
            call_id = f"{int(time.time())}.{self.local_host}"
            branch = f"z9hG4bK{int(time.time() * 1000)}"
            
            register_msg = (
                f"REGISTER sip:{self.sip_server_host} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch}\r\n"
                f"From: <sip:{username}@{self.sip_server_host}>;tag={int(time.time())}\r\n"
                f"To: <sip:{username}@{self.sip_server_host}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 REGISTER\r\n"
                f"Contact: <sip:{username}@{self.local_host}:{self.local_port}>\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: FuzzSIPClient/1.0\r\n"
                f"Expires: {expires}\r\n"
                f"Content-Length: 0\r\n\r\n"
            )
            
            # 应用模糊测试技术
            fuzzed_register_msg = self._apply_fuzzing(register_msg)
            
            # 发送模糊后的消息
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(10)
                sock.sendto(fuzzed_register_msg.encode(), (self.sip_server_host, self.sip_server_port))
                
                try:
                    response, server_addr = sock.recvfrom(8192)
                    response_str = response.decode()
                    self.logger.info(f"收到服务器响应: {response_str[:200]}...")
                    
                    # 检查是否收到响应（不关心响应内容，主要是看服务器是否崩溃或异常）
                    return True
                except socket.timeout:
                    self.logger.warning("注册请求超时 - 可能是服务器异常")
                    return False
                    
        except Exception as e:
            self.logger.error(f"模糊测试注册失败: {e}")
            return False

    def make_call(self, caller: str, callee: str) -> bool:
        """发起模糊测试呼叫"""
        try:
            # 构建基础INVITE消息
            call_id = f"{int(time.time())}.{self.local_host}"
            branch = f"z9hG4bK{int(time.time() * 1000)}"
            
            invite_msg = (
                f"INVITE sip:{callee}@{self.sip_server_host} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch}\r\n"
                f"From: <sip:{caller}@{self.sip_server_host}>;tag={int(time.time())}\r\n"
                f"To: <sip:{callee}@{self.sip_server_host}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 INVITE\r\n"
                f"Contact: <sip:{caller}@{self.local_host}:{self.local_port}>\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: FuzzSIPClient/1.0\r\n"
                f"Content-Type: application/sdp\r\n"
                f"Content-Length: 150\r\n\r\n"
                f"v=0\r\n"
                f"o=- {int(time.time())} {int(time.time())} IN IP4 {self.local_host}\r\n"
                f"s=-\r\n"
                f"c=IN IP4 {self.local_host}\r\n"
                f"t=0 0\r\n"
                f"m=audio 8000 RTP/AVP 0\r\n"
                f"a=rtpmap:0 PCMU/8000\r\n"
            )
            
            # 应用模糊测试技术
            fuzzed_invite_msg = self._apply_fuzzing(invite_msg)
            
            # 发送模糊后的消息
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(10)
                sock.sendto(fuzzed_invite_msg.encode(), (self.sip_server_host, self.sip_server_port))
                
                try:
                    response, server_addr = sock.recvfrom(8192)
                    response_str = response.decode()
                    self.logger.info(f"收到服务器响应: {response_str[:200]}...")
                    
                    # 检查是否收到响应（不关心响应内容，主要是看服务器是否崩溃或异常）
                    return True
                except socket.timeout:
                    self.logger.warning("呼叫请求超时 - 可能是服务器异常")
                    return False
                    
        except Exception as e:
            self.logger.error(f"模糊测试呼叫失败: {e}")
            return False

    def send_message(self, sender: str, recipient: str, content: str) -> bool:
        """发送模糊测试消息"""
        try:
            # 构建基础MESSAGE消息
            call_id = f"{int(time.time())}.{self.local_host}"
            branch = f"z9hG4bK{int(time.time() * 1000)}"
            
            message_msg = (
                f"MESSAGE sip:{recipient}@{self.sip_server_host} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch}\r\n"
                f"From: <sip:{sender}@{self.sip_server_host}>;tag={int(time.time())}\r\n"
                f"To: <sip:{recipient}@{self.sip_server_host}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 MESSAGE\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: FuzzSIPClient/1.0\r\n"
                f"Content-Type: text/plain\r\n"
                f"Content-Length: {len(content)}\r\n\r\n"
                f"{content}"
            )
            
            # 应用模糊测试技术
            fuzzed_message_msg = self._apply_fuzzing(message_msg)
            
            # 发送模糊后的消息
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(10)
                sock.sendto(fuzzed_message_msg.encode(), (self.sip_server_host, self.sip_server_port))
                
                try:
                    response, server_addr = sock.recvfrom(8192)
                    response_str = response.decode()
                    self.logger.info(f"收到服务器响应: {response_str[:200]}...")
                    
                    # 检查是否收到响应（不关心响应内容，主要是看服务器是否崩溃或异常）
                    return True
                except socket.timeout:
                    self.logger.warning("消息请求超时 - 可能是服务器异常")
                    return False
                    
        except Exception as e:
            self.logger.error(f"模糊测试消息发送失败: {e}")
            return False

    def close(self):
        """关闭客户端"""
        # 由于使用临时socket，无需特殊关闭操作
        pass