"""
简单SIP测试示例 - 验证框架架构可行性（纯单元测试版本）
此测试将验证SIP DSL和核心组件的逻辑，而不实际连接到SIP服务器
"""
import pytest
import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from AutoTestForUG.core.pytest_integration.sip_dsl import SIPCallFlow, SIPMessageValidator, SIPMethod, SIPCallState
from unittest.mock import Mock, patch


class TestSimpleSIPCall:
    """简单SIP呼叫测试类（纯单元测试）"""
    
    def test_sip_call_flow_creation(self):
        """测试SIP呼叫流程对象创建"""
        call_flow = SIPCallFlow(
            caller_uri='sip:alice@127.0.0.1:5060',
            callee_uri='sip:bob@127.0.0.1:5060'
        )
        
        # 验证对象属性
        assert call_flow.caller_uri == 'sip:alice@127.0.0.1:5060'
        assert call_flow.callee_uri == 'sip:bob@127.0.0.1:5060'
        assert call_flow.state == SIPCallState.IDLE
        assert len(call_flow.steps) == 0
        assert len(call_flow.expected_results) == 0
        assert call_flow.call_id is not None
        
        print(f"SIP Call Flow创建成功: {call_flow.call_id}")
        print(f"初始状态: {call_flow.state}")

    def test_basic_invite_ack_bye_flow(self):
        """测试基础INVITE-ACK-BYE流程定义（不执行实际连接）"""
        call_flow = SIPCallFlow(
            caller_uri='sip:alice@127.0.0.1:5060',
            callee_uri='sip:bob@127.0.0.1:5060'
        )
        
        # 定义呼叫流程
        call_flow.make_call(duration=3)\
                  .wait_for_ringing()\
                  .wait_for_answer()\
                  .wait(2)\
                  .terminate_call()
        
        # 验证步骤数量和内容
        assert len(call_flow.steps) == 5  # make_call, wait_for_ringing, wait_for_answer, wait, terminate_call
        assert len(call_flow.expected_results) >= 5  # 至少有5个预期结果
        
        # 验证第一步是make_call
        assert call_flow.steps[0]['action'] == 'make_call'
        assert call_flow.steps[0]['caller_uri'] == 'sip:alice@127.0.0.1:5060'
        assert call_flow.steps[0]['callee_uri'] == 'sip:bob@127.0.0.1:5060'
        
        # 验证最后一步是terminate_call
        assert call_flow.steps[-1]['action'] == 'send_bye'
        
        # 验证预期结果包含关键信息
        expected_results_str = " ".join(call_flow.expected_results)
        assert "INVITE" in expected_results_str
        assert "200 OK" in expected_results_str
        assert "BYE" in expected_results_str
        
        # 验证最终状态
        assert call_flow.state == SIPCallState.TERMINATED
        
        print(f"测试步骤数量: {len(call_flow.steps)}")
        print(f"预期结果数量: {len(call_flow.expected_results)}")
        print(f"最终呼叫状态: {call_flow.state}")

    def test_sip_message_validation(self):
        """测试SIP消息验证功能"""
        # 测试有效的INVITE消息
        valid_invite = """INVITE sip:user@example.com SIP/2.0
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK123456
From: <sip:test@test.com>;tag=12345
To: <sip:user@example.com>
Call-ID: 12345@example.com
CSeq: 1 INVITE
Content-Length: 0

"""
        result = SIPMessageValidator.validate_invite(valid_invite)
        assert result is True  # 有效消息应返回True
        
        # 测试无效的INVITE消息（缺少必要头部）
        invalid_invite = """INVITE sip:user@example.com SIP/2.0
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK123456
From: <sip:test@test.com>;tag=12345
To: <sip:user@example.com>
"""
        result = SIPMessageValidator.validate_invite(invalid_invite)
        assert result is False  # 无效消息应返回False
        
        print("SIP消息验证测试通过")

    def test_sip_method_enum(self):
        """测试SIP方法枚举"""
        assert SIPMethod.INVITE.value == "INVITE"
        assert SIPMethod.ACK.value == "ACK"
        assert SIPMethod.BYE.value == "BYE"
        assert SIPMethod.CANCEL.value == "CANCEL"
        assert SIPMethod.OPTIONS.value == "OPTIONS"
        assert SIPMethod.REGISTER.value == "REGISTER"
        assert SIPMethod.MESSAGE.value == "MESSAGE"
        
        print("SIP方法枚举测试通过")

    def test_sip_call_state_enum(self):
        """测试SIP呼叫状态枚举"""
        assert SIPCallState.IDLE.value == "idle"
        assert SIPCallState.CALLING.value == "calling"
        assert SIPCallState.RINGING.value == "ringing"
        assert SIPCallState.CONNECTED.value == "connected"
        assert SIPCallState.TERMINATED.value == "terminated"
        
        print("SIP呼叫状态枚举测试通过")


if __name__ == "__main__":
    # 直接运行测试以验证pytest集成
    pytest.main(["-v", __file__])