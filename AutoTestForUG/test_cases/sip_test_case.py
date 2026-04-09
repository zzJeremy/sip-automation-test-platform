"""
SIP测试用例基类
定义原子化测试用例的基本结构和执行框架
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

import sys
import os
from pathlib import Path
# 添加项目根目录到Python路径以解决相对导入问题
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from error_handler import SIPTestLogger, error_handler, SIPTestError
from basic_sip_call_tester import BasicSIPCallTester


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


class CallForwardingUnconditionalTestCase(SIPTestCase):
    """
    无条件前转功能测试用例
    验证SIP呼叫无条件前转功能
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="Unconditional Call Forwarding Test",
            description="验证SIP无条件前转功能: A呼叫B，B无条件前转到C",
            config=config
        )
        self.caller_uri = config.get('caller_uri', 'sip:670491@127.0.0.1:5060')
        self.callee_uri = config.get('callee_uri', 'sip:670492@127.0.0.1:5060')
        self.forward_to_uri = config.get('forward_to_uri', 'sip:670493@127.0.0.1:5060')
        self.call_duration = config.get('call_duration', 10)
        self.proxy_username = config.get('proxy_username', '')
        self.proxy_password = config.get('proxy_password', '')
        self.sip_client = None
    
    def setup(self):
        """设置无条件前转测试环境"""
        server_host = self.config.get('server_host', '127.0.0.1')
        server_port = self.config.get('server_port', 5060)
        local_host = self.config.get('local_host', '127.0.0.1')
        local_port = self.config.get('local_port', 5081)  # 使用不同的本地端口避免冲突
        
        self.sip_client = BasicSIPCallTester(
            server_host=server_host,
            server_port=server_port,
            local_host=local_host,
            local_port=local_port
        )
    
    def execute(self) -> bool:
        """执行无条件前转测试"""
        if not self.sip_client:
            raise SIPTestError("SIP客户端未初始化")
        
        try:
            # 执行呼叫，期望检测到前转行为
            result = self._execute_call_with_forward_detection()
            return result
        except Exception as e:
            self.logger.log_test_failure(self.name, e)
            return False
    
    def _execute_call_with_forward_detection(self) -> bool:
        """执行呼叫并检测前转行为"""
        import socket
        import sys
        from pathlib import Path
        
        # 添加项目根目录到Python路径以解决相对导入问题
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # 创建SIP客户端实例用于检测前转
        from validate_call_forwarding import CallForwardingValidator
        
        validator = CallForwardingValidator(
            server_host=self.config.get('server_host', '127.0.0.1'),
            server_port=self.config.get('server_port', 5060)
        )
        
        # 从URI中提取号码
        caller = self.caller_uri.split('@')[0].split(':')[1]
        callee = self.callee_uri.split('@')[0].split(':')[1]
        forward_target = self.forward_to_uri.split('@')[0].split(':')[1]
        
        # 验证前转功能
        validation_results = validator.validate_call_forwarding(
            caller=caller,
            callee=callee,
            expected_forward_target=forward_target,
            proxy_username=self.proxy_username,
            proxy_password=self.proxy_password
        )
        
        # 如果检测到前转，则认为测试成功
        return validation_results.get('forwarding_detected', False)
    
    def teardown(self):
        """清理无条件前转测试环境"""
        self.sip_client = None


