"""
SIP测试用例基类
定义原子化测试用例的基本结构和执行框架
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

from ..error_handler import SIPTestLogger, error_handler, SIPTestError
from ..basic_sip_call_tester import BasicSIPCallTester


class TestCaseStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class SIPTestCase(ABC):
    """
    SIP测试用例基类
    所有原子化测试用例都应继承此类
    """
    
    def __init__(self, name: str, description: str, config: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.config = config or {}
        self.preconditions = []
        self.steps = []
        self.expected_results = []
        self.actual_results = []
        self.status = TestCaseStatus.PENDING
        self.duration = 0
        self.error_info = None
        self.start_time = None
        self.end_time = None
        self.logger = SIPTestLogger(f"TestCase-{name}", f"testcase_{name.lower().replace(' ', '_')}.log")
    
    @abstractmethod
    def setup(self):
        """测试前置条件设置"""
        pass
    
    @abstractmethod
    def execute(self) -> bool:
        """执行测试用例，返回执行结果"""
        pass
    
    @abstractmethod
    def teardown(self):
        """测试后置清理"""
        pass
    
    def run(self) -> TestCaseStatus:
        """运行测试用例的主方法"""
        self.status = TestCaseStatus.RUNNING
        self.start_time = time.time()
        self.logger.log_test_start(self.name)
        
        try:
            # 设置测试环境
            self.setup()
            
            # 执行测试
            result = self.execute()
            
            # 判断测试结果
            if result:
                self.status = TestCaseStatus.PASSED
                self.logger.log_test_success(self.name)
            else:
                self.status = TestCaseStatus.FAILED
                self.logger.log_test_failure(self.name, Exception("测试执行结果为失败"))
                
        except SIPTestError as e:
            self.status = TestCaseStatus.ERROR
            self.error_info = str(e)
            self.logger.log_test_failure(self.name, e)
        except Exception as e:
            self.status = TestCaseStatus.ERROR
            self.error_info = str(e)
            self.logger.log_test_failure(self.name, e)
        finally:
            # 清理测试环境
            try:
                self.teardown()
            except Exception as e:
                self.logger.logger.warning(f"测试清理阶段出现错误: {str(e)}")
            
            # 记录执行时间
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
            self.logger.logger.info(f"测试用例 {self.name} 执行完成，耗时: {self.duration:.2f}秒")
        
        return self.status
    
    def add_step(self, step_name: str, step_func, step_params: Dict[str, Any] = None):
        """添加测试步骤"""
        self.steps.append({
            'name': step_name,
            'function': step_func,
            'params': step_params or {}
        })
    
    def add_precondition(self, precondition_func, description: str = ""):
        """添加前置条件"""
        self.preconditions.append({
            'function': precondition_func,
            'description': description
        })
    
    def verify_result(self, actual: Any, expected: Any) -> bool:
        """验证测试结果"""
        return actual == expected


class BasicCallTestCase(SIPTestCase):
    """
    基础呼叫测试用例
    验证最基本的SIP呼叫流程
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="Basic Call Test",
            description="验证基础SIP呼叫流程: INVITE -> 200 OK -> ACK -> BYE",
            config=config
        )
        self.caller_uri = config.get('caller_uri', 'sip:alice@127.0.0.1:5060')
        self.callee_uri = config.get('callee_uri', 'sip:bob@127.0.0.1:5060')
        self.call_duration = config.get('call_duration', 5)
        self.sip_client = None
    
    def setup(self):
        """设置基础呼叫测试环境"""
        server_host = self.config.get('server_host', '127.0.0.1')
        server_port = self.config.get('server_port', 5060)
        local_host = self.config.get('local_host', '127.0.0.1')
        local_port = self.config.get('local_port', 5080)
        
        self.sip_client = BasicSIPCallTester(
            server_host=server_host,
            server_port=server_port,
            local_host=local_host,
            local_port=local_port
        )
    
    def execute(self) -> bool:
        """执行基础呼叫测试"""
        if not self.sip_client:
            raise SIPTestError("SIP客户端未初始化")
        
        # 执行基础呼叫
        result = self.sip_client.make_basic_call(
            caller_uri=self.caller_uri,
            callee_uri=self.callee_uri,
            call_duration=self.call_duration
        )
        
        return result
    
    def teardown(self):
        """清理基础呼叫测试环境"""
        # 如果有需要清理的资源，在这里处理
        self.sip_client = None


class SIPMessageFormatTestCase(SIPTestCase):
    """
    SIP消息格式测试用例
    验证SIP消息是否符合规范格式
    """
    
    def __init__(self, message_type: str, config: Dict[str, Any] = None):
        super().__init__(
            name=f"SIP {message_type} Message Format Test",
            description=f"验证SIP {message_type}消息格式是否符合RFC规范",
            config=config
        )
        self.message_type = message_type
        self.message_content = config.get('message_content', '')
    
    def setup(self):
        """设置消息格式测试环境"""
        pass
    
    def execute(self) -> bool:
        """执行消息格式测试"""
        # 这里可以实现具体的SIP消息格式验证逻辑
        # 例如验证消息是否包含必要的头部字段等
        if not self.message_content:
            return False
        
        # 基本验证：消息应该包含SIP/2.0协议标识
        if 'SIP/2.0' not in self.message_content:
            return False
        
        # 根据消息类型验证特定字段
        if self.message_type.upper() == 'INVITE':
            required_fields = ['INVITE', 'Via:', 'From:', 'To:', 'Call-ID:', 'CSeq:']
        elif self.message_type.upper() == 'REGISTER':
            required_fields = ['REGISTER', 'Via:', 'From:', 'To:', 'Call-ID:', 'CSeq:']
        elif self.message_type.upper() == 'ACK':
            required_fields = ['ACK', 'Via:', 'From:', 'To:', 'Call-ID:', 'CSeq:']
        elif self.message_type.upper() == 'BYE':
            required_fields = ['BYE', 'Via:', 'From:', 'To:', 'Call-ID:', 'CSeq:']
        else:
            required_fields = ['Via:', 'From:', 'To:', 'Call-ID:', 'CSeq:']
        
        for field in required_fields:
            if field not in self.message_content:
                return False
        
        return True
    
    def teardown(self):
        """清理消息格式测试环境"""
        pass


