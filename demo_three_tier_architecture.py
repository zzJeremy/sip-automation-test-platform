"""
三层架构演示示例
展示如何使用新的SIP自动化测试平台架构
"""
from AutoTestForUG.sip_client import (
    TestOrchestrator, 
    TestCase, 
    TestType,
    SIPpDriverClient,
    SocketFuzzClient,
    PJSIPSIPClient
)
from typing import Dict, Any


def demonstrate_three_layer_architecture():
    """演示三层架构的使用"""
    print("=== SIP自动化测试平台三层架构演示 ===\n")
    
    # 1. 配置测试环境
    config = {
        "server_host": "127.0.0.1",
        "server_port": 5060,
        "domain": "example.com",
        "local_ip": "127.0.0.1",
        "local_port": 5080
    }
    
    # 2. 创建测试调度器（智能调度层）
    print("1. 创建测试调度器...")
    orchestrator = TestOrchestrator(config)
    
    # 3. 定义测试用例（展示不同类型测试的自动调度）
    print("2. 定义测试用例...")
    
    test_cases = [
        # 性能测试 - 会被调度到SIPpDriverClient
        TestCase(
            name="性能注册测试",
            test_type=TestType.PERFORMANCE,
            description="高并发注册性能测试",
            parameters={
                "username": "perf_user",
                "password": "password",
                "concurrent_calls": 50
            },
            priority=4
        ),
        
        # 安全测试 - 会被调度到SocketFuzzClient
        TestCase(
            name="安全注册测试",
            test_type=TestType.SECURITY,
            description="使用畸形报文进行安全测试",
            parameters={
                "username": "fuzz_user",
                "password": "password"
            },
            priority=5
        ),
        
        # 功能测试 - 会被调度到PJSIPSIPClient或SocketSIPClient
        TestCase(
            name="功能呼叫测试",
            test_type=TestType.FUNCTIONAL,
            description="基本呼叫功能测试",
            parameters={
                "caller": "caller_user",
                "callee": "callee_user",
                "message": "Hello from functional test"
            },
            priority=3
        ),
        
        # 合规性测试 - 会被调度到PJSIPSIPClient
        TestCase(
            name="合规性测试",
            test_type=TestType.COMPLIANCE,
            description="SIP协议合规性验证",
            parameters={
                "username": "compliance_user",
                "password": "password"
            },
            priority=2
        )
    ]
    
    # 4. 执行测试套件
    print("3. 执行测试套件...")
    results = orchestrator.execute_test_suite(test_cases)
    
    # 5. 输出结果摘要
    print("\n4. 测试结果摘要:")
    print(f"总测试数: {results['total_tests']}")
    print(f"成功数: {results['successful_tests']}")
    print(f"失败数: {results['failed_tests']}")
    print(f"成功率: {results['success_rate']:.2%}")
    
    print("\n详细结果:")
    for result in results['results']:
        test_name = result.get('test_case', 'Unknown')
        success = result.get('success', False)
        test_type = result.get('test_type', 'Unknown')
        print(f"  - {test_name} ({test_type}): {'✓' if success else '✗'}")
    
    return results


def demonstrate_direct_client_usage():
    """演示直接使用客户端"""
    print("\n=== 直接客户端使用演示 ===\n")
    
    config = {
        "server_host": "127.0.0.1",
        "server_port": 5060,
        "domain": "example.com",
        "local_ip": "127.0.0.1",
        "local_port": 5080
    }
    
    # 1. 使用SIPpDriverClient进行性能测试
    print("1. 使用SIPpDriverClient进行性能测试...")
    sipp_client = SIPpDriverClient(config)
    perf_result = sipp_client.register("perf_test", "password", expires=300)
    print(f"   性能测试注册结果: {'成功' if perf_result else '失败'}")
    
    # 2. 使用SocketFuzzClient进行安全测试
    print("2. 使用SocketFuzzClient进行安全测试...")
    fuzz_config = {**config, "sip_server_host": "127.0.0.1", "sip_server_port": 5060}
    fuzz_client = SocketFuzzClient(fuzz_config)
    fuzz_result = fuzz_client.register("fuzz_test", "password")
    print(f"   模糊测试注册结果: {'成功' if fuzz_result else '失败'} (服务器是否稳定?)")
    
    # 3. 使用PJSIPSIPClient进行功能测试
    print("3. 使用PJSIPSIPClient进行功能测试...")
    try:
        pj_client = PJSIPSIPClient(config)
        func_result = pj_client.register("func_test", "password")
        print(f"   功能测试注册结果: {'成功' if func_result else '失败'}")
    except Exception as e:
        print(f"   PJSIP客户端不可用: {e}")


if __name__ == "__main__":
    # 运行演示
    try:
        demonstrate_three_layer_architecture()
        demonstrate_direct_client_usage()
        print("\n=== 演示完成 ===")
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()