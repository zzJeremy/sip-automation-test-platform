"""
混合SIP测试客户端
结合socket实现和专业SIP库的优势
"""

from typing import Dict, Any, Optional
import logging
import time
from enum import Enum

from .client_manager import SIPClientManager, SIPClientType, create_default_client
from .sip_client_base import SIPClientBase


class TestResult:
    """
    测试结果类
    """
    def __init__(self, test_case: str, result: str, details: str, response_time: float = 0):
        self.test_case = test_case
        self.result = result  # "PASS" or "FAIL"
        self.details = details
        self.response_time = response_time
        self.timestamp = time.time()


class HybridSIPTestClient:
    """
    混合SIP测试客户端
    结合socket实现和专业SIP库的优势
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化混合测试客户端
        
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.client_manager = SIPClientManager(self.config)
        self.test_results = []
        self.current_client_type = SIPClientType.SOCKET  # 默认使用socket实现
        
        # 初始化默认客户端
        self.client = create_default_client(self.config)
        logging.info("混合SIP测试客户端初始化完成")
    
    def switch_client_type(self, client_type: SIPClientType):
        """
        切换客户端类型
        
        Args:
            client_type: 客户端类型
        """
        success = self.client_manager.switch_client(client_type)
        if success:
            self.current_client_type = client_type
            self.client = self.client_manager.get_current_client()
            logging.info(f"客户端类型已切换到: {client_type.value}")
        else:
            logging.error(f"切换到 {client_type.value} 客户端失败")
    
    def register_user(self, username: str, password: str, expires: int = 3600, client_type: SIPClientType = None) -> bool:
        """
        执行SIP用户注册
        
        Args:
            username: 用户名
            password: 密码
            expires: 注册有效期（秒）
            client_type: 指定客户端类型，如果为None则使用当前类型
            
        Returns:
            bool: 注册是否成功
        """
        start_time = time.time()
        
        # 选择客户端类型
        if client_type is None:
            client_type = self.current_client_type
            client = self.client
        else:
            client = self.client_manager.get_client(client_type)
        
        try:
            logging.info(f"使用 {client_type.value} 客户端进行注册: {username}")
            result = client.register(username, password, expires)
            
            response_time = time.time() - start_time
            if result:
                logging.info(f"用户 {username} 注册成功")
                test_result = TestResult(
                    test_case="REGISTRATION_TEST",
                    result="PASS",
                    details=f"用户 {username} 注册成功",
                    response_time=response_time
                )
            else:
                logging.error(f"用户 {username} 注册失败")
                test_result = TestResult(
                    test_case="REGISTRATION_TEST", 
                    result="FAIL",
                    details=f"用户 {username} 注册失败",
                    response_time=response_time
                )
            
            self.test_results.append(test_result)
            return result
            
        except Exception as e:
            logging.error(f"注册过程中发生异常: {str(e)}")
            response_time = time.time() - start_time
            test_result = TestResult(
                test_case="REGISTRATION_TEST",
                result="FAIL", 
                details=f"注册异常: {str(e)}",
                response_time=response_time
            )
            self.test_results.append(test_result)
            return False
    
    def make_call(self, from_uri: str, to_uri: str, client_type: SIPClientType = None) -> bool:
        """
        发起SIP呼叫
        
        Args:
            from_uri: 主叫URI
            to_uri: 被叫URI
            client_type: 指定客户端类型，如果为None则使用当前类型
            
        Returns:
            bool: 呼叫是否成功
        """
        start_time = time.time()
        
        # 选择客户端类型
        if client_type is None:
            client_type = self.current_client_type
            client = self.client
        else:
            client = self.client_manager.get_client(client_type)
        
        try:
            logging.info(f"使用 {client_type.value} 客户端发起呼叫: {from_uri} -> {to_uri}")
            result = client.make_call(from_uri, to_uri)
            
            response_time = time.time() - start_time
            if result:
                logging.info(f"呼叫成功: {from_uri} -> {to_uri}")
                test_result = TestResult(
                    test_case="CALL_SETUP_TEST",
                    result="PASS",
                    details=f"呼叫 {from_uri} -> {to_uri} 成功",
                    response_time=response_time
                )
            else:
                logging.error(f"呼叫失败: {from_uri} -> {to_uri}")
                test_result = TestResult(
                    test_case="CALL_SETUP_TEST",
                    result="FAIL",
                    details=f"呼叫 {from_uri} -> {to_uri} 失败",
                    response_time=response_time
                )
            
            self.test_results.append(test_result)
            return result
            
        except Exception as e:
            logging.error(f"呼叫过程中发生异常: {str(e)}")
            response_time = time.time() - start_time
            test_result = TestResult(
                test_case="CALL_SETUP_TEST",
                result="FAIL",
                details=f"呼叫异常: {str(e)}",
                response_time=response_time
            )
            self.test_results.append(test_result)
            return False
    
    def send_message(self, from_uri: str, to_uri: str, content: str, client_type: SIPClientType = None) -> bool:
        """
        发送SIP消息
        
        Args:
            from_uri: 发送方URI
            to_uri: 接收方URI
            content: 消息内容
            client_type: 指定客户端类型，如果为None则使用当前类型
            
        Returns:
            bool: 消息发送是否成功
        """
        start_time = time.time()
        
        # 选择客户端类型
        if client_type is None:
            client_type = self.current_client_type
            client = self.client
        else:
            client = self.client_manager.get_client(client_type)
        
        try:
            logging.info(f"使用 {client_type.value} 客户端发送消息: {from_uri} -> {to_uri}")
            result = client.send_message(from_uri, to_uri, content)
            
            response_time = time.time() - start_time
            if result:
                logging.info(f"消息发送成功: {from_uri} -> {to_uri}")
                test_result = TestResult(
                    test_case="MESSAGE_TEST",
                    result="PASS", 
                    details=f"消息从 {from_uri} 到 {to_uri} 发送成功",
                    response_time=response_time
                )
            else:
                logging.error(f"消息发送失败: {from_uri} -> {to_uri}")
                test_result = TestResult(
                    test_case="MESSAGE_TEST",
                    result="FAIL",
                    details=f"消息从 {from_uri} 到 {to_uri} 发送失败",
                    response_time=response_time
                )
            
            self.test_results.append(test_result)
            return result
            
        except Exception as e:
            logging.error(f"消息发送过程中发生异常: {str(e)}")
            response_time = time.time() - start_time
            test_result = TestResult(
                test_case="MESSAGE_TEST",
                result="FAIL",
                details=f"消息发送异常: {str(e)}",
                response_time=response_time
            )
            self.test_results.append(test_result)
            return False
    
    def run_comparison_test(self, username: str, password: str, from_uri: str, to_uri: str):
        """
        运行对比测试，比较不同客户端实现的性能
        
        Args:
            username: 用户名
            password: 密码
            from_uri: 主叫URI
            to_uri: 被叫URI
        """
        logging.info("开始对比测试 - 比较不同客户端实现")
        
        results = {}
        
        # 测试socket实现
        self.switch_client_type(SIPClientType.SOCKET)
        logging.info("测试Socket实现...")
        reg_result_socket = self.register_user(username, password)
        call_result_socket = self.make_call(from_uri, to_uri)
        
        results['socket'] = {
            'registration': reg_result_socket,
            'call': call_result_socket
        }
        
        # 测试PJSIP实现（如果可用）
        try:
            self.switch_client_type(SIPClientType.PJSIP)
            logging.info("测试PJSIP实现...")
            reg_result_pjsip = self.register_user(username, password)
            call_result_pjsip = self.make_call(from_uri, to_uri)
            
            results['pj_sip'] = {
                'registration': reg_result_pjsip,
                'call': call_result_pjsip
            }
        except:
            logging.info("PJSIP实现不可用，跳过测试")
        
        # 输出对比结果
        logging.info("=== 对比测试结果 ===")
        for client_type, result in results.items():
            logging.info(f"{client_type.upper()} 实现:")
            logging.info(f"  注册: {'成功' if result['registration'] else '失败'}")
            logging.info(f"  呼叫: {'成功' if result['call'] else '失败'}")
        
        return results
    
    def get_test_results(self) -> list:
        """
        获取测试结果
        
        Returns:
            list: 测试结果列表
        """
        return self.test_results
    
    def reset_test_results(self):
        """
        重置测试结果
        """
        self.test_results = []
    
    def close(self):
        """
        关闭客户端，释放资源
        """
        if self.client:
            self.client.close()


# 示例用法
if __name__ == "__main__":
    # 创建混合测试客户端
    client = HybridSIPTestClient()
    
    print("=== 混合SIP测试客户端演示 ===")
    
    # 执行注册测试
    print("\n执行注册测试...")
    reg_success = client.register_user("test_user", "test_password")
    print(f"注册结果: {'成功' if reg_success else '失败'}")
    
    # 执行呼叫测试
    print("\n执行呼叫测试...")
    call_success = client.make_call("sip:alice@127.0.0.1:5060", "sip:bob@127.0.0.1:5060")
    print(f"呼叫结果: {'成功' if call_success else '失败'}")
    
    # 执行消息测试
    print("\n执行消息测试...")
    msg_success = client.send_message(
        "sip:alice@127.0.0.1:5060", 
        "sip:bob@127.0.0.1:5060", 
        "Hello, this is a test message"
    )
    print(f"消息发送结果: {'成功' if msg_success else '失败'}")
    
    # 显示测试结果
    print("\n测试结果:")
    for result in client.get_test_results():
        print(f"- {result.test_case}: {result.result} - {result.details} (响应时间: {result.response_time:.3f}s)")
    
    # 运行对比测试
    print("\n运行对比测试...")
    comparison_results = client.run_comparison_test(
        "test_user", 
        "test_password",
        "sip:alice@127.0.0.1:5060", 
        "sip:bob@127.0.0.1:5060"
    )
    
    # 关闭客户端
    client.close()