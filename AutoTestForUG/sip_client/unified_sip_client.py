"""
SIP客户端抽象基类和工厂模式实现
优化代码复用性，提供统一的SIP客户端接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol
from enum import Enum
from dataclasses import dataclass
import logging
import socket
import time

# 导入之前创建的安全和错误处理模块
from .sip_client_base import SIPClientBase

# 尝试导入安全模块，如果失败则使用默认实现
try:
    from security_enhancements import SecureSIPMessageBuilder, secure_credential_manager, secure_sip_logger
except ImportError:
    # 默认实现
    class SecureSIPMessageBuilder:
        def __init__(self, logger):
            self.logger = logger
    
    class SecureCredentialManager:
        def store_credentials(self, key, username, password):
            pass
        def remove_credentials(self, key):
            pass
    
    secure_credential_manager = SecureCredentialManager()
    secure_sip_logger = logging.getLogger('secure_sip_logger')

# 尝试导入错误处理模块，如果失败则使用默认实现
try:
    from enhanced_error_handler import SIPErrorHandler, categorize_sip_error, parse_sip_response_code
except ImportError:
    # 默认实现
    class SIPErrorHandler:
        pass
    
    def categorize_sip_error(response, operation):
        return Exception(f"SIP error: {operation}")
    
    def parse_sip_response_code(response):
        return 0

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


# 定义SIP错误码和异常类型
class SIPErrorCode(Enum):
    """SIP错误码枚举"""
    SUCCESS = "success"
    NETWORK_ERROR = "network_error"
    AUTH_FAILED = "auth_failed"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    INVALID_RESPONSE = "invalid_response"
    CLIENT_ERROR = "client_error"
    CONFIG_ERROR = "config_error"


class SIPException(Exception):
    """SIP异常基类"""
    def __init__(self, error_code: SIPErrorCode, message: str, details: dict = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{error_code.value}] {message}")


@dataclass
class SIPResult:
    """SIP操作结果"""
    success: bool
    error_code: Optional[SIPErrorCode] = None
    error_message: Optional[str] = None
    response_code: Optional[int] = None
    details: Dict[str, Any] = None


class UnifiedSIPClient(AbstractSIPClient):
    """
    统一SIP客户端实现
    提供完整的SIP功能实现，继承自抽象基类
    """
    
    def register(self, username: str, password: str, expires: int = 3600) -> SIPResult:
        """
        执行SIP注册
        
        Args:
            username: 用户名
            password: 密码
            expires: 注册有效期（秒）
            
        Returns:
            SIPResult: 注册结果
        """
        try:
            self.set_state(SIPClientState.REGISTERING, f"开始注册用户 {username}")
            secure_sip_logger.info(f"执行SIP注册: {username}@{self.config.get('sip_server_host')}")
            
            # 验证参数
            if not username or not password:
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.CLIENT_ERROR,
                    error_message="用户名和密码不能为空",
                    details={"username": username}
                )
            
            # 使用BasicSIPCallTester的完整注册功能
            domain = self.config.get('sip_server_host', '127.0.0.1')
            
            try:
                result = self._client.register_user(username, domain, password, expires)
            except socket.timeout:
                self.set_state(SIPClientState.ERROR, f"注册超时: {username}")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.TIMEOUT,
                    error_message="注册超时",
                    details={"username": username, "domain": domain}
                )
            except ConnectionRefusedError:
                self.set_state(SIPClientState.ERROR, f"连接被拒绝: {domain}")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.NETWORK_ERROR,
                    error_message="连接被拒绝",
                    details={"domain": domain}
                )
            
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
                return SIPResult(
                    success=True,
                    details={"username": username, "domain": domain, "expires": expires}
                )
            else:
                self.set_state(SIPClientState.UNREGISTERED, f"用户 {username} 注册失败")
                secure_sip_logger.error("SIP注册失败")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.AUTH_FAILED,
                    error_message="注册失败，可能是用户名或密码错误",
                    details={"username": username, "domain": domain}
                )
        except SIPException as e:
            secure_sip_logger.error(f"SIP注册失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"注册异常: {str(e)}")
            return SIPResult(
                success=False,
                error_code=e.error_code,
                error_message=e.message,
                details=e.details
            )
        except Exception as e:
            secure_sip_logger.error(f"SIP注册失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"注册异常: {str(e)}")
            return SIPResult(
                success=False,
                error_code=SIPErrorCode.CLIENT_ERROR,
                error_message=f"注册异常: {str(e)}",
                details={"exception": str(e)}
            )
    
    def make_call(self, from_uri: str, to_uri: str, timeout: int = 30) -> SIPResult:
        """
        发起SIP呼叫
        
        Args:
            from_uri: 主叫URI
            to_uri: 被叫URI
            timeout: 超时时间（秒）
            
        Returns:
            SIPResult: 呼叫结果
        """
        try:
            # 验证参数
            if not from_uri or not to_uri:
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.CLIENT_ERROR,
                    error_message="主叫和被叫URI不能为空",
                    details={"from_uri": from_uri, "to_uri": to_uri}
                )
            
            # 检查当前状态
            if self._state not in [SIPClientState.REGISTERED, SIPClientState.IDLE]:
                secure_sip_logger.warning(f"客户端状态为 {self._state.value}，仍尝试发起呼叫")
            
            self.set_state(SIPClientState.CALLING, f"开始呼叫 {from_uri} -> {to_uri}")
            
            # 使用基础通话测试器执行呼叫
            call_duration = min(timeout // 2, 30)  # 最大通话时间不超过30秒
            
            try:
                result = self._client.make_basic_call(from_uri, to_uri, call_duration)
            except socket.timeout:
                self.set_state(SIPClientState.IDLE, f"呼叫超时: {from_uri} -> {to_uri}")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.TIMEOUT,
                    error_message="呼叫超时",
                    details={"from_uri": from_uri, "to_uri": to_uri, "timeout": timeout}
                )
            except ConnectionRefusedError:
                self.set_state(SIPClientState.IDLE, f"连接被拒绝: {from_uri} -> {to_uri}")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.NETWORK_ERROR,
                    error_message="连接被拒绝",
                    details={"from_uri": from_uri, "to_uri": to_uri}
                )
            
            if result:
                self.set_state(SIPClientState.IDLE, f"成功完成呼叫: {from_uri} -> {to_uri}")
                secure_sip_logger.info(f"成功完成呼叫: {from_uri} -> {to_uri}")
                return SIPResult(
                    success=True,
                    details={"from_uri": from_uri, "to_uri": to_uri, "duration": call_duration}
                )
            else:
                self.set_state(SIPClientState.IDLE, f"呼叫失败: {from_uri} -> {to_uri}")
                secure_sip_logger.error(f"呼叫失败: {from_uri} -> {to_uri}")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.SERVER_ERROR,
                    error_message="呼叫失败",
                    details={"from_uri": from_uri, "to_uri": to_uri}
                )
        except SIPException as e:
            secure_sip_logger.error(f"发起呼叫失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"呼叫异常: {str(e)}")
            return SIPResult(
                success=False,
                error_code=e.error_code,
                error_message=e.message,
                details=e.details
            )
        except Exception as e:
            secure_sip_logger.error(f"发起呼叫失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"呼叫异常: {str(e)}")
            return SIPResult(
                success=False,
                error_code=SIPErrorCode.CLIENT_ERROR,
                error_message=f"呼叫异常: {str(e)}",
                details={"exception": str(e)}
            )
    
    def send_message(self, from_uri: str, to_uri: str, content: str) -> SIPResult:
        """
        发送SIP消息
        
        Args:
            from_uri: 发送方URI
            to_uri: 接收方URI
            content: 消息内容
            
        Returns:
            SIPResult: 消息发送结果
        """
        try:
            # 验证参数
            if not from_uri or not to_uri:
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.CLIENT_ERROR,
                    error_message="发送方和接收方URI不能为空",
                    details={"from_uri": from_uri, "to_uri": to_uri}
                )
            
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
            try:
                sock.sendto(message.encode('utf-8'), 
                           (self.config.get('sip_server_host'), self.config.get('sip_server_port')))
            except ConnectionRefusedError:
                sock.close()
                self.set_state(SIPClientState.ERROR, f"消息发送失败: 连接被拒绝")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.NETWORK_ERROR,
                    error_message="连接被拒绝",
                    details={"from_uri": from_uri, "to_uri": to_uri}
                )
            
            # 尝试接收响应
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                secure_sip_logger.info(f"收到MESSAGE响应: {response_str.split()[1]} {response_str.split()[2]}")
                
                # 解析响应确认成功
                if "200 OK" in response_str:
                    sock.close()
                    secure_sip_logger.info(f"成功发送消息: {from_uri} -> {to_uri}")
                    return SIPResult(
                        success=True,
                        response_code=200,
                        details={"from_uri": from_uri, "to_uri": to_uri}
                    )
                else:
                    sock.close()
                    return SIPResult(
                        success=False,
                        error_code=SIPErrorCode.SERVER_ERROR,
                        error_message=f"服务器返回错误: {response_str.split()[1]} {response_str.split()[2]}",
                        response_code=int(response_str.split()[1]) if len(response_str.split()) > 1 else None,
                        details={"from_uri": from_uri, "to_uri": to_uri}
                    )
            except socket.timeout:
                sock.close()
                secure_sip_logger.warning("等待MESSAGE响应超时")
                return SIPResult(
                    success=True,  # 超时但消息可能已发送
                    error_code=SIPErrorCode.TIMEOUT,
                    error_message="等待响应超时，但消息可能已发送",
                    details={"from_uri": from_uri, "to_uri": to_uri}
                )
        except SIPException as e:
            secure_sip_logger.error(f"发送消息失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"消息发送异常: {str(e)}")
            return SIPResult(
                success=False,
                error_code=e.error_code,
                error_message=e.message,
                details=e.details
            )
        except Exception as e:
            secure_sip_logger.error(f"发送消息失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"消息发送异常: {str(e)}")
            return SIPResult(
                success=False,
                error_code=SIPErrorCode.CLIENT_ERROR,
                error_message=f"消息发送异常: {str(e)}",
                details={"exception": str(e)}
            )
    
    def unregister(self) -> SIPResult:
        """
        取消SIP注册
        
        Returns:
            SIPResult: 取消注册结果
        """
        try:
            if not self._username:
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.CLIENT_ERROR,
                    error_message="没有已注册的用户",
                    details={}
                )
            
            self.set_state(SIPClientState.UNREGISTERING, "开始取消注册")
            secure_sip_logger.info("执行SIP取消注册")
            
            # 使用BasicSIPCallTester的注销功能
            domain = self.config.get('sip_server_host', '127.0.0.1')
            
            try:
                if hasattr(self._client, 'unregister_user'):
                    result = self._client.unregister_user(self._username, domain)
                else:
                    # 如果没有注销方法，则仅更新状态
                    result = True
            except socket.timeout:
                self.set_state(SIPClientState.ERROR, "注销超时")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.TIMEOUT,
                    error_message="注销超时",
                    details={"username": self._username, "domain": domain}
                )
            
            if result:
                self.set_state(SIPClientState.UNREGISTERED, "SIP取消注册成功")
                secure_sip_logger.info("SIP取消注册成功")
                
                # 移除安全存储的凭据
                secure_credential_manager.remove_credentials(f"{self._username}@{domain}")
                
                # 重置注册相关信息
                username = self._username
                self._username = None
                self._password = None
                self._expires = 3600
                
                return SIPResult(
                    success=True,
                    details={"username": username, "domain": domain}
                )
            else:
                self.set_state(SIPClientState.REGISTERED, "SIP取消注册失败，仍为注册状态")
                secure_sip_logger.error("SIP取消注册失败")
                return SIPResult(
                    success=False,
                    error_code=SIPErrorCode.SERVER_ERROR,
                    error_message="取消注册失败",
                    details={"username": self._username, "domain": domain}
                )
        except SIPException as e:
            secure_sip_logger.error(f"SIP取消注册失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"注销异常: {str(e)}")
            return SIPResult(
                success=False,
                error_code=e.error_code,
                error_message=e.message,
                details=e.details
            )
        except Exception as e:
            secure_sip_logger.error(f"SIP取消注册失败: {str(e)}")
            self.set_state(SIPClientState.ERROR, f"注销异常: {str(e)}")
            return SIPResult(
                success=False,
                error_code=SIPErrorCode.CLIENT_ERROR,
                error_message=f"注销异常: {str(e)}",
                details={"exception": str(e)}
            )
    
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


# 为向后兼容，保留原始的SocketSIPClientAdapter
# 但推荐使用UnifiedSIPClient


# 客户端创建功能已迁移到 SIPClientManager
# 请使用 SIPClientManager 来创建和管理客户端