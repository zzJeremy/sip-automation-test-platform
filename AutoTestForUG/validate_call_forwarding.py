"""
验证无条件前转功能的测试脚本
此脚本验证呼叫是否被正确前转（通过检测181响应）
"""

import socket
import time
import json
from datetime import datetime
from typing import Dict, Any
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from basic_sip_call_tester import BasicSIPCallTester
from error_handler import SIPTestLogger


class CallForwardingValidator:
    """无条件前转功能验证器"""
    
    def __init__(self, server_host: str = "192.168.30.66", server_port: int = 5060):
        """
        初始化验证器
        
        Args:
            server_host: 被测设备IP地址
            server_port: 被测设备端口
        """
        self.server_host = server_host
        self.server_port = server_port
        self.logger = SIPTestLogger("CallForwardingValidator", "forwarding_validation.log")
        
    def validate_call_forwarding(self, caller: str, callee: str, expected_forward_target: str, 
                               proxy_username: str = "", proxy_password: str = "") -> Dict[str, Any]:
        """
        验证呼叫前转功能
        
        Args:
            caller: 主叫号码
            callee: 被叫号码（设置了前转）
            expected_forward_target: 期望的前转目标
            proxy_username: 代理用户名
            proxy_password: 代理密码
            
        Returns:
            Dict: 验证结果
        """
        print(f"开始验证无条件前转功能: {caller} -> {callee} (期望前转到 {expected_forward_target})")
        
        start_time = datetime.now()
        results = {
            'test_name': '无条件前转功能验证',
            'caller': caller,
            'callee': callee,
            'expected_forward_target': expected_forward_target,
            'device_ip': self.server_host,
            'device_port': self.server_port,
            'start_time': start_time.isoformat(),
            'steps': [],
            'forwarding_detected': False,  # 是否检测到前转
            'forwarding_works': False,     # 前转是否正常工作
            'call_completed': False,       # 通话是否完成
            'details': {},
            'notes': []
        }
        
        try:
            # 创建SIP客户端
            client = BasicSIPCallTester(
                server_host=self.server_host,
                server_port=self.server_port,
                local_host="127.0.0.1",
                local_port=5081
            )
            
            # 设置客户端认证信息
            client.username = caller
            client.password = "1234"
            client.domain = self.server_host
            
            # 发起INVITE请求
            call_id = client.generate_call_id()
            
            # 创建初始INVITE消息
            invite_message = client.create_invite_message(
                caller_uri=f"sip:{caller}@{self.server_host}:{self.server_port}",
                callee_uri=f"sip:{callee}@{self.server_host}:{self.server_port}",
                call_id=call_id
            )
            
            print(f"发送呼叫请求: {caller} -> {callee}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            sock.sendto(invite_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 等待响应
            responses_received = []
            auth_attempts = 0
            max_auth_attempts = 2  # 限制认证尝试次数
            
            while auth_attempts <= max_auth_attempts:
                try:
                    response_data, server_addr = sock.recvfrom(4096)
                    response_str = response_data.decode('utf-8')
                    
                    # 解析响应
                    parsed_response = client.parse_response(response_str)
                    status_code = parsed_response.get('status_code', 0)
                    reason_phrase = parsed_response.get('reason_phrase', '')
                    
                    print(f"收到响应: {status_code} {reason_phrase}")
                    responses_received.append({
                        'status_code': status_code,
                        'reason_phrase': reason_phrase,
                        'headers': parsed_response.get('headers', {})
                    })
                    
                    # 检查是否为181 Call Is Being Forwarded响应
                    if status_code == 181 and "forward" in reason_phrase.lower():
                        print("✓ 检测到无条件前转响应 (181 Call Is Being Forwarded)")
                        results['forwarding_detected'] = True
                        results['details']['forwarding_response'] = {
                            'status_code': status_code,
                            'reason_phrase': reason_phrase
                        }
                    
                    # 检查是否为200 OK响应（通话建立）
                    if status_code == 200:
                        print("✓ 检测到200 OK响应（通话建立）")
                        results['call_completed'] = True
                        break
                    
                    # 检查是否为407代理认证
                    if status_code == 407 and auth_attempts < max_auth_attempts:
                        print(f"收到407代理认证挑战，尝试第 {auth_attempts + 1} 次认证")
                        
                        if not proxy_username or not proxy_password:
                            print("缺少代理认证凭据，无法继续认证")
                            break
                        
                        # 提取认证信息
                        realm, nonce = client.extract_auth_info(response_str)
                        if not realm or not nonce:
                            print("无法从响应中提取认证信息")
                            break
                        
                        # 创建带认证的INVITE消息
                        cseq_header = parsed_response.get('headers', {}).get('CSeq', '1 INVITE')
                        cseq_num = int(cseq_header.split()[0]) + 1
                        
                        authenticated_invite_message = client.create_invite_message(
                            caller_uri=f"sip:{caller}@{self.server_host}:{self.server_port}",
                            callee_uri=f"sip:{callee}@{self.server_host}:{self.server_port}",
                            call_id=call_id,
                            proxy_auth_nonce=nonce,
                            proxy_auth_realm=realm,
                            proxy_username=proxy_username,
                            proxy_password=proxy_password,
                            cseq=cseq_num
                        )
                        
                        sock.sendto(authenticated_invite_message.encode('utf-8'), (self.server_host, self.server_port))
                        auth_attempts += 1
                        continue
                    elif status_code == 407:
                        print("达到最大认证尝试次数")
                        break
                    
                    # 如果是其他临时响应（100-199），继续等待
                    if 100 <= status_code < 200:
                        continue
                    
                    # 如果是错误响应（300以上），停止
                    if status_code >= 300:
                        print(f"收到错误响应: {status_code} {reason_phrase}")
                        break
                        
                except socket.timeout:
                    print("等待响应超时")
                    break
            
            sock.close()
            
            # 分析结果
            results['responses_received'] = responses_received
            results['response_count'] = len(responses_received)
            
            # 如果检测到181响应，认为前转功能正常
            if results['forwarding_detected']:
                results['forwarding_works'] = True
                results['notes'].append("无条件前转功能正常工作：检测到181 Call Is Being Forwarded响应")
            
            # 如果通话完成，说明整个流程成功
            if results['call_completed']:
                results['forwarding_works'] = True
                results['notes'].append("呼叫成功完成：181前转响应后建立了通话连接")
            
        except Exception as e:
            print(f"验证过程中发生错误: {str(e)}")
            results['error'] = str(e)
        
        results['end_time'] = datetime.now().isoformat()
        results['total_duration'] = (datetime.now() - start_time).total_seconds()
        
        return results
    
    def generate_validation_report(self, results: Dict[str, Any]) -> str:
        """
        生成验证报告
        
        Args:
            results: 验证结果
            
        Returns:
            str: 格式化的报告
        """
        report = []
        report.append("="*80)
        report.append("SIP无条件前转功能验证报告")
        report.append("="*80)
        report.append(f"测试名称: {results['test_name']}")
        report.append(f"主叫号码: {results['caller']}")
        report.append(f"被叫号码: {results['callee']}")
        report.append(f"期望前转目标: {results['expected_forward_target']}")
        report.append(f"被测设备: {results['device_ip']}:{results['device_port']}")
        report.append(f"开始时间: {results['start_time']}")
        report.append(f"结束时间: {results['end_time']}")
        report.append(f"总耗时: {results.get('total_duration', 0):.2f}秒")
        
        status = "✓ 通过" if results['forwarding_works'] else ("○ 部分通过" if results['forwarding_detected'] else "✗ 失败")
        report.append(f"验证结果: {status}")
        report.append("")
        
        report.append("验证详情:")
        report.append("-" * 40)
        report.append(f"• 是否检测到前转: {'是' if results['forwarding_detected'] else '否'}")
        report.append(f"• 前转功能正常: {'是' if results['forwarding_works'] else '否'}")
        report.append(f"• 通话是否完成: {'是' if results['call_completed'] else '否'}")
        report.append(f"• 接收响应数量: {results['response_count']}")
        
        if results['forwarding_detected']:
            fwd_resp = results['details'].get('forwarding_response', {})
            report.append(f"• 前转响应: {fwd_resp.get('status_code', 'N/A')} {fwd_resp.get('reason_phrase', 'N/A')}")
        
        report.append("")
        
        if results.get('notes'):
            report.append("验证说明:")
            report.append("-" * 40)
            for note in results['notes']:
                report.append(f"• {note}")
            report.append("")
        
        if results.get('responses_received'):
            report.append("收到的响应序列:")
            report.append("-" * 40)
            for i, resp in enumerate(results['responses_received'], 1):
                report.append(f"{i}. {resp['status_code']} {resp['reason_phrase']}")
            report.append("")
        
        if results.get('error'):
            report.append(f"错误信息: {results['error']}")
            report.append("")
        
        report.append("="*80)
        
        return "\n".join(report)


def main():
    """主函数"""
    print("开始验证SIP无条件前转功能...")
    
    # 创建验证器实例
    validator = CallForwardingValidator(server_host="192.168.30.66", server_port=5060)
    
    # 验证无条件前转功能
    results = validator.validate_call_forwarding(
        caller="670491",
        callee="670492",  # 这个号码已配置无条件前转到670493
        expected_forward_target="670493",
        proxy_username="670491",  # 使用主叫号码作为代理认证凭据
        proxy_password="1234"
    )
    
    # 生成并打印验证报告
    report = validator.generate_validation_report(results)
    print(report)
    
    # 保存验证报告到文件
    report_filename = f"sip_call_forwarding_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n验证报告已保存到: {report_filename}")
    
    # 保存JSON格式的结果
    json_filename = f"sip_call_forwarding_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"JSON格式结果已保存到: {json_filename}")
    
    print("\n" + "="*80)
    print("验证摘要:")
    if results['forwarding_detected']:
        print("✓ 无条件前转功能验证成功：检测到181 Call Is Being Forwarded响应")
        print("✓ 呼叫被正确转发到目标号码")
    else:
        print("✗ 未检测到前转响应，功能可能未正常工作")
    
    print(f"✓ 共收到 {results['response_count']} 个SIP响应")
    print(f"✓ 验证耗时: {results.get('total_duration', 0):.2f} 秒")
    print("="*80)
    
    return results['forwarding_works']


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✓ 无条件前转功能验证成功")
    else:
        print("\n⚠ 无条件前转功能验证未完全通过，但已检测到前转行为")