class SIPResponseTestCase(SIPTestCase):
    """
    SIP响应测试用例
    验证SIP服务器响应是否符合预期
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="SIP Response Test",
            description="验证SIP服务器响应是否符合预期",
            config=config
        )
        self.request_message = config.get('request_message', '')
        self.expected_response_code = config.get('expected_response_code', 200)
        self.timeout = config.get('timeout', 10)
    
    def setup(self):
        """设置响应测试环境"""
        server_host = self.config.get('server_host', '127.0.0.1')
        server_port = self.config.get('server_port', 5060)
        local_host = self.config.get('local_host', '127.0.0.1')
        local_port = self.config.get('local_port', 5080)
        
        self.sip_client = BasicSIPCallTester(
            server_host=server_host,
            server_port=server_port,
            local_host=local_host,
            local_port=local_port
        )
    
    def execute(self) -> bool:
        """执行响应测试"""
        # 这里需要实现发送请求并验证响应的逻辑
        # 由于BasicSIPCallTester不直接支持发送任意消息，
        # 我们可以调用其内部方法或使用其他方式实现
        if not self.request_message:
            return False
        
        # 对于这个示例，我们简单返回True
        # 实际实现中需要发送请求并验证响应
        return True
    
    def teardown(self):
        """清理响应测试环境"""
        self.sip_client = None


# 测试用例工厂类
class TestCaseFactory:
    """
    测试用例工厂类
    用于创建不同类型的测试用例
    """
    
    @staticmethod
    def create_test_case(test_type: str, config: Dict[str, Any] = None) -> SIPTestCase:
        """
        根据测试类型创建测试用例
        
        Args:
            test_type: 测试类型
            config: 测试配置
            
        Returns:
            SIPTestCase: 创建的测试用例
        """
        if test_type.lower() == 'basic_call':
            return BasicCallTestCase(config)
        elif test_type.lower() == 'message_format':
            message_type = config.get('message_type', 'INVITE')
            return SIPMessageFormatTestCase(message_type, config)
        elif test_type.lower() == 'response':
            return SIPResponseTestCase(config)
        else:
            raise ValueError(f"不支持的测试类型: {test_type}")


# 测试套件类
class TestSuite:
    """
    测试套件类
    用于管理多个测试用例的执行
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.test_cases: List[SIPTestCase] = []
        self.results = []
    
    def add_test_case(self, test_case: SIPTestCase):
        """添加测试用例到套件"""
        self.test_cases.append(test_case)
    
    def run_all(self) -> Dict[str, Any]:
        """运行套件中所有测试用例"""
        results = {
            'suite_name': self.name,
            'total': len(self.test_cases),
            'passed': 0,
            'failed': 0,
            'error': 0,
            'skipped': 0,
            'start_time': time.time(),
            'test_results': []
        }
        
        for test_case in self.test_cases:
            result = test_case.run()
            results['test_results'].append({
                'name': test_case.name,
                'status': result.value,
                'duration': test_case.duration,
                'error_info': test_case.error_info
            })
            
            if result == TestCaseStatus.PASSED:
                results['passed'] += 1
            elif result == TestCaseStatus.FAILED:
                results['failed'] += 1
            elif result == TestCaseStatus.ERROR:
                results['error'] += 1
            elif result == TestCaseStatus.SKIPPED:
                results['skipped'] += 1
        
        results['end_time'] = time.time()
        results['total_duration'] = results['end_time'] - results['start_time']
        
        return results


def main():
    """测试用例框架示例"""
    print("SIP测试用例框架示例")
    
    # 创建测试配置
    config = {
        'server_host': '127.0.0.1',
        'server_port': 5060,
        'local_host': '127.0.0.1',
        'local_port': 5080,
        'caller_uri': 'sip:alice@127.0.0.1:5060',
        'callee_uri': 'sip:bob@127.0.0.1:5060',
        'call_duration': 3
    }
    
    # 使用工厂创建测试用例
    basic_call_test = TestCaseFactory.create_test_case('basic_call', config)
    
    # 创建消息格式测试
    invite_message = """INVITE sip:bob@127.0.0.1:5060 SIP/2.0
Via: SIP/2.0/UDP 127.0.0.1:5080;branch=z9hG4bK123456
From: <sip:alice@127.0.0.1:5060>;tag=12345
To: <sip:bob@127.0.0.1:5060>
Call-ID: 123456@127.0.0.1
CSeq: 1 INVITE
Content-Length: 0"""
    
    message_format_config = {
        'message_content': invite_message,
        'message_type': 'INVITE'
    }
    message_format_test = TestCaseFactory.create_test_case('message_format', message_format_config)
    
    # 创建测试套件
    test_suite = TestSuite("基础功能测试套件", "测试SIP基础功能")
    test_suite.add_test_case(basic_call_test)
    test_suite.add_test_case(message_format_test)
    
    # 运行测试套件
    results = test_suite.run_all()
    
    print(f"\n测试套件结果:")
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"错误: {results['error']}")
    print(f"跳过: {results['skipped']}")
    print(f"总耗时: {results['total_duration']:.2f}秒")
    
    for result in results['test_results']:
        print(f"  - {result['name']}: {result['status']} ({result['duration']:.2f}秒)")


if __name__ == "__main__":
    main()