"""
三层架构使用示例
展示如何使用业务层、客户端层和核心层协同工作
"""
import logging
from AutoTestForUG.business_layer.business_test_suite import BusinessTestSuite
from AutoTestForUG.business_layer.test_scenario import TestScenarioManager
from AutoTestForUG.sip_client.hybrid_client import HybridClient
from typing import Dict, Any


def create_basic_call_scenario():
    """创建基础通话测试场景"""
    scenario_manager = TestScenarioManager()
    
    # 定义基础通话测试步骤
    call_steps = [
        {
            "type": "register",
            "params": {
                "registrar_uri": "sip:proxy.example.com:5060",
                "username": "alice",
                "password": "secret"
            }
        },
        {
            "type": "make_call",
            "params": {
                "caller_uri": "sip:alice@example.com",
                "callee_uri": "sip:bob@example.com",
                "duration": 5
            }
        },
        {
            "type": "send_message",
            "params": {
                "sender_uri": "sip:alice@example.com",
                "recipient_uri": "sip:bob@example.com",
                "message": "Hello from SIP test!"
            }
        },
        {
            "type": "unregister",
            "params": {}
        }
    ]
    
    # 创建测试场景
    scenario = scenario_manager.define_scenario("basic_call_scenario", call_steps)
    return scenario_manager


def run_business_test_suite():
    """运行业务测试套件示例"""
    # 创建业务测试套件
    test_suite = BusinessTestSuite("SIP_Regression_Test_Suite", "SIP协议回归测试套件")
    
    # 创建测试场景
    scenario_manager = create_basic_call_scenario()
    
    # 添加场景到测试套件
    # 注意：这里只是示例，实际实现中需要连接各个层
    config = {
        "server_uri": "sip:test-server.local:5060",
        "timeout": 30,
        "retries": 3
    }
    
    # 执行测试套件
    results = test_suite.execute_suite(config)
    
    print(f"测试套件 '{results['suite_name']}' 执行完成")
    print(f"总体状态: {results['overall_status']}")
    print(f"执行时间: {results['end_time'] - results['start_time']}")
    
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_business_test_suite()