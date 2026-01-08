"""
Socket SIP客户端适配器
将现有的SIPTestClient适配到SIPClientBase接口
"""

from typing import Dict, Any, Optional
import logging

from .sip_client_base import SIPClientBase
from ..test_client.sip_test_client import SIPTestClient  # 导入现有的socket实现


class SocketSIPClientAdapter(SIPClientBase):
    """
    Socket SIP客户端适配器
    将现有的SIPTestClient适配到SIPClientBase接口
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
                'TEST_CLIENT': {
                    'sip_server_host': '127.0.0.1',
                    'sip_server_port': 5060,
                    'local_host': '127.0.0.1',
                    'local_port': 5080,
                    'username': 'test',
                    'password': 'password'
                }
            }
        
        # 直接使用SIPTestClient的默认初始化
        self._client = SIPTestClient()
        self.config = config
    
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
        # 调用SIPTestClient的register_user方法
        return self._client.register_user(username, password, expires)
    
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
        # 从URI中提取用户名和域信息
        # 例如: sip:alice@127.0.0.1:5060
        try:
            # 简化处理，直接调用现有的make_call方法
            # 这里可能需要根据实际的make_call方法签名进行调整
            return self._client.make_call(from_uri, to_uri)
        except Exception as e:
            logging.error(f"发起呼叫失败: {str(e)}")
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
            return self._client.send_message(from_uri, to_uri, content)
        except Exception as e:
            logging.error(f"发送消息失败: {str(e)}")
            return False
    
    def unregister(self) -> bool:
        """
        取消SIP注册
        
        Returns:
            bool: 取消注册是否成功
        """
        # 现有的SIPTestClient可能没有unregister方法，需要实现
        # 这里暂时返回True，实际实现需要根据协议添加
        try:
            # 发送取消注册的请求
            # 实现注销逻辑
            logging.info("取消注册功能待实现")
            return True
        except Exception as e:
            logging.error(f"取消注册失败: {str(e)}")
            return False
    
    def close(self):
        """
        关闭SIP客户端，释放资源
        """
        # 如果有需要清理的资源，在这里处理
        logging.info("Socket SIP客户端已关闭")
        pass