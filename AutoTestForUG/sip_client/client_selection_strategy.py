"""
客户端自动选择策略
根据测试需求自动选择最合适的SIP客户端实现
"""
from enum import Enum
from typing import Dict, Any, List, Tuple
from .client_manager import SIPClientType, SIPClientManager
import logging
import os


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
    CONFERENCING = "conferencing"                 # 会议测试
    STRESS_TESTING = "stress_testing"             # 压力测试
    REALTIME_MONITORING = "realtime_monitoring"   # 实时监控测试
    MULTI_CODEC = "multi_codec"                   # 多编解码器测试


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
        self.logger = logging.getLogger(__name__)
        self.availability_cache = {}  # 客户端可用性缓存
    
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
        elif requirement in [TestRequirement.PERFORMANCE, TestRequirement.STRESS_TESTING]:
            # 性能和压力测试 - 使用SIPp
            return self._select_performance_client()
        elif requirement == TestRequirement.FUZZ_TESTING:
            # 模糊测试 - 使用Socket Fuzz
            return self._select_fuzz_client()
        elif requirement in [TestRequirement.COMPLEX_BUSINESS, 
                           TestRequirement.FXO_FXS_LINES,
                           TestRequirement.IVR_TESTING,
                           TestRequirement.CALL_FORWARDING,
                           TestRequirement.CONFERENCING]:
            # 复杂业务场景、FXO/FXS线路、IVR、呼叫转移、会议 - 使用Asterisk
            return self._select_complex_business_client()
        elif requirement == TestRequirement.REALTIME_MONITORING:
            # 实时监控 - 使用Socket（轻量级）
            return self._select_realtime_monitoring_client()
        elif requirement == TestRequirement.MULTI_CODEC:
            # 多编解码器测试 - 使用PJSIP（支持多种编解码器）
            return self._select_multi_codec_client()
        else:
            # 默认使用PJSIP
            return self._select_basic_protocol_client()
    
    def evaluate_client_availability(self) -> Dict[SIPClientType, bool]:
        """
        评估所有客户端的可用性
        
        Returns:
            Dict[SIPClientType, bool]: 客户端可用性状态
        """
        availability = {}
        
        for client_type in SIPClientType:
            try:
                client = self.client_manager.get_client(client_type)
                # 尝试执行一个简单操作来测试可用性
                if client_type == SIPClientType.SOCKET:
                    # 对于Socket客户端，我们只需检查能否创建实例
                    availability[client_type] = True
                elif client_type == SIPClientType.PJSIP:
                    # 对于PJSIP，检查库是否可用
                    try:
                        # 尝试导入PJSIP库
                        import pjsua2
                        availability[client_type] = True
                    except ImportError:
                        # 在Windows环境下，可能需要特殊处理
                        import sys
                        if sys.platform.startswith('win'):
                            try:
                                # 尝试备用导入方法
                                import importlib.util
                                import site
                                # 查找可能的pjsua2安装位置
                                for path in site.getsitepackages():
                                    pjsip_path = os.path.join(path, "pjsip", "pjsua2.cp3*.pyd")
                                    import glob
                                    pyd_files = glob.glob(pjsip_path)
                                    if pyd_files:
                                        spec = importlib.util.spec_from_file_location("pjsua2", pyd_files[0])
                                        pjsua2 = importlib.util.module_from_spec(spec)
                                        spec.loader.exec_module(pjsua2)
                                        availability[client_type] = True
                                        break
                                else:
                                    availability[client_type] = False
                            except Exception:
                                availability[client_type] = False
                        else:
                            availability[client_type] = False
                elif client_type == SIPClientType.SIPp_DRIVER:
                    # 对于SIPp，检查命令是否可用
                    import subprocess
                    result = subprocess.run(['which', 'sipp'], capture_output=True, text=True)
                    availability[client_type] = result.returncode == 0
                elif client_type == SIPClientType.ASTERISK_AMI:
                    # 对于Asterisk AMI，检查配置
                    asterisk_config_keys = [
                        'asterisk_host', 'ami_port', 'ami_username', 'ami_password'
                    ]
                    has_config = all(key in self.config for key in asterisk_config_keys)
                    availability[client_type] = has_config
                else:
                    # 其他类型，尝试创建实例
                    availability[client_type] = client is not None
            except Exception:
                availability[client_type] = False
        
        self.availability_cache = availability
        return availability
    
    def _select_basic_protocol_client(self) -> SIPClientType:
        """
        选择基础协议测试的客户端
        
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        # 优先尝试PJSIP库，然后回退到Socket
        availability = self.availability_cache if self.availability_cache else self.evaluate_client_availability()
        
        if availability.get(SIPClientType.PJSIP, False):
            return SIPClientType.PJSIP
        elif availability.get(SIPClientType.SOCKET, False):
            return SIPClientType.SOCKET
        else:
            # 如果都不可用，返回第一个可用的客户端
            for client_type, is_available in availability.items():
                if is_available:
                    return client_type
            # 如果都没有可用的，返回SOCKET（总是可用）
            return SIPClientType.SOCKET
    
    def _select_performance_client(self) -> SIPClientType:
        """
        选择性能测试的客户端
        
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        availability = self.availability_cache if self.availability_cache else self.evaluate_client_availability()
        
        # 优先使用SIPp进行性能测试
        if availability.get(SIPClientType.SIPp_DRIVER, False):
            return SIPClientType.SIPp_DRIVER
        elif availability.get(SIPClientType.SOCKET, False):
            # 如果SIPp不可用，使用Socket（轻量级）
            return SIPClientType.SOCKET
        else:
            # 返回第一个可用的客户端
            for client_type, is_available in availability.items():
                if is_available:
                    return client_type
            return SIPClientType.SOCKET
    
    def _select_fuzz_client(self) -> SIPClientType:
        """
        选择模糊测试的客户端
        
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        availability = self.availability_cache if self.availability_cache else self.evaluate_client_availability()
        
        # 模糊测试使用Socket Fuzz
        if availability.get(SIPClientType.SOCKET_FUZZ, False):
            return SIPClientType.SOCKET_FUZZ
        elif availability.get(SIPClientType.SOCKET, False):
            # 如果Socket Fuzz不可用，使用普通Socket
            return SIPClientType.SOCKET
        else:
            # 返回第一个可用的客户端
            for client_type, is_available in availability.items():
                if is_available:
                    return client_type
            return SIPClientType.SOCKET
    
    def _select_complex_business_client(self) -> SIPClientType:
        """
        选择复杂业务测试的客户端
        
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        availability = self.availability_cache if self.availability_cache else self.evaluate_client_availability()
        
        # 优先使用Asterisk AMI进行复杂业务测试
        asterisk_config_keys = [
            'asterisk_host', 'ami_port', 'ami_username', 'ami_password',
            'ari_port', 'ari_username', 'ari_password'
        ]
        
        has_asterisk_config = all(key in self.config for key in asterisk_config_keys)
        
        if has_asterisk_config and availability.get(SIPClientType.ASTERISK_AMI, False):
            # 如果有Asterisk配置且可用，则使用Asterisk AMI
            return SIPClientType.ASTERISK_AMI
        elif availability.get(SIPClientType.PJSIP, False):
            # 如果Asterisk不可用，使用PJSIP
            return SIPClientType.PJSIP
        elif availability.get(SIPClientType.SOCKET, False):
            # 最后回退到Socket
            return SIPClientType.SOCKET
        else:
            # 返回第一个可用的客户端
            for client_type, is_available in availability.items():
                if is_available:
                    return client_type
            return SIPClientType.SOCKET
    
    def _select_realtime_monitoring_client(self) -> SIPClientType:
        """
        选择实时监控测试的客户端
        
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        availability = self.availability_cache if self.availability_cache else self.evaluate_client_availability()
        
        # 实时监控使用轻量级的Socket客户端
        if availability.get(SIPClientType.SOCKET, False):
            return SIPClientType.SOCKET
        else:
            # 返回第一个可用的轻量级客户端
            for client_type, is_available in availability.items():
                if is_available and client_type in [SIPClientType.SOCKET, SIPClientType.SOCKET_FUZZ]:
                    return client_type
            # 如果没有轻量级客户端可用，返回任意可用的客户端
            for client_type, is_available in availability.items():
                if is_available:
                    return client_type
            return SIPClientType.SOCKET
    
    def _select_multi_codec_client(self) -> SIPClientType:
        """
        选择多编解码器测试的客户端
        
        Returns:
            SIPClientType: 推荐的客户端类型
        """
        availability = self.availability_cache if self.availability_cache else self.evaluate_client_availability()
        
        # 多编解码器测试优先使用PJSIP（支持多种编解码器）
        if availability.get(SIPClientType.PJSIP, False):
            return SIPClientType.PJSIP
        elif availability.get(SIPClientType.SOCKET, False):
            # Socket也可以进行基本的编解码器测试
            return SIPClientType.SOCKET
        else:
            # 返回第一个可用的客户端
            for client_type, is_available in availability.items():
                if is_available:
                    return client_type
            return SIPClientType.SOCKET
    
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
        elif any(keyword in scenario_lower for keyword in ['forward', 'redirect', 'transfer', 'call forwarding']):
            return self.select_client_for_requirement(TestRequirement.CALL_FORWARDING)
        elif any(keyword in scenario_lower for keyword in ['fxo', 'fxs', 'analog', 'line', 'physical line']):
            return self.select_client_for_requirement(TestRequirement.FXO_FXS_LINES)
        elif any(keyword in scenario_lower for keyword in ['performance', 'load', 'throughput', 'capacity']):
            return self.select_client_for_requirement(TestRequirement.PERFORMANCE)
        elif any(keyword in scenario_lower for keyword in ['fuzz', 'malformed', 'invalid', 'corrupted']):
            return self.select_client_for_requirement(TestRequirement.FUZZ_TESTING)
        elif any(keyword in scenario_lower for keyword in ['complex', 'advanced', 'enterprise', 'business']):
            return self.select_client_for_requirement(TestRequirement.COMPLEX_BUSINESS)
        elif any(keyword in scenario_lower for keyword in ['conference', 'multi-party', 'bridge']):
            return self.select_client_for_requirement(TestRequirement.CONFERENCING)
        elif any(keyword in scenario_lower for keyword in ['stress', 'pressure', 'overload']):
            return self.select_client_for_requirement(TestRequirement.STRESS_TESTING)
        elif any(keyword in scenario_lower for keyword in ['monitor', 'watch', 'track', 'real-time']):
            return self.select_client_for_requirement(TestRequirement.REALTIME_MONITORING)
        elif any(keyword in scenario_lower for keyword in ['codec', 'audio', 'g711', 'g729', 'opus']):
            return self.select_client_for_requirement(TestRequirement.MULTI_CODEC)
        else:
            # 默认为基础SIP协议测试
            return self.select_client_for_requirement(TestRequirement.BASIC_SIP_PROTOCOL)
    
    def get_recommendation_reason(self, requirement: TestRequirement) -> str:
        """
        获取客户端选择推荐的原因
        
        Args:
            requirement: 测试需求类型
            
        Returns:
            str: 推荐原因
        """
        reasons = {
            TestRequirement.BASIC_SIP_PROTOCOL: "基础SIP协议测试，优先使用PJSIP库实现",
            TestRequirement.COMPLEX_BUSINESS: "复杂业务场景，需要Asterisk服务器支持",
            TestRequirement.PERFORMANCE: "性能测试，需要SIPp工具进行大规模并发测试",
            TestRequirement.FUZZ_TESTING: "模糊测试，需要Socket Fuzz进行异常输入测试",
            TestRequirement.FXO_FXS_LINES: "FXO/FXS线路测试，需要Asterisk与物理线路接口",
            TestRequirement.IVR_TESTING: "IVR测试，需要Asterisk拨号计划支持",
            TestRequirement.CALL_FORWARDING: "呼叫转移测试，需要Asterisk配置支持",
            TestRequirement.CONFERENCING: "会议测试，需要Asterisk多方通话支持",
            TestRequirement.STRESS_TESTING: "压力测试，需要SIPp进行高负载测试",
            TestRequirement.REALTIME_MONITORING: "实时监控，使用轻量级Socket客户端",
            TestRequirement.MULTI_CODEC: "多编解码器测试，需要PJSIP支持多种音频编解码器"
        }
        
        return reasons.get(requirement, f"未定义的测试需求: {requirement.value}")
    
    def get_client_capabilities(self, client_type: SIPClientType) -> List[str]:
        """
        获取客户端的能力列表
        
        Args:
            client_type: 客户端类型
            
        Returns:
            List[str]: 客户端能力列表
        """
        capabilities = {
            SIPClientType.SOCKET: [
                "基础SIP协议支持",
                "手动消息构造",
                "灵活的协议定制",
                "轻量级实现"
            ],
            SIPClientType.PJSIP: [
                "完整的SIP协议栈",
                "多编解码器支持",
                "高质量音频处理",
                "稳定可靠的实现"
            ],
            SIPClientType.SIPp_DRIVER: [
                "高性能并发测试",
                "预定义场景执行",
                "大规模负载生成",
                "详细的统计报告"
            ],
            SIPClientType.SOCKET_FUZZ: [
                "异常输入测试",
                "协议健壮性验证",
                "安全漏洞探测",
                "边界条件测试"
            ],
            SIPClientType.ASTERISK_AMI: [
                "复杂业务逻辑",
                "IVR支持",
                "呼叫转移",
                "会议桥接",
                "FXO/FXS线路控制"
            ]
        }
        
        return capabilities.get(client_type, ["未知能力"])
    
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