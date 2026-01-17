"""
简化版SIP基础通话测试客户端
专注于实现最基本的SIP呼叫功能：INVITE -> 200 OK -> ACK -> BYE
"""

import socket
import time
import logging
import random
import re
from typing import Dict, Any, Optional

from .error_handler import error_handler, retry_on_failure, SIPTestLogger, validate_sip_uri


class BasicSIPCallTester:
    """
    基础SIP通话测试器
    实现最基本的SIP呼叫流程
    """
    
    def __init__(self, server_host: str = "127.0.0.1", server_port: int = 5060, 
                 local_host: str = "127.0.0.1", local_port: int = 5080):
        """
        初始化基础SIP通话测试器
        
        Args:
            server_host: SIP服务器地址
            server_port: SIP服务器端口
            local_host: 本地地址
            local_port: 本地端口
        """
        self.server_host = server_host
        self.server_port = server_port
        self.local_host = local_host
        self.local_port = local_port
        
        # 设置日志
        self.logger = SIPTestLogger("BasicSIPCallTester", "basic_sip_call_tester.log")
    
    def generate_branch(self) -> str:
        """生成唯一的branch ID"""
        return f"z9hG4bK{int(time.time() * 1000000)}{random.randint(1000, 9999)}"
    
    def generate_call_id(self) -> str:
        """生成唯一的Call-ID"""
        return f"{int(time.time())}.{random.randint(10000, 99999)}{self.local_port}"
    
    def generate_tag(self) -> str:
        """生成唯一的tag"""
        return f"tag{int(time.time() * 1000)}"
    
    def validate_uri(self, uri: str) -> bool:
        """验证SIP URI格式"""
        return validate_sip_uri(uri)
    
    def create_invite_message(self, caller_uri: str, callee_uri: str, call_id: str) -> str:
        """创建INVITE请求消息"""
        branch = self.generate_branch()
        from_tag = self.generate_tag()
        
        # 简化的SDP内容
        sdp_content = (
            "v=0\r\n"
            "o=- {timestamp} {timestamp} IN IP4 {local_host}\r\n"
            "s=Basic Call\r\n"
            "c=IN IP4 {local_host}\r\n"
            "t=0 0\r\n"
            "m=audio {rtp_port} RTP/AVP 0 8 101\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
            "a=rtpmap:8 PCMA/8000\r\n"
            "a=rtpmap:101 telephone-event/8000\r\n"
            "a=sendrecv\r\n"
        ).format(
            timestamp=int(time.time()), 
            local_host=self.local_host, 
            rtp_port=self.local_port+1000  # 使用不同端口用于RTP
        )
        
        message = (
            f"INVITE {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"From: {caller_uri};tag={from_tag}\r\n"
            f"To: {callee_uri}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: BasicSIPCallTester 1.0\r\n"
            f"Contact: <{caller_uri.replace('sip:', 'sip:')[:-len(self.server_host)-6]}@{self.local_host}:{self.local_port}>\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp_content)}\r\n"
            f"\r\n"
            f"{sdp_content}"
        )
        return message
    
    def create_ack_message(self, caller_uri: str, callee_uri: str, call_id: str, cseq: int = 1) -> str:
        """创建ACK消息"""
        message = (
            f"ACK {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={self.generate_branch()}\r\n"
            f"From: {caller_uri};tag={self.generate_tag()}\r\n"
            f"To: {callee_uri}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} ACK\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return message
    
    def create_bye_message(self, caller_uri: str, callee_uri: str, call_id: str, cseq: int = 2) -> str:
        """创建BYE消息"""
        message = (
            f"BYE {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={self.generate_branch()}\r\n"
            f"From: {caller_uri};tag={self.generate_tag()}\r\n"
            f"To: {callee_uri}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} BYE\r\n"
            f"Max-Forwards: 70\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return message
    
    @error_handler
    @retry_on_failure(max_retries=3, delay=2.0)
    def make_basic_call(self, caller_uri: str, callee_uri: str, call_duration: int = 5) -> bool:
        """
        执行基础SIP呼叫
        
        Args:
            caller_uri: 主叫URI (e.g., "sip:alice@127.0.0.1:5060")
            callee_uri: 被叫URI (e.g., "sip:bob@127.0.0.1:5060")
            call_duration: 通话持续时间（秒）
            
        Returns:
            bool: 呼叫是否成功
        """
        # 验证SIP URI格式
        if not self.validate_uri(caller_uri) or not self.validate_uri(callee_uri):
            self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(f"无效的SIP URI格式: {caller_uri} -> {callee_uri}"))
            return False
        
        call_id = self.generate_call_id()
        self.logger.log_test_start(f"基础呼叫 {caller_uri} -> {callee_uri}", {"call_id": call_id, "duration": call_duration})
        
        start_time = time.time()
        
        try:
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)  # 10秒超时
            
            # 步骤1: 发送INVITE
            invite_message = self.create_invite_message(caller_uri, callee_uri, call_id)
            self.logger.logger.debug(f"发送INVITE消息: {invite_message[:200]}...")
            
            sock.sendto(invite_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 步骤2: 等待180 Ringing或200 OK响应
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                self.logger.logger.debug(f"收到响应: {response_str[:200]}...")
                
                # 检查是否为180 Ringing
                if "180" in response_str:
                    self.logger.logger.info("收到180 Ringing响应")
                    # 继续等待200 OK
                    response_data, server_addr = sock.recvfrom(4096)
                    response_str = response_data.decode('utf-8')
                
                # 检查是否为200 OK
                if "200 OK" in response_str:
                    self.logger.logger.info("收到200 OK响应，发送ACK确认")
                    
                    # 发送ACK
                    ack_message = self.create_ack_message(caller_uri, callee_uri, call_id, cseq=1)
                    sock.sendto(ack_message.encode('utf-8'), (self.server_host, self.server_port))
                    
                    # 保持通话
                    self.logger.logger.info(f"保持通话 {call_duration} 秒")
                    time.sleep(call_duration)
                    
                    # 发送BYE结束通话
                    self.logger.logger.info("发送BYE请求结束通话")
                    bye_message = self.create_bye_message(caller_uri, callee_uri, call_id, cseq=2)
                    sock.sendto(bye_message.encode('utf-8'), (self.server_host, self.server_port))
                    
                    # 尝试接收BYE确认
                    try:
                        response_data, server_addr = sock.recvfrom(4096)
                        response_str = response_data.decode('utf-8')
                        if "200 OK" in response_str:
                            self.logger.logger.info("收到BYE确认，通话成功完成")
                        else:
                            self.logger.logger.info(f"收到BYE响应: {response_str.split()[1]} {response_str.split()[2]}")
                    except socket.timeout:
                        self.logger.logger.info("BYE确认超时，但通话已尝试结束")
                    
                    sock.close()
                    total_time = time.time() - start_time
                    self.logger.log_test_success(f"基础呼叫 {caller_uri} -> {callee_uri}", total_time)
                    return True
                else:
                    error_msg = f"未收到预期的200 OK响应，收到: {response_str[:100]}..."
                    self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                    sock.close()
                    return False
                    
            except socket.timeout:
                error_msg = "等待SIP响应超时"
                self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                sock.close()
                return False
                
        except Exception as e:
            error_msg = f"基础呼叫执行失败: {str(e)}"
            self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", e)
            return False


def main():
    """基础通话测试主函数"""
    # 创建基础SIP通话测试器
    tester = BasicSIPCallTester(
        server_host="127.0.0.1",
        server_port=5060,
        local_host="127.0.0.1",
        local_port=5080
    )
    
    # 执行基础呼叫测试
    success = tester.make_basic_call(
        caller_uri="sip:alice@127.0.0.1:5060",
        callee_uri="sip:bob@127.0.0.1:5060",
        call_duration=5  # 通话5秒
    )
    
    if success:
        print("基础SIP呼叫测试成功完成！")
    else:
        print("基础SIP呼叫测试失败！")


if __name__ == "__main__":
    main()