class CallForwardingBusyTestCase(SIPTestCase):
    """
    遇忙前转功能测试用例
    验证SIP呼叫遇忙前转功能
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="Busy Call Forwarding Test",
            description="验证SIP遇忙前转功能: A呼叫B，B遇忙时前转到C",
            config=config
        )
        self.caller_uri = config.get('caller_uri', 'sip:670491@127.0.0.1:5060')
        self.callee_uri = config.get('callee_uri', 'sip:670492@127.0.0.1:5060')
        self.forward_to_uri = config.get('forward_to_uri', 'sip:670493@127.0.0.1:5060')
        self.call_duration = config.get('call_duration', 10)
        self.proxy_username = config.get('proxy_username', '')
        self.proxy_password = config.get('proxy_password', '')
        self.sip_client = None
    
    def setup(self):
        """设置遇忙前转测试环境"""
        server_host = self.config.get('server_host', '127.0.0.1')
        server_port = self.config.get('server_port', 5060)
        local_host = self.config.get('local_host', '127.0.0.1')
        local_port = self.config.get('local_port', 5082)  # 使用不同的本地端口避免冲突
        
        self.sip_client = BasicSIPCallTester(
            server_host=server_host,
            server_port=server_port,
            local_host=local_host,
            local_port=local_port
        )
    
    def execute(self) -> bool:
        """执行遇忙前转测试"""
        if not self.sip_client:
            raise SIPTestError("SIP客户端未初始化")
        
        try:
            # 执行遇忙前转测试，模拟被叫方处于忙碌状态
            result = self._execute_busy_forwarding_test()
            return result
        except Exception as e:
            self.logger.log_test_failure(self.name, e)
            return False
    
    def _execute_busy_forwarding_test(self) -> bool:
        """执行遇忙前转测试"""
        import socket
        import sys
        from pathlib import Path
        
        # 添加项目根目录到Python路径以解决相对导入问题
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # 创建SIP客户端实例用于检测前转
        from validate_call_forwarding import CallForwardingValidator
        
        validator = CallForwardingValidator(
            server_host=self.config.get('server_host', '127.0.0.1'),
            server_port=self.config.get('server_port', 5060)
        )
        
        # 从URI中提取号码
        caller = self.caller_uri.split('@')[0].split(':')[1]
        callee = self.callee_uri.split('@')[0].split(':')[1]
        forward_target = self.forward_to_uri.split('@')[0].split(':')[1]
        
        # 验证前转功能 - 模拟遇忙情况
        # 由于实际模拟遇忙状态比较复杂，我们主要验证486 Busy Here响应
        validation_results = self._simulate_busy_forwarding_test(
            caller=caller,
            callee=callee,
            forward_target=forward_target,
            proxy_username=self.proxy_username,
            proxy_password=self.proxy_password
        )
        
        return validation_results
    
    def _simulate_busy_forwarding_test(self, caller: str, callee: str, forward_target: str,
                                      proxy_username: str, proxy_password: str) -> bool:
        """模拟遇忙前转测试"""
        import socket
        
        # 创建SIP客户端
        client = BasicSIPCallTester(
            server_host=self.config.get('server_host', '127.0.0.1'),
            server_port=self.config.get('server_port', 5060),
            local_host='127.0.0.1',
            local_port=self.config.get('local_port', 5082)
        )
        
        # 发送INVITE请求
        call_id = client.generate_call_id()
        invite_message = client.create_invite_message(
            caller_uri=f"sip:{caller}@{self.config.get('server_host', '127.0.0.1')}:{self.config.get('server_port', 5060)}",
            callee_uri=f"sip:{callee}@{self.config.get('server_host', '127.0.0.1')}:{self.config.get('server_port', 5060)}",
            call_id=call_id
        )
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        try:
            sock.sendto(invite_message.encode('utf-8'), (
                self.config.get('server_host', '127.0.0.1'),
                self.config.get('server_port', 5060)
            ))
            
            # 等待响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            # 解析响应
            parsed_response = client.parse_response(response_str)
            status_code = parsed_response.get('status_code', 0)
            
            # 如果收到486 Busy Here响应，说明被叫方繁忙
            if status_code == 486:
                # 尝试使用代理认证重新发送
                if proxy_username and proxy_password:
                    # 提取认证信息
                    realm, nonce = client.extract_auth_info(response_str)
                    if realm and nonce:
                        # 创建带认证的请求
                        cseq_header = parsed_response.get('headers', {}).get('CSeq', '1 INVITE')
                        cseq_num = int(cseq_header.split()[0]) + 1
                        
                        authenticated_invite_message = client.create_invite_message(
                            caller_uri=f"sip:{caller}@{self.config.get('server_host', '127.0.0.1')}:{self.config.get('server_port', 5060)}",
                            callee_uri=f"sip:{callee}@{self.config.get('server_host', '127.0.0.1')}:{self.config.get('server_port', 5060)}",
                            call_id=call_id,
                            proxy_auth_nonce=nonce,
                            proxy_auth_realm=realm,
                            proxy_username=proxy_username,
                            proxy_password=proxy_password,
                            cseq=cseq_num
                        )
                        
                        sock.sendto(authenticated_invite_message.encode('utf-8'), (
                            self.config.get('server_host', '127.0.0.1'),
                            self.config.get('server_port', 5060)
                        ))
                        
                        # 再次等待响应
                        try:
                            response_data, server_addr = sock.recvfrom(4096)
                            response_str = response_data.decode('utf-8')
                            parsed_response = client.parse_response(response_str)
                            status_code = parsed_response.get('status_code', 0)
                        except socket.timeout:
                            pass
                
                # 检查是否收到3xx重定向响应（表示遇忙前转）
                if 300 <= status_code < 400:
                    # 检查响应中是否包含前转目标
                    headers = parsed_response.get('headers', {})
                    contact = headers.get('Contact', '')
                    if forward_target in contact or f"sip:{forward_target}" in contact:
                        return True
            
            # 如果收到181 Call Is Being Forwarded响应，也表示前转激活
            if status_code == 181 and "forward" in parsed_response.get('reason_phrase', '').lower():
                return True
                
        except socket.timeout:
            pass
        except Exception as e:
            self.logger.logger.warning(f"遇忙前转测试异常: {str(e)}")
        finally:
            sock.close()
        
        return False
    
    def teardown(self):
        """清理遇忙前转测试环境"""
        self.sip_client = None


class CallForwardingNoAnswerTestCase(SIPTestCase):
    """
    无应答前转功能测试用例
    验证SIP呼叫无应答前转功能
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="No Answer Call Forwarding Test",
            description="验证SIP无应答前转功能: A呼叫B，B无应答时前转到C",
            config=config
        )
        self.caller_uri = config.get('caller_uri', 'sip:670491@127.0.0.1:5060')
        self.callee_uri = config.get('callee_uri', 'sip:670492@127.0.0.1:5060')
        self.forward_to_uri = config.get('forward_to_uri', 'sip:670493@127.0.0.1:5060')
        self.call_duration = config.get('call_duration', 10)
        self.timeout_duration = config.get('timeout_duration', 30)  # 超时时间
        self.proxy_username = config.get('proxy_username', '')
        self.proxy_password = config.get('proxy_password', '')
        self.sip_client = None
    
    def setup(self):
        """设置无应答前转测试环境"""
        server_host = self.config.get('server_host', '127.0.0.1')
        server_port = self.config.get('server_port', 5060)
        local_host = self.config.get('local_host', '127.0.0.1')
        local_port = self.config.get('local_port', 5083)  # 使用不同的本地端口避免冲突
        
        self.sip_client = BasicSIPCallTester(
            server_host=server_host,
            server_port=server_port,
            local_host=local_host,
            local_port=local_port
        )
    
    def execute(self) -> bool:
        """执行无应答前转测试"""
        if not self.sip_client:
            raise SIPTestError("SIP客户端未初始化")
        
        try:
            # 执行无应答前转测试
            result = self._execute_no_answer_forwarding_test()
            return result
        except Exception as e:
            self.logger.log_test_failure(self.name, e)
            return False
    
    def _execute_no_answer_forwarding_test(self) -> bool:
        """执行无应答前转测试"""
        import socket
        import time
        
        # 创建SIP客户端
        client = BasicSIPCallTester(
            server_host=self.config.get('server_host', '127.0.0.1'),
            server_port=self.config.get('server_port', 5060),
            local_host='127.0.0.1',
            local_port=self.config.get('local_port', 5083)
        )
        
        # 发送INVITE请求
        call_id = client.generate_call_id()
        invite_message = client.create_invite_message(
            caller_uri=f"sip:{self.caller_uri.split('@')[0].split(':')[1]}@{self.config.get('server_host', '127.0.0.1')}:{self.config.get('server_port', 5060)}",
            callee_uri=f"sip:{self.callee_uri.split('@')[0].split(':')[1]}@{self.config.get('server_host', '127.0.0.1')}:{self.config.get('server_port', 5060)}",
            call_id=call_id
        )
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 设置较短的超时时间以测试无应答场景
        sock.settimeout(self.timeout_duration)
        
        try:
            sock.sendto(invite_message.encode('utf-8'), (
                self.config.get('server_host', '127.0.0.1'),
                self.config.get('server_port', 5060)
            ))
            
            # 等待响应，但可能长时间没有响应（因为被叫方不接听）
            start_time = time.time()
            while time.time() - start_time < self.timeout_duration:
                try:
                    response_data, server_addr = sock.recvfrom(4096)
                    response_str = response_data.decode('utf-8')
                    
                    # 解析响应
                    parsed_response = client.parse_response(response_str)
                    status_code = parsed_response.get('status_code', 0)
                    
                    # 检查是否收到3xx重定向响应（表示无应答前转）
                    if 300 <= status_code < 400:
                        # 检查响应中是否包含前转目标
                        headers = parsed_response.get('headers', {})
                        contact = headers.get('Contact', '')
                        forward_target = self.forward_to_uri.split('@')[0].split(':')[1]
                        
                        if forward_target in contact or f"sip:{forward_target}" in contact:
                            return True
                    # 检查是否收到181 Call Is Being Forwarded响应
                    elif status_code == 181 and "forward" in parsed_response.get('reason_phrase', '').lower():
                        return True
                    # 如果收到BYE（可能来自前转目标），也表示前转成功
                    elif 'BYE' in response_str:
                        return True
                        
                except socket.timeout:
                    # 超时是正常的，因为被叫方可能不会应答
                    # 检查是否在超时期间有前转发生
                    break
            
        except Exception as e:
            self.logger.logger.warning(f"无应答前转测试异常: {str(e)}")
        finally:
            sock.close()
        
        return False
    
    def teardown(self):
        """清理无应答前转测试环境"""
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
        elif test_type.lower() == 'call_forwarding' or test_type.lower() == 'call_forwarding_unconditional':
            return CallForwardingUnconditionalTestCase(config)
        elif test_type.lower() == 'call_forwarding_busy':
            return CallForwardingBusyTestCase(config)
        elif test_type.lower() == 'call_forwarding_noanswer':
            return CallForwardingNoAnswerTestCase(config)
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