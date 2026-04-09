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
from .asterisk_sip_client import AsteriskSIPClient
from .unified_sip_client import UnifiedSIPClient
from .enhanced_socket_client import EnhancedSocketSIPClientAdapter


class SIPClientType(Enum):
    """
    SIP客户端类型枚举
    """
    UNIFIED = "unified"           # 统一客户端实现
    SOCKET = "socket"           # 基础socket实现
    ENHANCED_SOCKET = "enhanced_socket"  # 增强型socket实现
    PJSIP = "pj_sip"           # PJSIP实现
    SIPp_DRIVER = "sipp_driver" # SIPp实现
    SOCKET_FUZZ = "socket_fuzz" # 模糊测试
    ASTERISK_AMI = "asterisk_ami"  # Asterisk AMI接口
    ASTERISK_AGI = "asterisk_agi"  # Asterisk AGI接口
    ASTERISK_ARI = "asterisk_ari"  # Asterisk ARI接口


class SIPClientManager:
    """
    SIP客户端管理器
    负责创建和管理不同类型的SIP客户端
    单例模式实现，确保全局唯一实例
    """
    
    _instance = None
    _clients: Dict[str, SIPClientBase] = {}
    
    def __new__(cls, config: Dict[str, Any] = None):
        """
        单例模式实现
        """
        if cls._instance is None:
            cls._instance = super(SIPClientManager, cls).__new__(cls)
            cls._instance._initialize(config)
        return cls._instance
    
    def _initialize(self, config: Dict[str, Any] = None):
        """
        初始化客户端管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or {
            'sip_server_host': '127.0.0.1',
            'sip_server_port': 5060,
            'local_host': '127.0.0.1',
            'local_port': 5080
        }
        self.active_client: Optional[SIPClientBase] = None
    
    def create_client(self, client_type: SIPClientType) -> SIPClientBase:
        """
        创建指定类型的SIP客户端
        
        Args:
            client_type: 客户端类型
            
        Returns:
            SIPClientBase: 创建的客户端实例
        """
        client_key = f"{client_type.value}:{self.config.get('local_port')}"
        
        if client_key not in self._clients:
            if client_type == SIPClientType.UNIFIED:
                return UnifiedSIPClient(self.config)
            elif client_type == SIPClientType.SOCKET:
                # 返回我们的socket适配器实现
                return SocketSIPClientAdapter(self.config)
            elif client_type == SIPClientType.ENHANCED_SOCKET:
                # 返回增强型socket实现
                return EnhancedSocketSIPClientAdapter(self.config)
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
            elif client_type in [SIPClientType.ASTERISK_AMI, SIPClientType.ASTERISK_AGI, SIPClientType.ASTERISK_ARI]:
                # 返回Asterisk客户端实现
                return AsteriskSIPClient(self.config)
            else:
                raise ValueError(f"不支持的客户端类型: {client_type}")
        
        return self._clients[client_key]
    
    def get_client(self, client_type: SIPClientType) -> SIPClientBase:
        """
        获取指定类型的SIP客户端（带缓存）
        
        Args:
            client_type: 客户端类型
            
        Returns:
            SIPClientBase: 客户端实例
        """
        client_key = f"{client_type.value}:{self.config.get('local_port')}"
        
        if client_key not in self._clients:
            self._clients[client_key] = self.create_client(client_type)
        
        return self._clients[client_key]
    
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
    
    @classmethod
    def get_available_client_types(cls) -> list:
        """
        获取可用的客户端类型
        
        Returns:
            list: 可用客户端类型的列表
        """
        return [client_type.value for client_type in SIPClientType]
    
    def clear_cache(self):
        """
        清除客户端缓存
        """
        # 关闭所有客户端
        for client in self._clients.values():
            try:
                client.close()
            except Exception:
                pass
        
        # 清空缓存
        self._clients.clear()
        self.active_client = None
        logging.info("客户端缓存已清除")


def create_default_client(config: Dict[str, Any] = None) -> SIPClientBase:
    """
    创建默认的SIP客户端（优先使用PJSIP，回退到socket）
    
    Args:
        config: 配置参数
        
    Returns:
        SIPClientBase: 默认客户端实例
    """
    manager = SIPClientManager(config)
    
    # 尝试创建PJSIP客户端，如果失败则使用unified客户端
    try:
        # 在Windows环境下，我们可以尝试安装PJSIP
        from .pj_sip_client import PJSIP_AVAILABLE
        if PJSIP_AVAILABLE:
            logging.info("PJSIP库可用，正在创建PJSIP客户端")
            return manager.create_client(SIPClientType.PJSIP)
        else:
            logging.info("PJSIP库不可用，使用unified实现")
            return manager.create_client(SIPClientType.UNIFIED)
    except ImportError as e:
        logging.info(f"PJSIP库不可用 ({e})，使用unified实现")
        return manager.create_client(SIPClientType.UNIFIED)