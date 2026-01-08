"""
SIP客户端管理器
管理不同类型的SIP客户端实现
"""

from typing import Dict, Any, Optional
from enum import Enum
import logging

from .sip_client_base import SIPClientBase
from .pj_sip_client import PJSIPSIPClient
from .socket_client_adapter import SocketSIPClientAdapter  # 我们的socket适配器实现
from .sipp_driver_client import SIPpDriverClient
from .socket_fuzz_client import SocketFuzzClient


class SIPClientType(Enum):
    """
    SIP客户端类型枚举
    """
    SOCKET = "socket"        # 基于socket的实现
    PJSIP = "pj_sip"         # 基于PJSIP的实现
    SIPp_DRIVER = "sipp_driver"  # 基于SIPp的实现
    SOCKET_FUZZ = "socket_fuzz"  # 基于socket的模糊测试实现


class SIPClientManager:
    """
    SIP客户端管理器
    负责创建和管理不同类型的SIP客户端
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化客户端管理器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.active_client: Optional[SIPClientBase] = None
        self.clients: Dict[SIPClientType, SIPClientBase] = {}
    
    def create_client(self, client_type: SIPClientType) -> SIPClientBase:
        """
        创建指定类型的SIP客户端
        
        Args:
            client_type: 客户端类型
            
        Returns:
            SIPClientBase: 创建的客户端实例
        """
        if client_type == SIPClientType.SOCKET:
            # 返回我们的socket适配器实现
            return SocketSIPClientAdapter(self.config)
        elif client_type == SIPClientType.PJSIP:
            # 返回PJSIP实现
            try:
                return PJSIPSIPClient(self.config)
            except ImportError:
                logging.warning("PJSIP库不可用，回退到socket实现")
                return SocketSIPClientAdapter(self.config)
        elif client_type == SIPClientType.SIPp_DRIVER:
            # 返回SIPp驱动客户端实现
            return SIPpDriverClient(self.config)
        elif client_type == SIPClientType.SOCKET_FUZZ:
            # 返回Socket模糊测试客户端实现
            return SocketFuzzClient(self.config)
        else:
            raise ValueError(f"不支持的客户端类型: {client_type}")
    
    def get_client(self, client_type: SIPClientType) -> SIPClientBase:
        """
        获取指定类型的SIP客户端（带缓存）
        
        Args:
            client_type: 客户端类型
            
        Returns:
            SIPClientBase: 客户端实例
        """
        if client_type not in self.clients:
            self.clients[client_type] = self.create_client(client_type)
        
        return self.clients[client_type]
    
    def switch_client(self, client_type: SIPClientType) -> bool:
        """
        切换到指定类型的SIP客户端
        
        Args:
            client_type: 客户端类型
            
        Returns:
            bool: 切换是否成功
        """
        try:
            # 如果当前有活动客户端，先关闭它
            if self.active_client:
                self.active_client.close()
            
            # 获取新客户端
            self.active_client = self.get_client(client_type)
            logging.info(f"已切换到 {client_type.value} 客户端")
            return True
        except Exception as e:
            logging.error(f"切换客户端失败: {str(e)}")
            return False
    
    def get_current_client(self) -> Optional[SIPClientBase]:
        """
        获取当前活动的客户端
        
        Returns:
            SIPClientBase: 当前活动的客户端
        """
        return self.active_client
    
    def execute_with_client(self, client_type: SIPClientType, operation, *args, **kwargs):
        """
        使用指定类型的客户端执行操作
        
        Args:
            client_type: 客户端类型
            operation: 操作函数
            *args: 操作参数
            **kwargs: 操作关键字参数
            
        Returns:
            操作结果
        """
        client = self.get_client(client_type)
        return operation(client, *args, **kwargs)


def create_default_client(config: Dict[str, Any] = None) -> SIPClientBase:
    """
    创建默认的SIP客户端（优先使用PJSIP，回退到socket）
    
    Args:
        config: 配置参数
        
    Returns:
        SIPClientBase: 默认客户端实例
    """
    if config is None:
        # 使用默认配置
        config = {
            'sip_server_host': '127.0.0.1',
            'sip_server_port': 5060,
            'local_host': '127.0.0.1',
            'local_port': 5080
        }
    
    manager = SIPClientManager(config)
    
    # 尝试创建PJSIP客户端，如果失败则使用socket客户端
    try:
        return manager.create_client(SIPClientType.PJSIP)
    except ImportError:
        logging.info("PJSIP库不可用，使用socket实现")
        return manager.create_client(SIPClientType.SOCKET)