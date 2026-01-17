"""
增强的测试场景管理器
支持复杂业务场景和客户端自动选择
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from ..sip_client import ClientSelectionStrategy, TestRequirement, SIPClientBase
from ..sip_client.client_manager import SIPClientManager


class ScenarioStatus(Enum):
    """测试场景状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class EnhancedTestScenario:
    """
    增强的测试场景管理器
    支持复杂业务场景定义和客户端自动选择
    """
    
    def __init__(self, name: str, description: str = "", requirement: TestRequirement = None):
        """
        初始化测试场景
        
        Args:
            name: 场景名称
            description: 场景描述
            requirement: 测试需求类型，用于客户端选择
        """
        self.name = name
        self.description = description
        self.requirement = requirement or TestRequirement.BASIC_SIP_PROTOCOL
        self.steps: List[Dict[str, Any]] = []
        self.status = ScenarioStatus.PENDING
        self.results: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.logger = logging.getLogger(__name__)
        
        # 客户端选择策略
        self.client_strategy: Optional[ClientSelectionStrategy] = None
        self.client: Optional[SIPClientBase] = None
    
    def set_client_strategy(self, strategy: ClientSelectionStrategy):
        """
        设置客户端选择策略
        
        Args:
            strategy: 客户端选择策略
        """
        self.client_strategy = strategy
        # 根据需求获取合适的客户端
        if strategy:
            self.client = strategy.get_client_for_scenario(self.requirement)
    
    def add_step(self, step: Dict[str, Any]):
        """
        添加测试步骤
        
        Args:
            step: 测试步骤定义，包含type、params等信息
        """
        self.steps.append(step)
    
    def execute(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行测试场景
        
        Args:
            config: 配置参数
            
        Returns:
            Dict: 执行结果
        """
        self.status = ScenarioStatus.RUNNING
        self.start_time = datetime.now()
        self.results = []
        
        try:
            # 如果还没有客户端策略，创建默认策略
            if not self.client_strategy:
                self.client_strategy = ClientSelectionStrategy(config)
                self.client = self.client_strategy.get_client_for_scenario(self.requirement)
            
            # 执行所有步骤
            for step in self.steps:
                step_result = self._execute_step(step, config)
                self.results.append(step_result)
                
                # 如果步骤失败且配置为失败时停止，则中断执行
                if not step_result.get('success', True) and config.get('stop_on_failure', False):
                    self.logger.warning(f"步骤失败，根据配置停止执行: {step_result.get('step_name', 'Unknown')}")
                    break
            
            # 判断整体结果
            all_passed = all(result.get('success', False) for result in self.results)
            self.status = ScenarioStatus.PASSED if all_passed else ScenarioStatus.FAILED
            
        except Exception as e:
            self.logger.error(f"执行测试场景失败: {str(e)}")
            self.status = ScenarioStatus.ERROR
            self.results.append({
                'step_name': 'scenario_execution',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            })
        finally:
            self.end_time = datetime.now()
        
        return self._format_result()
    
    def _execute_step(self, step: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个测试步骤
        
        Args:
            step: 步骤定义
            config: 配置参数
            
        Returns:
            Dict: 步骤执行结果
        """
        step_type = step.get('type', '')
        step_params = step.get('params', {})
        step_name = step.get('name', step_type)
        
        result = {
            'step_name': step_name,
            'type': step_type,
            'success': False,
            'details': {},
            'timestamp': datetime.now()
        }
        
        try:
            if not self.client:
                raise Exception("客户端未初始化")
            
            # 根据步骤类型执行相应的操作
            if step_type == 'register':
                username = step_params.get('username', '')
                password = step_params.get('password', '')
                expires = step_params.get('expires', 3600)
                
                success = self.client.register(username, password, expires)
                result['success'] = success
                result['details'] = {'action': 'register', 'username': username, 'expires': expires}
                
            elif step_type == 'make_call':
                from_uri = step_params.get('from_uri', '')
                to_uri = step_params.get('to_uri', '')
                timeout = step_params.get('timeout', 30)
                
                success = self.client.make_call(from_uri, to_uri, timeout)
                result['success'] = success
                result['details'] = {'action': 'make_call', 'from': from_uri, 'to': to_uri}
                
            elif step_type == 'configure_ivr':
                # 仅在Asterisk客户端支持IVR配置
                if hasattr(self.client, 'configure_ivr'):
                    ivr_config = step_params.get('ivr_config', {})
                    success = self.client.configure_ivr(ivr_config)
                    result['success'] = success
                    result['details'] = {'action': 'configure_ivr', 'config': ivr_config}
                else:
                    result['success'] = False
                    result['details'] = {'action': 'configure_ivr', 'error': '客户端不支持IVR配置'}
                    
            elif step_type == 'configure_call_forwarding':
                # 仅在Asterisk客户端支持呼叫转移配置
                if hasattr(self.client, 'configure_call_forwarding'):
                    forward_config = step_params.get('forward_config', {})
                    success = self.client.configure_call_forwarding(forward_config)
                    result['success'] = success
                    result['details'] = {'action': 'configure_call_forwarding', 'config': forward_config}
                else:
                    result['success'] = False
                    result['details'] = {'action': 'configure_call_forwarding', 'error': '客户端不支持呼叫转移配置'}
            else:
                # 未知步骤类型
                result['success'] = False
                result['details'] = {'action': step_type, 'error': f'未知的步骤类型: {step_type}'}
                
        except Exception as e:
            result['success'] = False
            result['details'] = {'action': step_type, 'error': str(e)}
            self.logger.error(f"执行步骤失败 {step_name}: {str(e)}")
        
        return result
    
    def _format_result(self) -> Dict[str, Any]:
        """
        格式化执行结果
        
        Returns:
            Dict: 格式化的结果
        """
        return {
            'scenario_name': self.name,
            'description': self.description,
            'requirement': self.requirement.value,
            'status': self.status.value,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0,
            'total_steps': len(self.steps),
            'successful_steps': len([r for r in self.results if r.get('success', False)]),
            'failed_steps': len([r for r in self.results if not r.get('success', False)]),
            'results': self.results
        }


class TestScenarioManager:
    """
    测试场景管理器
    管理多个测试场景的执行
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化场景管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.scenarios: List[EnhancedTestScenario] = []
        self.client_strategy = ClientSelectionStrategy(self.config)
        self.logger = logging.getLogger(__name__)
    
    def add_scenario(self, scenario: EnhancedTestScenario):
        """
        添加测试场景
        
        Args:
            scenario: 测试场景
        """
        scenario.set_client_strategy(self.client_strategy)
        self.scenarios.append(scenario)
    
    def execute_all_scenarios(self) -> List[Dict[str, Any]]:
        """
        执行所有测试场景
        
        Returns:
            List: 所有场景的执行结果
        """
        results = []
        
        for scenario in self.scenarios:
            self.logger.info(f"开始执行场景: {scenario.name}")
            result = scenario.execute(self.config)
            results.append(result)
        
        return results
    
    def execute_scenario_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        按名称执行特定场景
        
        Args:
            name: 场景名称
            
        Returns:
            Optional[Dict]: 场景执行结果
        """
        for scenario in self.scenarios:
            if scenario.name == name:
                return scenario.execute(self.config)
        
        self.logger.warning(f"未找到场景: {name}")
        return None
    
    def get_scenario_by_name(self, name: str) -> Optional[EnhancedTestScenario]:
        """
        按名称获取场景对象
        
        Args:
            name: 场景名称
            
        Returns:
            Optional[EnhancedTestScenario]: 场景对象
        """
        for scenario in self.scenarios:
            if scenario.name == name:
                return scenario
        
        return None