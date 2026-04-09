"""
SIP注册业务测试示例
验证SIP用户注册功能的完整流程
"""
import pytest
import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from AutoTestForUG.core.pytest_integration.sip_dsl import SIPCallFlow, SIPMethod, SIPCallState


class TestSIPRegistration:
    """SIP注册业务测试类"""
    
    def test_register_user_flow(self):
        """测试用户注册流程"""
        # 创建一个专门用于注册的SIP流程实例
        reg_flow = SIPCallFlow()  # 不传入caller/callee参数，用于注册
        
        # 定义注册流程
        reg_flow.register_user(
            username="alice",
            password="secret123",
            server_uri="sip:sip.example.com:5060",
            expires=3600
        )
        
        # 验证注册步骤
        assert len(reg_flow.steps) == 1
        assert reg_flow.steps[0]['action'] == 'register'
        assert reg_flow.steps[0]['username'] == 'alice'
        assert reg_flow.steps[0]['server_uri'] == 'sip:sip.example.com:5060'
        
        # 验证预期结果
        assert len(reg_flow.expected_results) == 3
        assert "向 sip:sip.example.com:5060 发送REGISTER请求" in reg_flow.expected_results
        assert "用户 alice 注册成功" in reg_flow.expected_results
        
        # 验证状态
        assert reg_flow.state == SIPCallState.CONNECTED  # 表示注册成功
        
        print("用户注册流程测试通过")
        print(f"执行步骤: {reg_flow.steps[0]}")
        print(f"预期结果: {reg_flow.expected_results}")
        print(f"最终状态: {reg_flow.state}")

    def test_unregister_user_flow(self):
        """测试用户注销流程"""
        # 创建一个专门用于注销的SIP流程实例
        reg_flow = SIPCallFlow()
        
        # 定义注销流程
        reg_flow.unregister_user(
            username="alice",
            server_uri="sip:sip.example.com:5060"
        )
        
        # 验证注销步骤
        assert len(reg_flow.steps) == 1
        assert reg_flow.steps[0]['action'] == 'unregister'
        assert reg_flow.steps[0]['username'] == 'alice'
        assert reg_flow.steps[0]['server_uri'] == 'sip:sip.example.com:5060'
        
        # 验证预期结果
        assert len(reg_flow.expected_results) == 2
        assert "向 sip:sip.example.com:5060 发送UNREGISTER请求" in reg_flow.expected_results
        assert "用户 alice 注销成功" in reg_flow.expected_results
        
        # 验证状态
        assert reg_flow.state == SIPCallState.TERMINATED  # 表示注销成功
        
        print("用户注销流程测试通过")
        print(f"执行步骤: {reg_flow.steps[0]}")
        print(f"预期结果: {reg_flow.expected_results}")
        print(f"最终状态: {reg_flow.state}")

    def test_register_and_unregister_sequence(self):
        """测试注册后注销的完整序列"""
        # 创建一个完整的注册-注销流程
        reg_flow = SIPCallFlow()
        
        # 定义完整的注册-注销流程
        reg_flow.register_user(
            username="bob",
            password="secret456",
            server_uri="sip:another-server.com:5060",
            expires=1800
        ).wait(5).unregister_user(
            username="bob",
            server_uri="sip:another-server.com:5060"
        )
        
        # 验证总步骤数
        assert len(reg_flow.steps) == 3  # register, wait, unregister
        
        # 验证每一步骤
        assert reg_flow.steps[0]['action'] == 'register'
        assert reg_flow.steps[1]['action'] == 'wait'
        assert reg_flow.steps[2]['action'] == 'unregister'
        
        # 验证用户名一致
        assert reg_flow.steps[0]['username'] == 'bob'
        assert reg_flow.steps[2]['username'] == 'bob'
        
        # 验证最终状态
        assert reg_flow.state == SIPCallState.TERMINATED
        
        print("注册-等待-注销完整流程测试通过")
        print(f"总步骤数: {len(reg_flow.steps)}")
        print(f"预期结果数: {len(reg_flow.expected_results)}")
        print(f"最终状态: {reg_flow.state}")

    def test_multiple_users_registration(self):
        """测试多个用户的注册"""
        # 测试多个用户注册
        users_to_register = [
            ("charlie", "pass789", "sip:company.com:5060"),
            ("diana", "pass999", "sip:company.com:5060"),
            ("eve", "pass555", "sip:partner.com:5060")
        ]
        
        for username, password, server_uri in users_to_register:
            reg_flow = SIPCallFlow()
            reg_flow.register_user(
                username=username,
                password=password,
                server_uri=server_uri,
                expires=3600
            )
            
            assert len(reg_flow.steps) == 1
            assert reg_flow.steps[0]['username'] == username
            assert reg_flow.steps[0]['server_uri'] == server_uri
            assert reg_flow.state == SIPCallState.CONNECTED
            
        print(f"多用户注册测试通过，共测试 {len(users_to_register)} 个用户")


if __name__ == "__main__":
    # 直接运行测试以验证pytest集成
    pytest.main(["-v", __file__])