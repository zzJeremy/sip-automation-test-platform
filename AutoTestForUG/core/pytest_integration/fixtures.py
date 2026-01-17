"""
SIP测试框架的pytest fixtures
提供SIP客户端、端口池、测试环境等共享资源
"""
import pytest
import tempfile
import os
import time
from typing import Dict, Any, Generator
from pathlib import Path

from AutoTestForUG.basic_sip_call_tester import BasicSIPCallTester
from AutoTestForUG.port_manager import PortManager
from AutoTestForUG.error_handler import SIPTestLogger


@pytest.fixture(scope="session")
def port_pool():
    """全局端口池，用于分配SIP测试端口"""
    port_manager = PortManager(start_port=5080, end_port=5100)
    yield port_manager
    # 清理端口资源
    port_manager.release_all()


@pytest.fixture
def sip_client_factory(port_pool):
    """SIP客户端工厂fixture"""
    created_clients = []
    
    def _create_client(
        server_host: str = "127.0.0.1",
        server_port: int = 5060,
        local_host: str = "127.0.0.1",
        local_port: int = None,
        client_id: str = None
    ):
        if local_port is None:
            local_port = port_pool.get_available_port()
        
        client = BasicSIPCallTester(
            server_host=server_host,
            server_port=server_port,
            local_host=local_host,
            local_port=local_port,
            client_id=client_id
        )
        created_clients.append(client)
        return client
    
    yield _create_client
    
    # 清理所有创建的客户端
    for client in created_clients:
        try:
            if hasattr(client, 'cleanup'):
                client.cleanup()
        except Exception:
            pass


@pytest.fixture
def temp_test_dir():
    """临时测试目录"""
    temp_dir = tempfile.mkdtemp(prefix="sip_test_")
    yield Path(temp_dir)
    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_logger(temp_test_dir):
    """测试日志记录器"""
    log_file = temp_test_dir / "test.log"
    logger = SIPTestLogger("pytest_sip_test", str(log_file))
    yield logger


@pytest.fixture
def basic_call_scenario(sip_client_factory):
    """基础呼叫场景fixture"""
    caller_client = sip_client_factory(client_id="caller")
    callee_client = sip_client_factory(client_id="callee")
    
    scenario = {
        'caller_client': caller_client,
        'callee_client': callee_client,
        'caller_uri': 'sip:alice@127.0.0.1:5060',
        'callee_uri': 'sip:bob@127.0.0.1:5060',
        'call_duration': 5
    }
    
    yield scenario
    
    # 清理资源
    try:
        caller_client.cleanup()
        callee_client.cleanup()
    except Exception:
        pass


@pytest.fixture
def sip_test_config():
    """SIP测试配置"""
    config = {
        'server_host': '127.0.0.1',
        'server_port': 5060,
        'local_host': '127.0.0.1',
        'timeout': 30,
        'retry_count': 3,
        'call_duration': 5,
        'test_environment': 'local'  # local, staging, production
    }
    yield config


@pytest.fixture
def pcap_collector():
    """PCAP包收集器（模拟实现）"""
    class MockPcapCollector:
        def __init__(self):
            self.packets = []
            self.is_collecting = False
        
        def start_capture(self, interface="lo"):
            self.is_collecting = True
            print(f"开始捕获网络包，接口: {interface}")
        
        def stop_capture(self):
            self.is_collecting = False
            print("停止捕获网络包")
            return self.packets
        
        def add_packet(self, packet_data):
            if self.is_collecting:
                self.packets.append(packet_data)
    
    collector = MockPcapCollector()
    yield collector
    
    # 停止捕获
    if collector.is_collecting:
        collector.stop_capture()


@pytest.fixture
def sip_trace_collector():
    """SIP消息追踪收集器"""
    class SipTraceCollector:
        def __init__(self):
            self.traces = []
            self.current_call_id = None
        
        def start_trace(self, call_id: str = None):
            self.current_call_id = call_id or f"call_{int(time.time())}"
            print(f"开始追踪SIP会话: {self.current_call_id}")
        
        def add_trace(self, direction: str, message: str, timestamp: float = None):
            trace = {
                'call_id': self.current_call_id,
                'direction': direction,  # 'sent' or 'received'
                'message': message,
                'timestamp': timestamp or time.time()
            }
            self.traces.append(trace)
            print(f"[{direction}] {message[:100]}...")  # 只打印前100字符
        
        def get_traces(self):
            return self.traces
        
        def clear_traces(self):
            self.traces.clear()
    
    collector = SipTraceCollector()
    yield collector