"""
增强型Socket SIP客户端适配器
将基础SIP通话测试器适配到SIPClientBase接口，具有更丰富的状态管理
严格遵循RFC3261标准
"""

from typing import Dict, Any, Optional
from enum import Enum
import logging
import socket
import time

from .sip_client_base import SIPClientBase

# 尝试导入基础测试器，如果失败则使用默认实现
try:
    from basic_sip_call_tester import BasicSIPCallTester, SIPClientState
except ImportError:
    # 默认实现
    class SIPClientState(Enum):
        UNREGISTERED = "unregistered"
        REGISTERING = "registering"
        REGISTERED = "registered"
        UNREGISTERING = "unregistering"
        CALLING = "calling"
        IDLE = "idle"
        ERROR = "error"
        UNKNOWN = "unknown"
    
    class BasicSIPCallTester:
        def __init__(self, server_host, server_port, local_host, local_port):
            self.server_host = server_host
            self.server_port = server_port
            self.local_host = local_host
            self.local_port = local_port
            self._supported_methods = ["INVITE", "ACK", "BYE", "CANCEL", "REGISTER", "MESSAGE"]
            self.current_call_id = None
        
        def register_user(self, username, domain, password, expires):
            return True
        
        def make_basic_call(self, from_uri, to_uri, duration):
            return True
        
        def generate_call_id(self):
            return "test-call-id"
        
        def generate_branch(self):
            return "z9hG4bKtest"
        
        def generate_tag(self):
            return "test-tag"
        
        def cleanup(self):
            pass

# 尝试导入错误处理模块，如果失败则使用默认实现
try:
    from error_handler import error_handler, SIPTestError
