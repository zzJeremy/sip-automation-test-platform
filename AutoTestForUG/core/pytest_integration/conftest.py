"""
pytest配置文件
集成Allure报告和其他测试增强功能
"""

import pytest
import allure
import logging
from typing import Dict, Any


def pytest_configure(config):
    """配置pytest"""
    # 配置日志
    logging.basicConfig(level=logging.INFO)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """捕获测试执行过程中的详细信息"""
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, "extra", [])
    
    if report.when == "call":
        # 添加SIP消息交互记录
        if hasattr(item.instance, 'sip_messages'):
            allure.attach(
                "\n".join(item.instance.sip_messages),
                name="SIP Messages",
                attachment_type=allure.attachment_type.TEXT
            )
        
        # 添加网络流量信息
        if hasattr(item.instance, 'network_traffic'):
            allure.attach(
                str(item.instance.network_traffic),
                name="Network Traffic",
                attachment_type=allure.attachment_type.JSON
            )


def pytest_runtest_setup(item):
    """测试设置钩子"""
    # 为测试添加标签
    if hasattr(item.function, '__name__'):
        allure.dynamic.title(item.function.__name__)
    
    # 添加描述
    if item.function.__doc__:
        allure.dynamic.description(item.function.__doc__)


@pytest.fixture(scope="function", autouse=True)
def attach_test_context(request):
    """自动附加测试上下文信息到Allure报告"""
    # 在测试开始前记录信息
    test_info = {
        "test_name": request.node.name,
        "test_module": request.module.__name__ if request.module else "unknown",
        "test_class": request.cls.__name__ if request.cls else "function",
        "start_time": __import__('time').time()
    }
    
    # 添加到Allure报告
    allure.attach(
        str(test_info),
        name="Test Context",
        attachment_type=allure.attachment_type.JSON
    )
    
    yield test_info
    
    # 测试结束后记录结束时间
    end_time = __import__('time').time()
    test_info["end_time"] = end_time
    test_info["duration"] = end_time - test_info["start_time"]
    
    allure.attach(
        str(test_info),
        name="Test Result",
        attachment_type=allure.attachment_type.JSON
    )


@pytest.fixture(scope="session")
def distributed_execution_engine():
    """分布式执行引擎fixture"""
    from core.distributed.execution_engine import DistributedExecutionEngine
    
    config = {
        "worker_threads": 3,
        "max_concurrent_per_node": 5
    }
    
    engine = DistributedExecutionEngine(config)
    
    # 添加本地节点
    engine.add_execution_node({
        "node_id": "local_node",
        "host": "localhost",
        "port": 5000,
        "max_concurrent": 3
    })
    
    yield engine
    
    # 清理资源
    engine.stop()


@pytest.fixture(scope="session")
def node_manager():
    """节点管理器fixture"""
    from core.distributed.node_manager import NodeManager
    
    config = {
        "heartbeat_interval": 30,
        "timeout_threshold": 60
    }
    
    manager = NodeManager(config)
    
    # 添加默认节点
    manager.add_node(
        node_id="default_node",
        host="localhost",
        port=5000,
        max_concurrent=5,
        capabilities=["pytest", "robot", "custom"]
    )
    
    yield manager
    
    # 清理资源
    manager.stop()


@pytest.fixture(scope="function")
def device_controller():
    """设备控制器fixture"""
    from sip_client.device_controller import DeviceControllerFactory
    
    # 创建Web设备控制器
    controller = DeviceControllerFactory.create_controller(
        'web',
        device_url='http://localhost:8080'
    )
    
    yield controller
    
    # 断开连接
    controller.disconnect()