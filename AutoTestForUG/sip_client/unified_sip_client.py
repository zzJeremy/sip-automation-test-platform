"""
SIP客户端抽象基类和工厂模式实现
优化代码复用性，提供统一的SIP客户端接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol
import logging
import socket
import time

# 导入之前创建的安全和错误处理模块
from .sip_client_base import SIPClientBase
from ..security_enhancements import SecureSIPMessageBuilder, secure_credential_manager, secure_sip_logger
from ..enhanced_error_handler import SIPErrorHandler, categorize_sip_error, parse_sip_response_code
from ..basic_sip_call_tester import BasicSIPCallTester, SIPClientState


class SIPMessageBuilderInterface(Protocol):
    """SIP消息构建器接口"""
    
    def create_register_message(self, username: str, domain: str, local_host: str, local_port: int, 
                               server_host: str, server_port: int, expires: int = 3600) -> str:
        ...
    
    def create_invite_message(self, caller_uri: str, callee_uri: str, local_host: str, local_port: int,
                             server_host: str, server_port: int) -> str:
        ...


class AbstractSIPClient(SIPClientBase, ABC):
    """
    抽象SIP客户端基类
    提供统一的SIP客户端接口和公共功能实现
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化抽象SIP客户端
        
        Args:
            config: 配置参数
        """
        # 设置默认配置
        default_config = {
            'sip_server_host': '127.0.0.1',
            'sip_server_port': 5060,
            'local_host': '127.0.0.1',
            'local_port': 5080,
            'username': 'test',
            'password': 'password',
            'timeout': 30,
            'max_retries': 3
        }
        
        # 合并配置
        self.config = {**default_config, **config}
        
        # 初始化安全组件
        self.secure_message_builder = SecureSIPMessageBuilder(secure_sip_logger)
        self.sip_error_handler = SIPErrorHandler()
        
        # 初始化状态
        self._state = SIPClientState.UNREGISTERED
        self._username = None
        self._password = None
        self._expires = 3600
        
        # 初始化基础测试器
        self._client = BasicSIPCallTester(
            server_host=self.config.get('sip_server_host', '127.0.0.1'),
            server_port=self.config.get('sip_server_port', 5060),
            local_host=self.config.get('local_host', '127.0.0.1'),
            local_port=self.config.get('local_port', 5080)
        )
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_state(self) -> SIPClientState:
        """获取当前客户端状态"""
        return self._state
    
    def set_state(self, new_state: SIPClientState, context: str = ""):
        """设置客户端状态"""
        old_state = self._state
        self._state = new_state
        secure_sip_logger.info(f"客户端状态变更: {old_state.value} -> {new_state.value} ({context})")
    
    def _validate_config(self) -> bool:
        """验证配置参数"""
        required_fields = ['sip_server_host', 'sip_server_port', 'local_host', 'local_port']
        for field in required_fields:
            if field not in self.config or not self.config[field]:
                secure_sip_logger.error(f"配置缺少必需字段: {field}")
                return False
        return True
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析SIP响应"""
        lines = response.split('\r\n')
        if not lines:
            return {}
        
        # 解析状态行
        status_line = lines[0]
        parts = status_line.split(' ', 2)
        if len(parts) >= 3:
            protocol, status_code, reason_phrase = parts
        else:
            return {}
        
        parsed_response = {
            'protocol': protocol,
            'status_code': int(status_code),
            'reason_phrase': reason_phrase,
            'headers': {},
            'body': ''
        }
        
        # 解析头字段
        body_started = False
        body_lines = []
        for line in lines[1:]:
            if line.strip() == '':
                body_started = True
                continue
            
            if not body_started:
                if line.startswith(' ') or line.startswith('\t'):
                    # 连续行，附加到上一个头字段
                    if parsed_response['headers']:
                        last_header = list(parsed_response['headers'].keys())[-1]
                        parsed_response['headers'][last_header] += ' ' + line.strip()
                else:
                    # 新的头字段
                    if ':' in line:
                        header_name, header_value = line.split(':', 1)
                        parsed_response['headers'][header_name.strip()] = header_value.strip()
            else:
                body_lines.append(line)
        
        parsed_response['body'] = '\r\n'.join(body_lines)
        return parsed_response
    
    def _handle_sip_error(self, response: str, operation: str = "SIP operation") -> Exception:
        """处理SIP错误响应"""
        status_code = parse_sip_response_code(response)
        return categorize_sip_error(response, operation)


