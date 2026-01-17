"""
客户端自动选择策略
根据测试需求自动选择最合适的SIP客户端实现
"""
from enum import Enum
from typing import Dict, Any
from .client_manager import SIPClientType, SIPClientManager


class TestRequirement(Enum):
    """
    测试需求类型枚举
    """
    BASIC_SIP_PROTOCOL = "basic_sip_protocol"      # 基础SIP协议测试
    COMPLEX_BUSINESS = "complex_business"          # 复杂业务场景
    PERFORMANCE = "performance"                    # 性能测试
    FUZZ_TESTING = "fuzz_testing"                 # 模糊测试
    FXO_FXS_LINES = "fxo_fxs_lines"               # FXO/FXS线路测试
    IVR_TESTING = "ivr_testing"                   # IVR测试
    CALL_FORWARDING = "call_forwarding"           # 呼叫转移测试


class ClientSelectionStrategy:
    """
    客户端选择策略
    根据测试需求自动选择最合适的客户端实现
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化选择策略
        
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.client_manager = SIPClientManager(self.config)
    
    def select_client_for_requirement(self, requirement: TestRequirement) -> SIPClientType:
        """
        根据测试需求选择最合适的客户端类型
        
        Args:
            requirement: 测试需求类型
            
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        if requirement == TestRequirement.BASIC_SIP_PROTOCOL:
            # 基础SIP协议测试 - 优先使用PJSIP，回退到socket
            return self._select_basic_protocol_client()
        elif requirement == TestRequirement.PERFORMANCE:
            # 性能测试 - 使用SIPp
            return SIPClientType.SIPp_DRIVER
        elif requirement == TestRequirement.FUZZ_TESTING:
            # 模糊测试 - 使用Socket Fuzz
            return SIPClientType.SOCKET_FUZZ
        elif requirement in [TestRequirement.COMPLEX_BUSINESS, 
                           TestRequirement.FXO_FXS_LINES,
                           TestRequirement.IVR_TESTING,
                           TestRequirement.CALL_FORWARDING]:
            # 复杂业务场景、FXO/FXS线路、IVR、呼叫转移 - 使用Asterisk
            return self._select_complex_business_client()
        else:
            # 默认使用PJSIP
            return self._select_basic_protocol_client()
    
    def _select_basic_protocol_client(self) -> SIPClientType:
        """
        选择基础协议测试的客户端
        
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        # 优先尝试PJSIP，如果不可用则使用Socket
        try:
            # 尝试导入PJSIP库
            import pjsua2
            return SIPClientType.PJSIP
        except ImportError:
            return SIPClientType.SOCKET
    
    def _select_complex_business_client(self) -> SIPClientType:
        """
        选择复杂业务测试的客户端
        
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        # 检查Asterisk配置是否存在
        asterisk_config_keys = [
            'asterisk_host', 'ami_port', 'ami_username', 'ami_password',
            'ari_port', 'ari_username', 'ari_password'
        ]
        
        has_asterisk_config = all(key in self.config for key in asterisk_config_keys)
        
        if has_asterisk_config:
            # 如果有Asterisk配置，则使用Asterisk AMI
            return SIPClientType.ASTERISK_AMI
        else:
            # 如果没有Asterisk配置，使用PJSIP进行基本测试
            return self._select_basic_protocol_client()
    
    def select_client_by_scenario(self, scenario_description: str) -> SIPClientType:
        """
        根据场景描述选择客户端
        
        Args:
            scenario_description: 场景描述
            
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        scenario_lower = scenario_description.lower()
        
        # 根据关键词判断测试需求
        if any(keyword in scenario_lower for keyword in ['ivr', 'menu', 'interactive voice']):
            return self.select_client_for_requirement(TestRequirement.IVR_TESTING)
        elif any(keyword in scenario_lower for keyword in ['forward', 'redirect', 'transfer']):
            return self.select_client_for_requirement(TestRequirement.CALL_FORWARDING)
        elif any(keyword in scenario_lower for keyword in ['fxo', 'fxs', 'analog', 'line']):
            return self.select_client_for_requirement(TestRequirement.FXO_FXS_LINES)
        elif any(keyword in scenario_lower for keyword in ['performance', 'load', 'stress']):
            return self.select_client_for_requirement(TestRequirement.PERFORMANCE)
        elif any(keyword in scenario_lower for keyword in ['fuzz', 'malformed', 'invalid']):
            return self.select_client_for_requirement(TestRequirement.FUZZ_TESTING)
        elif any(keyword in scenario_lower for keyword in ['complex', 'advanced', 'enterprise']):
            return self.select_client_for_requirement(TestRequirement.COMPLEX_BUSINESS)
        else:
            # 默认为基础SIP协议测试
            return self.select_client_for_requirement(TestRequirement.BASIC_SIP_PROTOCOL)
    
    def get_client_for_scenario(self, requirement: TestRequirement) -> 'SIPClientBase':
        """
        获取适用于特定需求的客户端实例
        
        Args:
            requirement: 测试需求类型
            
        Returns:
            SIPClientBase: 客户端实例
        """
        client_type = self.select_client_for_requirement(requirement)
        return self.client_manager.get_client(client_type)


class HybridClient:
    """
    混合客户端
    根据测试场景自动切换不同的SIP客户端实现
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化混合客户端
        
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.strategy = ClientSelectionStrategy(self.config)
        self.current_client_type = None
        self.current_client = None
    
    def switch_to_requirement(self, requirement: TestRequirement):
        """
        切换到适用于特定需求的客户端
        
        Args:
            requirement: 测试需求类型
        """
        target_client_type = self.strategy.select_client_for_requirement(requirement)
        
        if self.current_client_type != target_client_type:
            self.current_client_type = target_client_type
            self.current_client = self.strategy.client_manager.get_client(target_client_type)
    
    def get_client(self) -> 'SIPClientBase':
        """
        获取当前客户端实例
        
        Returns:
            SIPClientBase: 当前客户端实例
        """
        if self.current_client is None:
            # 默认使用基础协议客户端
            self.switch_to_requirement(TestRequirement.BASIC_SIP_PROTOCOL)
        
        return self.current_client