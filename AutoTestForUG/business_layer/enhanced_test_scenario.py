"""
增强的测试场景管理器
支持复杂业务场景和客户端自动选择
"""
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json

# 使用绝对导入避免相对导入问题
try:
    from sip_client import ClientSelectionStrategy, TestRequirement, SIPClientBase
    from sip_client.client_manager import SIPClientManager
except ImportError:
    # 如果直接运行此模块，则尝试从项目根目录导入
    import sys
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from sip_client import ClientSelectionStrategy, TestRequirement, SIPClientBase
    from sip_client.client_manager import SIPClientManager


class ScenarioStatus(Enum):
    """测试场景状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class TestScenarioType(Enum):
    """测试场景类型"""
    BASIC_SIP = "basic_sip"
    REGISTRATION = "registration"
    CALL_SETUP = "call_setup"
    IVR = "ivr"
    CALL_FORWARDING = "call_forwarding"
    CONFERENCE = "conference"
    PERFORMANCE = "performance"
    STRESS = "stress"
    FXO_FXS = "fxo_fxs"
    CUSTOM = "custom"


class EnhancedTestScenario:
    """
    增强的测试场景管理器
    支持复杂业务场景定义和客户端自动选择
    """
    
    def __init__(self, name: str, description: str = "", requirement: TestRequirement = None, scenario_type: TestScenarioType = TestScenarioType.BASIC_SIP):
        """
        初始化测试场景
        
        Args:
            name: 场景名称
            description: 场景描述
            requirement: 测试需求类型，用于客户端选择
            scenario_type: 场景类型
        """
        self.name = name
        self.description = description
        self.requirement = requirement or TestRequirement.BASIC_SIP_PROTOCOL
        self.scenario_type = scenario_type
        self.steps: List[Dict[str, Any]] = []
        self.pre_conditions: List[Callable] = []
        self.post_conditions: List[Callable] = []
        self.status = ScenarioStatus.PENDING
        self.results: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.timeout: Optional[int] = None  # 超时时间（秒）
        self.dependencies: List[str] = []  # 依赖的其他场景
        self.tags: List[str] = []  # 场景标签
        self.metadata: Dict[str, Any] = {}  # 元数据
        self.logger = logging.getLogger(__name__)
        
        # 客户端选择策略
        self.client_strategy: Optional[ClientSelectionStrategy] = None
        self.client: Optional[SIPClientBase] = None


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
    
    def add_pre_condition(self, condition: Callable[[], bool]):
        """
        添加前置条件
        
        Args:
            condition: 前置条件检查函数
        """
        self.pre_conditions.append(condition)
    
    def add_post_condition(self, condition: Callable[[], bool]):
        """
        添加后置条件
        
        Args:
            condition: 后置条件检查函数
        """
        self.post_conditions.append(condition)
    
    def set_timeout(self, timeout_seconds: int):
        """
        设置超时时间
        
        Args:
            timeout_seconds: 超时时间（秒）
        """
        self.timeout = timeout_seconds
    
    def add_dependency(self, scenario_name: str):
        """
        添加依赖场景
        
        Args:
            scenario_name: 依赖的场景名称
        """
        self.dependencies.append(scenario_name)
    
    def add_tag(self, tag: str):
        """
        添加标签
        
        Args:
            tag: 标签
        """
        self.tags.append(tag)
    
    def set_metadata(self, **kwargs):
        """
        设置元数据
        
        Args:
            **kwargs: 元数据键值对
        """
        self.metadata.update(kwargs)
    
    def execute(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行测试场景
        
        Args:
            config: 配置参数
            
        Returns:
            Dict: 执行结果
        """
        import signal
        import threading
        
        self.status = ScenarioStatus.RUNNING
        self.start_time = datetime.now()
        self.results = []
        
        def timeout_handler():
            self.status = ScenarioStatus.TIMEOUT
            self.logger.warning(f"场景 {self.name} 超时")
        
        # 设置超时机制
        timer = None
        if self.timeout:
            timer = threading.Timer(self.timeout, timeout_handler)
            timer.start()
        
        try:
            # 检查前置条件
            for i, condition in enumerate(self.pre_conditions):
                try:
                    if not condition():
                        self.logger.warning(f"前置条件 {i+1} 失败，跳过执行场景: {self.name}")
                        self.status = ScenarioStatus.SKIPPED
                        return self._format_result()
                except Exception as e:
                    self.logger.error(f"前置条件检查异常: {str(e)}")
                    self.status = ScenarioStatus.ERROR
                    return self._format_result()
            
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
            
            # 检查后置条件
            for i, condition in enumerate(self.post_conditions):
                try:
                    if not condition():
                        self.logger.warning(f"后置条件 {i+1} 失败，标记场景为失败: {self.name}")
                        self.status = ScenarioStatus.FAILED
                        break
                except Exception as e:
                    self.logger.error(f"后置条件检查异常: {str(e)}")
                    self.status = ScenarioStatus.ERROR
                    break
            
            # 判断整体结果
            if self.status not in [ScenarioStatus.ERROR, ScenarioStatus.TIMEOUT, ScenarioStatus.SKIPPED]:
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
            # 取消定时器
            if timer and timer.is_alive():
                timer.cancel()
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
        self.execution_order: List[str] = []  # 执行顺序
        self.results_history: List[List[Dict[str, Any]]] = []  # 历史结果
    
    def add_scenario(self, scenario: EnhancedTestScenario):
        """
        添加测试场景
        
        Args:
            scenario: 测试场景
        """
        scenario.set_client_strategy(self.client_strategy)
        self.scenarios.append(scenario)
    
    def remove_scenario(self, name: str) -> bool:
        """
        移除测试场景
        
        Args:
            name: 场景名称
            
        Returns:
            bool: 是否成功移除
        """
        for i, scenario in enumerate(self.scenarios):
            if scenario.name == name:
                del self.scenarios[i]
                self.logger.info(f"已移除场景: {name}")
                return True
        return False
    
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
    
    def get_scenarios_by_tag(self, tag: str) -> List[EnhancedTestScenario]:
        """
        按标签获取场景
        
        Args:
            tag: 标签
            
        Returns:
            List[EnhancedTestScenario]: 匹配的场景列表
        """
        return [scenario for scenario in self.scenarios if tag in scenario.tags]
    
    def get_scenarios_by_type(self, scenario_type: TestScenarioType) -> List[EnhancedTestScenario]:
        """
        按类型获取场景
        
        Args:
            scenario_type: 场景类型
            
        Returns:
            List[EnhancedTestScenario]: 匹配的场景列表
        """
        return [scenario for scenario in self.scenarios if scenario.scenario_type == scenario_type]
    
    def execute_all_scenarios(self, parallel: bool = False) -> List[Dict[str, Any]]:
        """
        执行所有测试场景
        
        Args:
            parallel: 是否并行执行
            
        Returns:
            List: 所有场景的执行结果
        """
        if parallel:
            return self._execute_scenarios_parallel()
        else:
            return self._execute_scenarios_sequential()
    
    def _execute_scenarios_sequential(self) -> List[Dict[str, Any]]:
        """
        顺序执行所有测试场景
        
        Returns:
            List: 所有场景的执行结果
        """
        results = []
        
        # 检查依赖关系并排序
        ordered_scenarios = self._get_ordered_scenarios()
        
        for scenario in ordered_scenarios:
            self.logger.info(f"开始执行场景: {scenario.name}")
            result = scenario.execute(self.config)
            results.append(result)
        
        self.results_history.append(results)
        return results
    
    def _execute_scenarios_parallel(self) -> List[Dict[str, Any]]:
        """
        并行执行所有测试场景
        
        Returns:
            List: 所有场景的执行结果
        """
        import concurrent.futures
        from copy import deepcopy
        
        results = []
        
        # 分组执行有依赖关系的场景
        grouped_scenarios = self._group_scenarios_by_dependencies()
        
        for group in grouped_scenarios:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(group), 4)) as executor:
                # 为每个线程创建独立的配置副本
                futures = []
                for scenario in group:
                    scenario_copy = deepcopy(scenario)
                    scenario_copy.set_client_strategy(ClientSelectionStrategy(deepcopy(self.config)))
                    future = executor.submit(scenario_copy.execute, deepcopy(self.config))
                    futures.append((future, scenario.name))
                
                for future, name in futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        self.logger.error(f"并行执行场景 {name} 失败: {str(e)}")
                        results.append({
                            'scenario_name': name,
                            'status': 'error',
                            'error': str(e)
                        })
        
        self.results_history.append(results)
        return results
    
    def _get_ordered_scenarios(self) -> List[EnhancedTestScenario]:
        """
        根据依赖关系获取有序的场景列表
        
        Returns:
            List[EnhancedTestScenario]: 有序的场景列表
        """
        # 简单的拓扑排序实现
        visited = set()
        ordering = []
        
        def dfs(scenario_name):
            if scenario_name in visited:
                return
            visited.add(scenario_name)
            
            scenario = self.get_scenario_by_name(scenario_name)
            if scenario:
                for dep in scenario.dependencies:
                    dfs(dep)
                ordering.append(scenario)
        
        for scenario in self.scenarios:
            dfs(scenario.name)
        
        return ordering
    
    def _group_scenarios_by_dependencies(self) -> List[List[EnhancedTestScenario]]:
        """
        根据依赖关系对场景进行分组
        
        Returns:
            List[List[EnhancedTestScenario]]: 分组后的场景列表
        """
        # 将有依赖关系的场景分到不同的组
        groups = []
        unprocessed = [s for s in self.scenarios]
        
        while unprocessed:
            current_group = []
            remaining = []
            
            for scenario in unprocessed:
                # 检查场景的依赖是否都在之前的组中
                deps_met = True
                for dep in scenario.dependencies:
                    dep_found = False
                    # 检查是否在之前已处理的组中
                    for prev_group in groups:
                        if any(s.name == dep for s in prev_group):
                            dep_found = True
                            break
                    if not dep_found:
                        deps_met = False
                        break
                
                if deps_met:
                    current_group.append(scenario)
                else:
                    remaining.append(scenario)
            
            if current_group:
                groups.append(current_group)
                unprocessed = remaining
            else:
                # 如果无法找到任何满足依赖的场景，说明存在循环依赖
                groups.append(remaining)
                break
        
        return groups
    
    def execute_scenario_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        按名称执行特定场景
        
        Args:
            name: 场景名称
            
        Returns:
            Optional[Dict]: 场景执行结果
        """
        scenario = self.get_scenario_by_name(name)
        if scenario:
            result = scenario.execute(self.config)
            return result
        
        self.logger.warning(f"未找到场景: {name}")
        return None
    
    def execute_scenarios_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        按标签执行场景
        
        Args:
            tag: 标签
            
        Returns:
            List[Dict]: 执行结果列表
        """
        scenarios = self.get_scenarios_by_tag(tag)
        results = []
        
        for scenario in scenarios:
            result = scenario.execute(self.config)
            results.append(result)
        
        return results
    
    def execute_scenarios_by_type(self, scenario_type: TestScenarioType) -> List[Dict[str, Any]]:
        """
        按类型执行场景
        
        Args:
            scenario_type: 场景类型
            
        Returns:
            List[Dict]: 执行结果列表
        """
        scenarios = self.get_scenarios_by_type(scenario_type)
        results = []
        
        for scenario in scenarios:
            result = scenario.execute(self.config)
            results.append(result)
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """
        生成执行报告
        
        Returns:
            Dict: 报告数据
        """
        if not self.results_history:
            return {"message": "没有执行历史记录"}
        
        latest_results = self.results_history[-1]
        
        total_scenarios = len(latest_results)
        passed_scenarios = sum(1 for r in latest_results if r.get('status') == 'passed')
        failed_scenarios = sum(1 for r in latest_results if r.get('status') == 'failed')
        error_scenarios = sum(1 for r in latest_results if r.get('status') == 'error')
        skipped_scenarios = sum(1 for r in latest_results if r.get('status') == 'skipped')
        
        # 计算总执行时间
        total_duration = sum(r.get('duration', 0) for r in latest_results)
        
        report = {
            "summary": {
                "total_scenarios": total_scenarios,
                "passed": passed_scenarios,
                "failed": failed_scenarios,
                "errors": error_scenarios,
                "skipped": skipped_scenarios,
                "success_rate": round(passed_scenarios / total_scenarios * 100, 2) if total_scenarios > 0 else 0,
                "total_duration": round(total_duration, 2)
            },
            "details": latest_results
        }
        
        return report
    
    def save_report(self, filename: str = None) -> str:
        """
        保存执行报告到文件
        
        Args:
            filename: 文件名，如果不提供则自动生成
            
        Returns:
            str: 保存的文件路径
        """
        import os
        from datetime import datetime
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sip_test_report_{timestamp}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"报告已保存到: {filename}")
        return os.path.abspath(filename)