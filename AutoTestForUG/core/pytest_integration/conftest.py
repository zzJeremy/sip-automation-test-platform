"""
pytest配置文件
定义共享的fixture和钩子函数
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from AutoTestForUG.core.pytest_integration.fixtures import (
    port_pool,
    sip_client_factory,
    temp_test_dir,
    test_logger,
    basic_call_scenario,
    sip_test_config,
    pcap_collector,
    sip_trace_collector
)

# 导入所有fixtures以使pytest能够发现它们
__all__ = [
    'port_pool',
    'sip_client_factory', 
    'temp_test_dir',
    'test_logger',
    'basic_call_scenario',
    'sip_test_config',
    'pcap_collector',
    'sip_trace_collector'
]


def pytest_configure(config):
    """pytest配置钩子"""
    config.addinivalue_line(
        "markers", "sip_basic: 标记基础SIP功能测试"
    )
    config.addinivalue_line(
        "markers", "sip_call_flow: 标记SIP呼叫流程测试"
    )
    config.addinivalue_line(
        "markers", "sip_message: 标记SIP消息格式测试"
    )
    config.addinivalue_line(
        "markers", "sip_integration: 标记SIP集成测试"
    )
    config.addinivalue_line(
        "markers", "sip_performance: 标记SIP性能测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试项收集"""
    for item in items:
        # 为没有明确标记的SIP测试添加默认标记
        if "sip" in item.nodeid.lower():
            item.add_marker(pytest.mark.sip_basic)