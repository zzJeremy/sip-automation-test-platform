"""
Robot Framework 适配器使用示例
展示如何使用Robot Framework风格的关键字驱动测试
"""
from AutoTestForUG.rf_adapter.robot_adapter import RobotFrameworkAdapter, SIPRobotKeywords
import tempfile
import os


def create_sample_robot_test():
    """创建示例Robot Framework测试文件"""
    robot_test_content = """*** Settings ***
Library    Collections
Library    String

*** Variables ***
${SERVER_URI}    sip:test-server.local:5060
${USER_ALICE}    alice
${PASSWORD}      secret123

*** Test Cases ***
Basic SIP Registration Test
    [Tags]    smoke    registration
    Register User    ${USER_ALICE}    ${PASSWORD}    ${SERVER_URI}
    Sleep    2s
    Unregister User    ${USER_ALICE}

Basic SIP Call Test
    [Tags]    functional    call
    Register User    alice    secret    sip:pbx.example.com:5060
    Make SIP Call    sip:alice@example.com    sip:bob@example.com    duration=10
    Sleep    15s
    End Call
    Unregister User    alice

SIP Messaging Test
    [Tags]    messaging
    Register User    alice    secret    sip:pbx.example.com:5060
    Send SIP Message    sip:alice@example.com    sip:bob@example.com    Hello from SIP test!
    Sleep    2s
    Unregister User    alice

*** Keywords ***
Register User
    [Arguments]    ${username}    ${password}    ${server_uri}
    Log    Registering user ${username} to ${server_uri}
    # 这里会调用底层pytest/SIP实现

Make SIP Call
    [Arguments]    ${caller_uri}    ${callee_uri}    ${duration}=30
    Log    Making call from ${caller_uri} to ${callee_uri} for ${duration} seconds
    # 这里会调用底层pytest/SIP实现

End Call
    Log    Ending current call
    # 这里会调用底层pytest/SIP实现
"""
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(robot_test_content)
        return temp_file.name


def run_robot_framework_test_example():
    """运行Robot Framework测试示例"""
    # 创建示例测试文件
    robot_file = create_sample_robot_test()
    
    try:
        # 创建适配器实例
        adapter = RobotFrameworkAdapter()
        
        print("Robot Framework适配器已创建")
        print(f"正在执行Robot Framework测试: {robot_file}")
        
        # 执行Robot Framework风格的测试
        result = adapter.execute_rf_style_test(robot_file)
        
        print(f"执行结果:")
        print(f"  返回码: {result['returncode']}")
        print(f"  成功: {result['success']}")
        if result['stderr']:
            print(f"  错误: {result['stderr']}")
        
        # 演示关键字映射
        print("\n关键字映射示例:")
        sample_keywords = ['Register User', 'Make SIP Call', 'End Call', 'Should Be Equal']
        for kw in sample_keywords:
            mapped = adapter.rf_to_pytest_keywords(kw)
            print(f"  {kw} -> {mapped}")
        
    finally:
        # 清理临时文件
        os.unlink(robot_file)


def demonstrate_sip_robot_keywords():
    """演示SIP Robot关键字的使用"""
    print("\nSIP Robot关键字演示:")
    
    # 创建SIP Robot关键字实例
    sip_keywords = SIPRobotKeywords()
    
    # 演示可用的方法
    print(f"可用的关键字方法:")
    for attr_name in dir(sip_keywords):
        if not attr_name.startswith('_') and callable(getattr(sip_keywords, attr_name)):
            print(f"  - {attr_name}")


if __name__ == "__main__":
    print("=== Robot Framework 适配器示例 ===")
    
    # 运行Robot Framework测试示例
    run_robot_framework_test_example()
    
    # 演示SIP Robot关键字
    demonstrate_sip_robot_keywords()
    
    print("\n=== 适配器功能总结 ===")
    print("1. 支持Robot Framework风格的测试用例")
    print("2. 将RF关键字映射到底层pytest/SIP实现")
    print("3. 非开发人员可以使用简单的关键字编写测试")
    print("4. 底层仍使用强大的pytest执行引擎")
    print("5. 保持了SIP协议的专业功能")