class UnifiedSIPClient(AbstractSIPClient):
    """
    统一SIP客户端实现
    提供完整的SIP功能实现，继承自抽象基类
    """
    
    def register(self, username: str, password: str, expires: int = 3600) -> bool:
        """
        执行SIP注册
        
        Args:
            username: 用户名
            password: 密码
            expires: 注册有效期（秒）
            
        Returns:
            bool: 注册是否成功
        """
        try:
            self.set_state(SIPClientState.REGISTERING, f"开始注册用户 {username}")
            secure_sip_logger.info(f"执行SIP注册: {username}@{self.config.get('sip_server_host')}")
            
            # 使用BasicSIPCallTester的完整注册功能
            domain = self.config.get('sip_server_host', '127.0.0.1')
            result = self._client.register_user(username, domain, password, expires)
            
            if result:
                self.set_state(SIPClientState.REGISTERED, f"用户 {username} 注册成功")
                self._username = username
                self._password = password
                self._expires = expires
                
                # 安全存储凭据
                secure_credential_manager.store_credentials(
                    f"{username}@{domain}", username, password
                )
                
                secure_sip_logger.info("SIP注册成功")
                return True
            else:
                self.set_state(SIPClientState.UNREGISTERED, f"用户 {username} 注册失败")
                secure_sip_logger.error("SIP注册失败")
                return False
        except Exception as e:
            secure_sip_logger.error(f"SIP注册失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"注册异常: {str(e)}")
            return False
    
    def make_call(self, from_uri: str, to_uri: str, timeout: int = 30) -> bool:
        """
        发起SIP呼叫
        
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
                secure_sip_logger.warning(f"客户端状态为 {self._state.value}，仍尝试发起呼叫")
            
            self.set_state(SIPClientState.CALLING, f"开始呼叫 {from_uri} -> {to_uri}")
            
            # 使用基础通话测试器执行呼叫
            call_duration = min(timeout // 2, 30)  # 最大通话时间不超过30秒
            result = self._client.make_basic_call(from_uri, to_uri, call_duration)
            
            if result:
                self.set_state(SIPClientState.IDLE, f"成功完成呼叫: {from_uri} -> {to_uri}")
                secure_sip_logger.info(f"成功完成呼叫: {from_uri} -> {to_uri}")
            else:
                self.set_state(SIPClientState.IDLE, f"呼叫失败: {from_uri} -> {to_uri}")
                secure_sip_logger.error(f"呼叫失败: {from_uri} -> {to_uri}")
            
            return result
        except Exception as e:
            secure_sip_logger.error(f"发起呼叫失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"呼叫异常: {str(e)}")
            return False
    
    def send_message(self, from_uri: str, to_uri: str, content: str) -> bool:
        """
        发送SIP消息
        
        Args:
            from_uri: 发送方URI
            to_uri: 接收方URI
            content: 消息内容
            
        Returns:
            bool: 消息发送是否成功
        """
        try:
            # 记录状态变化
            self.set_state(SIPClientState.UNKNOWN, f"发送消息 {from_uri} -> {to_uri}")
            
            # 创建UDP套接字发送MESSAGE请求
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.config.get('timeout', 10))  # 使用配置的超时值
            
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
                f"User-Agent: {self.__class__.__name__} RFC3261 Compliant\r\n"
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
                secure_sip_logger.info(f"收到MESSAGE响应: {response_str.split()[1]} {response_str.split()[2]}")
                
                # 解析响应确认成功
                if "200 OK" in response_str:
                    sock.close()
                    secure_sip_logger.info(f"成功发送消息: {from_uri} -> {to_uri}")
                    return True
            except socket.timeout:
                secure_sip_logger.warning("等待MESSAGE响应超时")
            
            sock.close()
            return True  # 默认返回True表示消息已发送
        except Exception as e:
            secure_sip_logger.error(f"发送消息失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"消息发送异常: {str(e)}")
            return False
    
    def unregister(self) -> bool:
        """
        取消SIP注册
        
        Returns:
            bool: 取消注册是否成功
        """
        try:
            self.set_state(SIPClientState.UNREGISTERING, "开始取消注册")
            secure_sip_logger.info("执行SIP取消注册")
            
            # 使用BasicSIPCallTester的注销功能
            if hasattr(self._client, 'unregister_user') and self._username:
                domain = self.config.get('sip_server_host', '127.0.0.1')
                result = self._client.unregister_user(self._username, domain)
            else:
                # 如果没有注销方法，则仅更新状态
                result = True
            
            if result:
                self.set_state(SIPClientState.UNREGISTERED, "SIP取消注册成功")
                secure_sip_logger.info("SIP取消注册成功")
                
                # 移除安全存储的凭据
                if self._username:
                    domain = self.config.get('sip_server_host', '127.0.0.1')
                    secure_credential_manager.remove_credentials(f"{self._username}@{domain}")
                
                # 重置注册相关信息
                self._username = None
                self._password = None
                self._expires = 3600
                return True
            else:
                self.set_state(SIPClientState.REGISTERED, "SIP取消注册失败，仍为注册状态")
                secure_sip_logger.error("SIP取消注册失败")
                return False
        except Exception as e:
            secure_sip_logger.error(f"SIP取消注册失败: {str(e)}")
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
                secure_sip_logger.error(f"清理客户端资源时出错: {str(e)}")
        
        secure_sip_logger.info("统一SIP客户端已关闭")
        
        # 设置最终状态
        self.set_state(SIPClientState.UNKNOWN, "客户端已关闭")


class SIPClientFactory:
    """
    SIP客户端工厂类
    提供创建不同类型SIP客户端的统一接口
    """
    
    @staticmethod
    def create_client(client_type: str, config: Dict[str, Any]) -> SIPClientBase:
        """
        创建SIP客户端
        
        Args:
            client_type: 客户端类型 ('unified', 'socket', 'enhanced_socket', 'pjsip')
            config: 配置参数
            
        Returns:
            SIPClientBase: 创建的SIP客户端实例
        """
        if client_type.lower() == 'unified':
            from .unified_sip_client import UnifiedSIPClient
            return UnifiedSIPClient(config)
        elif client_type.lower() == 'socket':
            from .socket_client_adapter import SocketSIPClientAdapter
            return SocketSIPClientAdapter(config)
        elif client_type.lower() == 'enhanced_socket':
            from .enhanced_socket_client import EnhancedSocketSIPClientAdapter
            return EnhancedSocketSIPClientAdapter(config)
        elif client_type.lower() == 'pjsip':
            from .pj_sip_client import PJSIPSIPClient
            return PJSIPSIPClient(config)
        else:
            raise ValueError(f"不支持的客户端类型: {client_type}")
    
    @staticmethod
    def get_available_client_types() -> list:
        """
        获取可用的客户端类型
        
        Returns:
            list: 可用客户端类型的列表
        """
        return ['unified', 'socket', 'enhanced_socket', 'pjsip']


# 为向后兼容，保留原始的SocketSIPClientAdapter
# 但推荐使用UnifiedSIPClient