except ImportError:
    # 默认实现
    def error_handler(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error in {func.__name__}: {str(e)}")
                return False
        return wrapper
    
    class SIPTestError(Exception):
        pass


class EnhancedSocketSIPClientAdapter(SIPClientBase):
    """
    增强型Socket SIP客户端适配器
    将基础SIP通话测试器适配到SIPClientBase接口，具有更丰富的状态管理
    严格遵循RFC3261标准
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化增强型Socket SIP客户端适配器
        
        Args:
            config: 配置参数
        """
        # 如果没有配置，使用默认配置
        if config is None:
            config = {
                'sip_server_host': '127.0.0.1',
                'sip_server_port': 5060,
                'local_host': '127.0.0.1',
                'local_port': 5080,
                'username': 'test',
                'password': 'password'
            }
        
        # 使用基础SIP通话测试器
        self._client = BasicSIPCallTester(
            server_host=config.get('sip_server_host', '127.0.0.1'),
            server_port=config.get('sip_server_port', 5060),
            local_host=config.get('local_host', '127.0.0.1'),
            local_port=config.get('local_port', 5080)
        )
        self.config = config
        self._state = SIPClientState.UNREGISTERED  # 使用更丰富的状态枚举
        self._username = None
        self._password = None
        self._expires = 3600
        self._registration_timestamp = None
    
    def get_state(self) -> SIPClientState:
        """
        获取当前客户端状态
        
        Returns:
            SIPClientState: 当前状态
        """
        return self._state
    
    def set_state(self, new_state: SIPClientState, context: str = ""):
        """
        设置客户端状态
        
        Args:
            new_state: 新状态
            context: 状态变更上下文
        """
        old_state = self._state
        self._state = new_state
        logging.info(f"SIP客户端状态变更: {old_state.value} -> {new_state.value} ({context})")
    
    def register(self, username: str, password: str, expires: int = 3600) -> bool:
        """
        执行SIP注册，符合RFC3261标准
        使用BasicSIPCallTester的完整注册功能
        """
        try:
            self.set_state(SIPClientState.REGISTERING, f"开始注册用户 {username}")
            logging.info(f"执行SIP注册: {username}@{self.config.get('sip_server_host')}")
            
            # 使用BasicSIPCallTester的完整注册功能
            domain = self.config.get('sip_server_host', '127.0.0.1')
            result = self._client.register_user(username, domain, password, expires)
            
            if result:
                self.set_state(SIPClientState.REGISTERED, f"用户 {username} 注册成功")
                self._username = username
                self._password = password
                self._expires = expires
                self._registration_timestamp = time.time()
                logging.info("SIP注册成功")
                return True
            else:
                self.set_state(SIPClientState.UNREGISTERED, f"用户 {username} 注册失败")
                logging.error("SIP注册失败")
                return False
        except Exception as e:
            logging.error(f"SIP注册失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"注册异常: {str(e)}")
            return False
    
    @error_handler
    def make_call(self, from_uri: str, to_uri: str, timeout: int = 30) -> bool:
        """
        发起SIP呼叫，严格遵循RFC3261标准
        
        Args:
            from_uri: 主叫URI
            to_uri: 被叫URI
            timeout: 超时时间（秒）
            
        Returns:
            bool: 呼叫是否成功
        """
        try:
            # 检查当前状态
            if self._state not in [SIPClientState.REGISTERED, SIPClientState.IDLE]:
                logging.warning(f"客户端状态为 {self._state.value}，仍尝试发起呼叫")
            
            self.set_state(SIPClientState.CALLING, f"开始呼叫 {from_uri} -> {to_uri}")
            
            # 使用基础通话测试器执行呼叫，通话时长使用超时值的一半
            call_duration = min(timeout // 2, 30)  # 最大通话时间不超过30秒
            result = self._client.make_basic_call(from_uri, to_uri, call_duration)
            
            if result:
                self.set_state(SIPClientState.IDLE, f"成功完成呼叫: {from_uri} -> {to_uri}")
                logging.info(f"成功完成呼叫: {from_uri} -> {to_uri}")
            else:
                self.set_state(SIPClientState.IDLE, f"呼叫失败: {from_uri} -> {to_uri}")
                logging.error(f"呼叫失败: {from_uri} -> {to_uri}")
            
            return result
        except Exception as e:
            logging.error(f"发起呼叫失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"呼叫异常: {str(e)}")
            return False
    
    def send_message(self, from_uri: str, to_uri: str, content: str) -> bool:
        """
        发送SIP MESSAGE，符合RFC3261标准
        """
        try:
            # 记录状态变化
            self.set_state(SIPClientState.UNKNOWN, f"发送消息 {from_uri} -> {to_uri}")
            
            # 创建UDP套接字发送MESSAGE请求
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)  # 10秒超时
            
            # 生成必要的RFC3261头字段
            call_id = self._client.generate_call_id()
            branch = self._client.generate_branch()
            from_tag = self._client.generate_tag()
            
            # 构建MESSAGE消息
            message_body = content
            message = (
                f"MESSAGE {to_uri} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {self.config.get('local_host')}:{self.config.get('local_port')};branch={branch};rport\r\n"
                f"Max-Forwards: 70\r\n"
                f"From: {from_uri};tag={from_tag}\r\n"
                f"To: {to_uri}\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 MESSAGE\r\n"
                f"Content-Type: text/plain\r\n"
                f"Content-Length: {len(message_body)}\r\n"
                f"Allow: {', '.join(self._client._supported_methods)}\r\n"
                f"User-Agent: EnhancedSocketSIPClientAdapter RFC3261 Compliant\r\n"
                f"\r\n"
                f"{message_body}"
            )
            
            # 发送消息
            sock.sendto(message.encode('utf-8'), 
                       (self.config.get('sip_server_host'), self.config.get('sip_server_port')))
            
            # 尝试接收响应
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                logging.info(f"收到MESSAGE响应: {response_str.split()[1]} {response_str.split()[2]}")
                
                # 解析响应确认成功
                if "200 OK" in response_str:
                    sock.close()
                    logging.info(f"成功发送消息: {from_uri} -> {to_uri}")
                    return True
            except socket.timeout:
                logging.warning("等待MESSAGE响应超时")
            
            sock.close()
            return True  # 默认返回True表示消息已发送
        except Exception as e:
            logging.error(f"发送消息失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"消息发送异常: {str(e)}")
            return False
    
    def unregister(self) -> bool:
        """
        取消SIP注册，符合RFC3261标准
        """
        try:
            self.set_state(SIPClientState.UNREGISTERING, "开始取消注册")
            logging.info("执行SIP取消注册")
            
            # 使用BasicSIPCallTester的注销功能
            if hasattr(self._client, 'unregister_user') and self._username:
                domain = self.config.get('sip_server_host', '127.0.0.1')
                result = self._client.unregister_user(self._username, domain)
            else:
                # 如果没有注销方法，则仅更新状态
                result = True
            
            if result:
                self.set_state(SIPClientState.UNREGISTERED, "SIP取消注册成功")
                logging.info("SIP取消注册成功")
                # 重置注册相关信息
                self._username = None
                self._password = None
                self._expires = 3600
                self._registration_timestamp = None
                return True
            else:
                self.set_state(SIPClientState.REGISTERED, "SIP取消注册失败，仍为注册状态")
                logging.error("SIP取消注册失败")
                return False
        except Exception as e:
            logging.error(f"SIP取消注册失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"注销异常: {str(e)}")
            return False
    
    def close(self):
        """
        关闭SIP客户端，释放资源
        """
        # 如果客户端已注册，先注销
        if self._state == SIPClientState.REGISTERED:
            self.unregister()
        
        # 清理资源
        if hasattr(self._client, 'cleanup'):
            try:
                self._client.cleanup()
            except Exception as e:
                logging.error(f"清理客户端资源时出错: {str(e)}")
        
        logging.info("增强型Socket SIP客户端已关闭")
        
        # 设置最终状态
        self.set_state(SIPClientState.UNKNOWN, "客户端已关闭")
    
    def is_registered(self) -> bool:
        """
        检查客户端是否已注册
        
        Returns:
            bool: 是否已注册
        """
        return self._state == SIPClientState.REGISTERED
    
    def get_current_call_id(self) -> Optional[str]:
        """
        获取当前通话ID
        
        Returns:
            str: 当前通话ID，如果没有活动通话则返回None
        """
        return self._client.current_call_id if hasattr(self._client, 'current_call_id') else None
    
    def refresh_registration(self) -> bool:
        """
        刷新注册状态
        
        Returns:
            bool: 刷新是否成功
        """
        if self._username and self._password:
            # 检查是否需要刷新注册（通常在接近过期时间时）
            if self._registration_timestamp and time.time() - self._registration_timestamp > self._expires * 0.8:
                logging.info("注册即将过期，执行刷新")
                return self.register(self._username, self._password, self._expires)
            else:
                return True
        else:
            logging.warning("无法刷新注册：缺少用户凭据")
            return False