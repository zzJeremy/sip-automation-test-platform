#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIP测试服务器模块
实现SIP服务器功能，用于处理来自客户端的SIP请求
"""

import socket
import threading
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import configparser
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config.config import load_config


@dataclass
class SIPRequest:
    """SIP请求数据类"""
    method: str
    uri: str
    version: str
    headers: Dict[str, str]
    body: str = ""


@dataclass
class SIPResponse:
    """SIP响应数据类"""
    status_code: int
    reason: str
    version: str
    headers: Dict[str, str]
    body: str = ""


class SIPMethod(Enum):
    """SIP方法枚举"""
    INVITE = "INVITE"
    ACK = "ACK"
    BYE = "BYE"
    CANCEL = "CANCEL"
    OPTIONS = "OPTIONS"
    REGISTER = "REGISTER"
    MESSAGE = "MESSAGE"


class SIPTestServer:
    """SIP测试服务器类"""
    
    def __init__(self, config_path: str = "./config/config.ini"):
        """
        初始化SIP测试服务器
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.config = load_config(config_path)
        
        # 从配置中获取服务器参数
        server_config = self.config.get('TEST_SERVER', {})
        self.host = server_config.get('server_host', '127.0.0.1')
        self.port = server_config.get('server_port', 5060)
        self.protocol = server_config.get('protocol', 'UDP').upper()
        
        # 服务器状态
        self.running = False
        self.socket = None
        self.client_connections = {}  # 存储客户端连接信息
        self.active_calls = {}  # 存储活跃通话信息
        self.registered_users = {}  # 存储注册用户信息
        
        # 初始化日志
        self._setup_logging()
        
        self.logger.info(f"SIP测试服务器初始化完成 - {self.protocol}://{self.host}:{self.port}")
    
    def _setup_logging(self):
        """设置日志配置"""
        log_config = self.config.get('LOGGING', {})
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())
        log_file = log_config.get('log_file', 'sip_test_server.log')
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # 设置日志级别
        self.logger.setLevel(log_level)
        self.logger.addHandler(file_handler)
    
    def start(self):
        """启动SIP测试服务器"""
        try:
            if self.protocol == 'UDP':
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            elif self.protocol == 'TCP':
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            else:
                raise ValueError(f"不支持的协议: {self.protocol}")
            
            # 绑定地址和端口
            self.socket.bind((self.host, self.port))
            self.running = True
            
            if self.protocol == 'TCP':
                self.socket.listen(5)
                self.logger.info(f"SIP测试服务器在TCP {self.host}:{self.port}上监听")
            else:
                self.logger.info(f"SIP测试服务器在UDP {self.host}:{self.port}上监听")
            
            # 启动接收线程
            receive_thread = threading.Thread(target=self._receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
        except Exception as e:
            self.logger.error(f"启动SIP测试服务器失败: {e}")
            raise
    
    def stop(self):
        """停止SIP测试服务器"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info("SIP测试服务器已停止")
    
    def _receive_messages(self):
        """接收SIP消息的线程函数"""
        while self.running:
            try:
                if self.protocol == 'UDP':
                    data, addr = self.socket.recvfrom(4096)
                    self._handle_message(data.decode('utf-8'), addr)
                else:  # TCP
                    conn, addr = self.socket.accept()
                    # 为每个连接启动一个处理线程
                    conn_thread = threading.Thread(
                        target=self._handle_tcp_connection, 
                        args=(conn, addr)
                    )
                    conn_thread.daemon = True
                    conn_thread.start()
            except socket.error:
                if self.running:  # 只在服务器仍在运行时记录错误
                    self.logger.error("接收消息时发生错误", exc_info=True)
                break
            except Exception as e:
                self.logger.error(f"处理消息时发生未预期错误: {e}", exc_info=True)
    
    def _handle_tcp_connection(self, conn, addr):
        """处理TCP连接"""
        try:
            while self.running:
                data = conn.recv(4096)
                if not data:
                    break
                self._handle_message(data.decode('utf-8'), addr)
        except Exception as e:
            self.logger.error(f"处理TCP连接时发生错误: {e}", exc_info=True)
        finally:
            conn.close()
    
    def _parse_sip_message(self, message: str) -> Optional[SIPRequest]:
        """解析SIP消息"""
        try:
            lines = message.strip().split('\r\n')
            if not lines:
                return None
            
            # 解析请求行或状态行
            first_line = lines[0].strip()
            parts = first_line.split(' ', 2)
            
            if len(parts) < 2:
                return None
            
            # 判断是请求还是响应
            if parts[0].upper() in [method.value for method in SIPMethod]:
                # 这是一个请求
                method = parts[0]
                uri = parts[1]
                version = parts[2] if len(parts) > 2 else 'SIP/2.0'
                
                # 解析头部
                headers = {}
                body_start = 1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == '':
                        body_start = i + 1
                        break
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip()] = value.strip()
                
                # 解析消息体
                body = '\r\n'.join(lines[body_start:]) if body_start < len(lines) else ""
                
                return SIPRequest(method, uri, version, headers, body)
            else:
                # 这是一个响应，暂时不处理
                return None
        except Exception as e:
            self.logger.error(f"解析SIP消息失败: {e}")
            return None
    
    def _handle_message(self, message: str, addr):
        """处理接收到的SIP消息"""
        self.logger.info(f"接收到SIP消息来自 {addr}: {message[:100]}...")
        
        sip_request = self._parse_sip_message(message)
        if not sip_request:
            self.logger.error("无法解析SIP消息")
            return
        
        self.logger.info(f"处理SIP请求: {sip_request.method} {sip_request.uri}")
        
        # 根据请求方法处理
        if sip_request.method == SIPMethod.REGISTER.value:
            response = self._handle_register(sip_request, addr)
        elif sip_request.method == SIPMethod.INVITE.value:
            response = self._handle_invite(sip_request, addr)
        elif sip_request.method == SIPMethod.BYE.value:
            response = self._handle_bye(sip_request, addr)
        elif sip_request.method == SIPMethod.MESSAGE.value:
            response = self._handle_message_request(sip_request, addr)
        elif sip_request.method == SIPMethod.OPTIONS.value:
            response = self._handle_options(sip_request, addr)
        else:
            response = self._create_response(405, "Method Not Allowed", sip_request)
        
        # 发送响应
        if self.protocol == 'UDP':
            self._send_response(response, addr)
        else:
            # 对于TCP，需要在连接中发送响应
            pass  # 简化处理，实际实现中需要在TCP连接中发送
    
    def _handle_register(self, request: SIPRequest, addr) -> SIPResponse:
        """处理注册请求"""
        self.logger.info("处理注册请求")
        
        # 检查认证信息
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            # 请求认证
            return self._create_response(401, "Unauthorized", request, {
                "WWW-Authenticate": 'Digest realm="example.com", nonce="1234567890"'
            })
        
        # 模拟注册成功
        contact = request.headers.get('Contact', '')
        expires = request.headers.get('Expires', '3600')
        
        # 存储注册信息
        user_info = {
            'contact': contact,
            'expires': int(expires),
            'registered_at': time.time(),
            'addr': addr
        }
        
        # 提取用户名
        if 'To' in request.headers:
            to_header = request.headers['To']
            if '<' in to_header:
                user_start = to_header.find('<') + 1
                user_end = to_header.find('>')
                if user_start > 0 and user_end > user_start:
                    user_uri = to_header[user_start:user_end]
                    username = user_uri.split('@')[0].split(':')[1] if ':' in user_uri else user_uri.split('@')[0]
                    self.registered_users[username] = user_info
                    self.logger.info(f"用户 {username} 注册成功")
        
        return self._create_response(200, "OK", request)
    
    def _handle_invite(self, request: SIPRequest, addr) -> SIPResponse:
        """处理邀请请求（呼叫建立）"""
        self.logger.info("处理INVITE请求")
        
        # 生成通话ID
        call_id = request.headers.get('Call-ID', str(int(time.time())))
        
        # 检查是否已经有活跃通话
        if call_id in self.active_calls:
            return self._create_response(486, "Busy Here", request)
        
        # 记录通话信息
        self.active_calls[call_id] = {
            'from': request.headers.get('From', ''),
            'to': request.headers.get('To', ''),
            'start_time': time.time(),
            'addr': addr
        }
        
        # 发送180 Ringing响应
        ringing_response = self._create_response(180, "Ringing", request)
        if self.protocol == 'UDP':
            self._send_response(ringing_response, addr)
        
        # 等待一小段时间后发送200 OK
        time.sleep(1)
        
        # 更新通话状态
        self.active_calls[call_id]['status'] = 'connected'
        
        return self._create_response(200, "OK", request, {
            "Content-Type": "application/sdp",
            "Content-Length": "0"  # 实际SDP内容应根据需要添加
        })
    
    def _handle_bye(self, request: SIPRequest, addr) -> SIPResponse:
        """处理挂断请求"""
        self.logger.info("处理BYE请求")
        
        call_id = request.headers.get('Call-ID', '')
        if call_id in self.active_calls:
            del self.active_calls[call_id]
            self.logger.info(f"通话 {call_id} 已结束")
        
        return self._create_response(200, "OK", request)
    
    def _handle_message_request(self, request: SIPRequest, addr) -> SIPResponse:
        """处理MESSAGE请求"""
        self.logger.info("处理MESSAGE请求")
        
        # 记录消息内容
        content_type = request.headers.get('Content-Type', 'text/plain')
        self.logger.info(f"收到消息 (类型: {content_type}): {request.body}")
        
        return self._create_response(200, "OK", request)
    
    def _handle_options(self, request: SIPRequest, addr) -> SIPResponse:
        """处理OPTIONS请求"""
        self.logger.info("处理OPTIONS请求")
        
        return self._create_response(200, "OK", request, {
            "Allow": "INVITE, ACK, CANCEL, OPTIONS, BYE, REGISTER, MESSAGE",
            "Accept": "application/sdp",
            "Supported": "replaces, from-change"
        })
    
    def _create_response(self, status_code: int, reason: str, request: SIPRequest, 
                        additional_headers: Dict[str, str] = None) -> SIPResponse:
        """创建SIP响应"""
        headers = {
            "Via": request.headers.get('Via', ''),
            "From": request.headers.get('From', ''),
            "To": request.headers.get('To', ''),
            "Call-ID": request.headers.get('Call-ID', str(int(time.time()))),
            "CSeq": request.headers.get('CSeq', '1 ' + request.method),
        }
        
        if additional_headers:
            headers.update(additional_headers)
        
        return SIPResponse(status_code, reason, request.version, headers)
    
    def _send_response(self, response: SIPResponse, addr):
        """发送SIP响应"""
        try:
            response_str = f"{response.version} {response.status_code} {response.reason}\r\n"
            for key, value in response.headers.items():
                response_str += f"{key}: {value}\r\n"
            response_str += f"\r\n{response.body}"
            
            self.socket.sendto(response_str.encode('utf-8'), addr)
            self.logger.info(f"发送SIP响应 {response.status_code} 给 {addr}")
        except Exception as e:
            self.logger.error(f"发送响应失败: {e}")
    
    def get_registered_users(self) -> Dict[str, dict]:
        """获取已注册用户列表"""
        return self.registered_users.copy()
    
    def get_active_calls(self) -> Dict[str, dict]:
        """获取活跃通话列表"""
        return self.active_calls.copy()
    
    def get_server_stats(self) -> Dict[str, any]:
        """获取服务器统计信息"""
        return {
            'registered_users_count': len(self.registered_users),
            'active_calls_count': len(self.active_calls),
            'server_running': self.running,
            'host': self.host,
            'port': self.port,
            'protocol': self.protocol
        }


def main():
    """测试服务器功能的主函数"""
    logging.basicConfig(level=logging.INFO)
    
    server = SIPTestServer()
    
    try:
        server.start()
        print("SIP测试服务器已启动，按Ctrl+C停止...")
        
        # 保持服务器运行
        while True:
            time.sleep(1)
            
            # 每隔一段时间打印服务器状态
            if int(time.time()) % 10 == 0:
                stats = server.get_server_stats()
                print(f"服务器状态: {stats}")
                
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server.stop()


if __name__ == "__main__":
    main()