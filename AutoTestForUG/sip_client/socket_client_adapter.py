"""
Socket SIP客户端适配器
将基础SIP通话测试器适配到SIPClientBase接口，专注于最基础的通话功能
"""

from typing import Dict, Any, Optional
import logging

from .sip_client_base import SIPClientBase
from ..basic_sip_call_tester import BasicSIPCallTester  # 导入基础通话测试器
from ..error_handler import error_handler, SIPTestError


class SocketSIPClientAdapter(SIPClientBase):
    """
    Socket SIP客户端适配器
    将基础SIP通话测试器适配到SIPClientBase接口
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化Socket SIP客户端适配器
        
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
    
    def register(self, username: str, password: str, expires: int = 3600) -> bool:
        """
        执行SIP注册
        
        注意: 基础版本暂时不实现注册功能，仅专注于通话测试
        """
        logging.warning("基础版本暂不支持注册功能")
        return True  # 模拟成功
    
    @error_handler
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
            # 使用基础通话测试器执行呼叫，通话时长使用超时值的一半
            call_duration = min(timeout // 2, 30)  # 最大通话时间不超过30秒
            return self._client.make_basic_call(from_uri, to_uri, call_duration)
        except Exception as e:
            logging.error(f"发起呼叫失败: {str(e)}")
            return False
    
    def send_message(self, from_uri: str, to_uri: str, content: str) -> bool:
        """
        发送SIP消息
        
        注意: 基础版本暂时不实现消息发送功能
        """
        logging.warning("基础版本暂不支持消息发送功能")
        return True  # 模拟成功
    
    def unregister(self) -> bool:
        """
        取消SIP注册
        
        注意: 基础版本暂时不实现取消注册功能
        """
        logging.warning("基础版本暂不支持取消注册功能")
        return True  # 模拟成功
    
    def close(self):
        """
        关闭SIP客户端，释放资源
        """
        # 如果有需要清理的资源，在这里处理
        logging.info("Socket SIP客户端已关闭")
        pass