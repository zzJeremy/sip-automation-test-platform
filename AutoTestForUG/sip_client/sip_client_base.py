"""
SIP客户端抽象基类
定义统一的SIP客户端接口，支持多种实现（socket、pjsua2等）
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging


class SIPClientBase(ABC):
    """
    SIP客户端抽象基类
    定义统一的SIP操作接口
    """
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """
        初始化SIP客户端
        
        Args:
            config: 配置参数
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def unregister(self) -> bool:
        """
        取消SIP注册
        
        Returns:
            bool: 取消注册是否成功
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        关闭SIP客户端，释放资源
        """
        pass