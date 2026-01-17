"""
业务测试套件 - 用于组织和管理业务层面的测试场景
"""
import logging
from datetime import datetime
from typing import Dict, Any, List
from .enhanced_test_scenario import EnhancedTestScenario, TestScenarioManager


class BusinessTestSuite:
    def __init__(self, suite_name: str, description: str = ""):
        """初始化业务测试套件"""
        self.suite_name = suite_name
        self.description = description
        self.test_scenarios = []
        self.logger = logging.getLogger(__name__)
        
        # 创建场景管理器
        self.scenario_manager = TestScenarioManager()
        
    def add_scenario(self, scenario: EnhancedTestScenario):
        """添加测试场景到套件"""
        self.test_scenarios.append(scenario)
        self.scenario_manager.add_scenario(scenario)
        
    def execute_suite(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行整个测试套件"""
        results = {
            "suite_name": self.suite_name,
            "description": self.description,
            "start_time": datetime.now(),
            "results": [],
            "overall_status": "PASS",
            "total_scenarios": len(self.test_scenarios),
            "successful_scenarios": 0,
            "failed_scenarios": 0
        }
        
        # 执行所有场景
        scenario_results = self.scenario_manager.execute_all_scenarios()
        results["results"] = scenario_results
        
        # 统计结果
        successful_scenarios = 0
        failed_scenarios = 0
        
        for result in scenario_results:
            if result.get("status") == "passed":
                successful_scenarios += 1
            else:
                failed_scenarios += 1
                if results["overall_status"] != "ERROR":
                    results["overall_status"] = "FAIL"
        
        results["successful_scenarios"] = successful_scenarios
        results["failed_scenarios"] = failed_scenarios
        results["end_time"] = datetime.now()
        results["duration"] = (results["end_time"] - results["start_time"]).total_seconds()
        
        return results


class BusinessTestSuiteFactory:
    """业务测试套件工厂类，用于创建不同类型的测试套件"""
    
    @staticmethod
    def create_basic_sip_suite(suite_name: str = "Basic SIP Test Suite") -> BusinessTestSuite:
        """创建基础SIP协议测试套件"""
        suite = BusinessTestSuite(suite_name, "基础SIP协议功能测试套件")
        return suite
    
    @staticmethod
    def create_complex_business_suite(suite_name: str = "Complex Business Suite") -> BusinessTestSuite:
        """创建复杂业务场景测试套件"""
        suite = BusinessTestSuite(suite_name, "复杂业务场景测试套件（如IVR、呼叫转移等）")
        return suite
    
    @staticmethod
    def create_performance_suite(suite_name: str = "Performance Test Suite") -> BusinessTestSuite:
        """创建性能测试套件"""
        suite = BusinessTestSuite(suite_name, "SIP协议性能测试套件")
        return suite
    
    @staticmethod
    def create_fxo_fxs_suite(suite_name: str = "FXO/FXS Test Suite") -> BusinessTestSuite:
        """创建FXO/FXS线路测试套件"""
        suite = BusinessTestSuite(suite_name, "FXO/FXS物理线路测试套件")
        return suite