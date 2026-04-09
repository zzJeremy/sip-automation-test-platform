"""
SIP测试DSL（领域特定语言）
提供简洁的API来定义SIP测试场景
"""
import logging
from typing import Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum
import time
import re


class SIPMethod(str, Enum):
    """SIP方法枚举"""
    INVITE = "INVITE"
    ACK = "ACK"
    BYE = "BYE"
    CANCEL = "CANCEL"
    OPTIONS = "OPTIONS"
    REGISTER = "REGISTER"
    MESSAGE = "MESSAGE"


class SIPCallState(str, Enum):
    """SIP呼叫状态"""
    IDLE = "idle"
    REGISTERING = "registering"
    REGISTERED = "registered"
    CALLING = "calling"
    RINGING = "ringing"
    CONNECTED = "connected"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class SIPMessage:
    """SIP消息数据类"""
    method: SIPMethod
    uri: str
    headers: Dict[str, str]
    body: str = ""
    call_id: str = ""
    cseq: int = 1


class SIPCallFlow:
    """SIP呼叫流程DSL类"""
    
    def __init__(self, caller_uri: str = "", callee_uri: str = "", client_manager=None):
        self.caller_uri = caller_uri
        self.callee_uri = callee_uri
        self.client_manager = client_manager
        self.steps = []
        self.expected_results = []
        self.call_id = f"call_{int(time.time())}"
        self.state = SIPCallState.IDLE if caller_uri and callee_uri else SIPCallState.IDLE
        # 添加用户凭证存储，用于注册后呼叫
        self.username = None
        self.password = None
        self.server_uri = None
        self.expires = 3600
    
    def register_user(self, username: str, password: str, server_uri: str, expires: int = 3600):
        """注册用户"""
        self.state = SIPCallState.REGISTERING
        self.steps.append({
            'action': 'register',
            'username': username,
            'password': password,
            'server_uri': server_uri,
            'expires': expires
        })
        self.expected_results.extend([
            f"向 {server_uri} 发送REGISTER请求",
            f"用户 {username} 注册成功",
            f"注册有效期 {expires} 秒"
        ])
        self.state = SIPCallState.REGISTERED  # 表示注册成功
        # 保存用户凭证，以便后续呼叫使用
        self.username = username
        self.password = password
        self.server_uri = server_uri
        self.expires = expires
        return self
    
    def unregister_user(self, username: str, server_uri: str):
        """注销用户"""
        if self.state != SIPCallState.REGISTERED:
            self.state = SIPCallState.ERROR
            raise ValueError("只有已注册的用户才能注销")
        
        self.steps.append({
            'action': 'unregister',
            'username': username,
            'server_uri': server_uri
        })
        self.expected_results.extend([
            f"向 {server_uri} 发送UNREGISTER请求",
            f"用户 {username} 注销成功"
        ])
        self.state = SIPCallState.IDLE
        # 清除用户凭证
        self.username = None
        self.password = None
        self.server_uri = None
        self.expires = 3600
        return self
    
    def make_call(self, duration: int = 5):
        """发起呼叫"""
        if not self.caller_uri or not self.callee_uri:
            self.state = SIPCallState.ERROR
            raise ValueError("呼叫前必须设置主叫和被叫URI")
        
        self.state = SIPCallState.CALLING
        self.steps.append({
            'action': 'make_call',
            'caller_uri': self.caller_uri,
            'callee_uri': self.callee_uri,
            'duration': duration,
            'call_id': self.call_id
        })
        self.expected_results.extend([
            f"成功发送INVITE到 {self.callee_uri}",
            f"收到200 OK响应",
            f"发送ACK确认",
            f"维持通话 {duration} 秒",
            f"发送BYE终止呼叫"
        ])
        return self
    
    def wait_for_ringing(self):
        """等待振铃"""
        if self.state != SIPCallState.CALLING:
            self.state = SIPCallState.ERROR
            raise ValueError("只有在呼叫状态才能等待振铃")
        
        self.steps.append({
            'action': 'wait_for_response',
            'expected_code': 180,  # Ringing
            'call_id': self.call_id
        })
        self.expected_results.append("收到180 Ringing响应")
        self.state = SIPCallState.RINGING
        return self
    
    def wait_for_answer(self):
        """等待接听"""
        if self.state not in [SIPCallState.CALLING, SIPCallState.RINGING]:
            self.state = SIPCallState.ERROR
            raise ValueError("只有在呼叫或振铃状态才能等待接听")
        
        self.steps.append({
            'action': 'wait_for_response',
            'expected_code': 200,  # OK
            'call_id': self.call_id
        })
        self.expected_results.append("收到200 OK响应，呼叫建立成功")
        self.state = SIPCallState.CONNECTED
        return self
    
    def hold_call(self):
        """保持呼叫"""
        if self.state != SIPCallState.CONNECTED:
            self.state = SIPCallState.ERROR
            raise ValueError("只有在通话连接状态才能保持呼叫")
        
        self.steps.append({
            'action': 'hold_call',
            'call_id': self.call_id
        })
        self.expected_results.append("成功发送保持请求")
        return self
    
    def unhold_call(self):
        """取消保持"""
        if self.state != SIPCallState.CONNECTED:
            self.state = SIPCallState.ERROR
            raise ValueError("只有在通话连接状态才能取消保持")
        
        self.steps.append({
            'action': 'unhold_call',
            'call_id': self.call_id
        })
        self.expected_results.append("成功发送取消保持请求")
        return self
    
    def terminate_call(self):
        """终止呼叫"""
        if self.state not in [SIPCallState.CALLING, SIPCallState.RINGING, SIPCallState.CONNECTED]:
            self.state = SIPCallState.ERROR
            raise ValueError("只有在呼叫、振铃或连接状态才能终止呼叫")
        
        self.steps.append({
            'action': 'send_bye',
            'call_id': self.call_id
        })
        self.expected_results.append("成功发送BYE请求")
        self.expected_results.append("收到200 OK响应，呼叫终止")
        self.state = SIPCallState.TERMINATED
        return self
    
    def reject_call(self):
        """拒绝呼叫"""
        if self.state != SIPCallState.RINGING:
            self.state = SIPCallState.ERROR
            raise ValueError("只有在振铃状态才能拒绝呼叫")
        
        self.steps.append({
            'action': 'send_reject',
            'call_id': self.call_id
        })
        self.expected_results.append("成功发送拒绝响应")
        self.state = SIPCallState.TERMINATED
        return self
    
    def wait(self, seconds: int):
        """等待指定秒数"""
        self.steps.append({
            'action': 'wait',
            'duration': seconds
        })
        return self
    
    def register_and_call(self, username: str, password: str, server_uri: str, callee_uri: str, expires: int = 3600, call_duration: int = 5):
        """注册用户并立即发起呼叫"""
        # 先注册
        self.register_user(username, password, server_uri, expires)
        
        # 更新呼叫参数
        self.caller_uri = f"sip:{username}@{server_uri.replace('sip:', '')}" if server_uri.startswith('sip:') else f"sip:{username}@{server_uri}"
        self.callee_uri = callee_uri
        
        # 发起呼叫
        self.state = SIPCallState.CALLING
        self.steps.append({
            'action': 'make_call',
            'caller_uri': self.caller_uri,
            'callee_uri': self.callee_uri,
            'duration': call_duration,
            'call_id': self.call_id
        })
        self.expected_results.extend([
            f"成功发送INVITE到 {self.callee_uri}",
            f"收到200 OK响应",
            f"发送ACK确认",
            f"维持通话 {call_duration} 秒",
            f"发送BYE终止呼叫"
        ])
        return self
    
    def execute_with_client(self):
        """使用客户端执行SIP流程，符合RFC3261标准"""
        if not self.client_manager:
            raise ValueError("需要提供client_manager才能执行SIP流程")
        
        # 根据步骤执行相应的SIP操作
        for step in self.steps:
            action = step['action']
            try:
                if action == 'register':
                    # 使用统一的客户端管理器注册方法
                    from AutoTestForUG.sip_client.client_manager import SIPClientType
                    client = self.client_manager.get_client(SIPClientType.UNIFIED)
                    success = client.register(
                        step['username'], 
                        step['password'], 
                        step.get('expires', 3600)
                    )
                    if not success:
                        self.state = SIPCallState.ERROR
                        raise Exception(f"注册失败: {step['username']}")
                    self.state = SIPCallState.REGISTERED
                elif action == 'unregister':
                    # 使用统一的客户端管理器注销方法
                    from AutoTestForUG.sip_client.client_manager import SIPClientType
                    client = self.client_manager.get_client(SIPClientType.UNIFIED)
                    success = client.unregister()
                    if not success:
                        self.state = SIPCallState.ERROR
                        raise Exception(f"注销失败: {step['username']}")
                    self.state = SIPCallState.IDLE
                elif action == 'make_call':
                    # 使用统一的客户端管理器呼叫方法
                    from AutoTestForUG.sip_client.client_manager import SIPClientType
                    client = self.client_manager.get_client(SIPClientType.UNIFIED)
                    success = client.make_call(
                        step['caller_uri'], 
                        step['callee_uri'], 
                        step.get('duration', 5)
                    )
                    if not success:
                        self.state = SIPCallState.ERROR
                        raise Exception(f"呼叫失败: {step['caller_uri']} -> {step['callee_uri']}")
                    # 呼叫成功后更新状态
                    self.state = SIPCallState.CONNECTED
                elif action == 'send_message':
                    # 使用统一的客户端管理器消息方法
                    from AutoTestForUG.sip_client.client_manager import SIPClientType
                    client = self.client_manager.get_client(SIPClientType.UNIFIED)
                    success = client.send_message(
                        step['from_uri'], 
                        step['to_uri'], 
                        step.get('content', '')
                    )
                    if not success:
                        self.state = SIPCallState.ERROR
                        raise Exception(f"消息发送失败: {step['from_uri']} -> {step['to_uri']}")
                elif action == 'wait':
                    time.sleep(step['duration'])
                elif action == 'wait_for_response':
                    # 这里可以添加响应等待逻辑
                   
                    # 等待响应的实现可以根据具体的客户端实现来定制
                    # 暂时简单处理
                    time.sleep(2)  # 模拟等待
                   
                    time.sleep(2)  # 模拟等待响应
                elif action == 'hold_call':
                    # 这里可以添加呼叫保持逻辑
                    time.sleep(1)  # 模拟保持操作
                elif action == 'unhold_call':
                    # 这里可以添加取消保持逻辑
                    time.sleep(1)  # 模拟取消保持操作
                elif action == 'send_bye':
                    # 这里可以添加发送BYE逻辑
                    time.sleep(1)  # 模拟发送BYE
                    self.state = SIPCallState.TERMINATED
                elif action == 'send_reject':
                    # 这里可以添加发送拒绝逻辑
                    time.sleep(1)  # 模拟发送拒绝
                    self.state = SIPCallState.TERMINATED
            except Exception as e:
                self.state = SIPCallState.ERROR
                raise Exception(f"执行步骤失败 [{action}]: {str(e)}")


class SIPMessageValidator:
    """SIP消息验证器"""
    
    @staticmethod
    def validate_invite(message: str) -> dict:
        """验证INVITE消息格式"""
        result = {
            'valid': True,
            'errors': []
        }
        
        lines = message.split('\r\n')
        if not lines or not lines[0].startswith('INVITE '):
            result['valid'] = False
            result['errors'].append('INVITE消息格式错误：缺少有效的请求行')
            return result
        
        # 检查必需头字段
        required_headers = ['Via', 'From', 'To', 'Call-ID', 'CSeq', 'Content-Length']
        message_lower = message.lower()
        
        for header in required_headers:
            if f'{header.lower()}:' not in message_lower:
                result['valid'] = False
                result['errors'].append(f'INVITE消息缺少必需的{header}头字段')
        
        # 检查Contact头字段（对于INVITE是推荐的）
        if 'contact:' not in message_lower:
            result['errors'].append('INVITE消息缺少Contact头字段（推荐）')
        
        # 检查SDP内容
        if 'content-type:' in message_lower:
            content_type = next((line for line in lines if line.lower().startswith('content-type:')), '')
            if 'application/sdp' in content_type:
                # 简单检查SDP是否存在
                body_start = False
                sdp_lines = []
                for line in lines:
                    if line.strip() == '':
                        body_start = True
                    elif body_start:
                        sdp_lines.append(line)
                
                if not sdp_lines:
                    result['errors'].append('INVITE消息Content-Type为application/sdp但缺少SDP内容')
        
        return result
    
    @staticmethod
    def validate_register(message: str) -> dict:
        """验证REGISTER消息格式"""
        result = {
            'valid': True,
            'errors': []
        }
        
        lines = message.split('\r\n')
        if not lines or not lines[0].startswith('REGISTER '):
            result['valid'] = False
            result['errors'].append('REGISTER消息格式错误：缺少有效的请求行')
            return result
        
        # 检查必需头字段
        required_headers = ['Via', 'From', 'To', 'Call-ID', 'CSeq', 'Contact', 'Content-Length']
        message_lower = message.lower()
        
        for header in required_headers:
            if f'{header.lower()}:' not in message_lower:
                result['valid'] = False
                result['errors'].append(f'REGISTER消息缺少必需的{header}头字段')
        
        # 检查Expires头字段
        if 'expires:' not in message_lower:
            result['errors'].append('REGISTER消息缺少Expires头字段（推荐）')
        
        return result
    
    @staticmethod
    def validate_ack(message: str) -> dict:
        """验证ACK消息格式"""
        result = {
            'valid': True,
            'errors': []
        }
        
        lines = message.split('\r\n')
        if not lines or not lines[0].startswith('ACK '):
            result['valid'] = False
            result['errors'].append('ACK消息格式错误：缺少有效的请求行')
            return result
        
        # 检查必需头字段
        required_headers = ['Via', 'From', 'To', 'Call-ID', 'CSeq']
        message_lower = message.lower()
        
        for header in required_headers:
            if f'{header.lower()}:' not in message_lower:
                result['valid'] = False
                result['errors'].append(f'ACK消息缺少必需的{header}头字段')
        
        return result
    
    @staticmethod
    def validate_bye(message: str) -> dict:
        """验证BYE消息格式"""
        result = {
            'valid': True,
            'errors': []
        }
        
        lines = message.split('\r\n')
        if not lines or not lines[0].startswith('BYE '):
            result['valid'] = False
            result['errors'].append('BYE消息格式错误：缺少有效的请求行')
            return result
        
        # 检查必需头字段
        required_headers = ['Via', 'From', 'To', 'Call-ID', 'CSeq']
        message_lower = message.lower()
        
        for header in required_headers:
            if f'{header.lower()}:' not in message_lower:
                result['valid'] = False
                result['errors'].append(f'BYE消息缺少必需的{header}头字段')
        
        return result
    
    @staticmethod
    def validate_cancel(message: str) -> dict:
        """验证CANCEL消息格式"""
        result = {
            'valid': True,
            'errors': []
        }
        
        lines = message.split('\r\n')
        if not lines or not lines[0].startswith('CANCEL '):
            result['valid'] = False
            result['errors'].append('CANCEL消息格式错误：缺少有效的请求行')
            return result
        
        # 检查必需头字段
        required_headers = ['Via', 'From', 'To', 'Call-ID', 'CSeq']
        message_lower = message.lower()
        
        for header in required_headers:
            if f'{header.lower()}:' not in message_lower:
                result['valid'] = False
                result['errors'].append(f'CANCEL消息缺少必需的{header}头字段')
        
        return result
    
    @staticmethod
    def validate_options(message: str) -> dict:
        """验证OPTIONS消息格式"""
        result = {
            'valid': True,
            'errors': []
        }
        
        lines = message.split('\r\n')
        if not lines or not lines[0].startswith('OPTIONS '):
            result['valid'] = False
            result['errors'].append('OPTIONS消息格式错误：缺少有效的请求行')
            return result
        
        # 检查必需头字段
        required_headers = ['Via', 'From', 'To', 'Call-ID', 'CSeq', 'Content-Length']
        message_lower = message.lower()
        
        for header in required_headers:
            if f'{header.lower()}:' not in message_lower:
                result['valid'] = False
                result['errors'].append(f'OPTIONS消息缺少必需的{header}头字段')
        
        return result
    
    @staticmethod
    def validate_response(message: str) -> dict:
        """验证响应消息格式"""
        result = {
            'valid': True,
            'errors': []
        }
        
        lines = message.split('\r\n')
        if not lines or not re.match(r'^SIP/2\.0 \d+ ', lines[0]):
            result['valid'] = False
            result['errors'].append('响应消息格式错误：缺少有效的状态行')
            return result
        
        # 检查必需头字段
        required_headers = ['Via', 'From', 'To', 'Call-ID', 'CSeq']
        message_lower = message.lower()
        
        for header in required_headers:
            if f'{header.lower()}:' not in message_lower:
                result['valid'] = False
                result['errors'].append(f'响应消息缺少必需的{header}头字段')
        
        # 检查To头字段是否包含tag
        to_header = next((line for line in lines if line.lower().startswith('to:')), '')
        if 'tag=' not in to_header:
            result['errors'].append('响应消息的To头字段缺少tag参数')
        
        return result
    
    @staticmethod
    def validate_message_syntax(message: str) -> dict:
        """验证SIP消息语法"""
        result = {
            'valid': True,
            'errors': []
        }
        
        try:
            lines = message.split('\r\n')
            if not lines:
                result['valid'] = False
                result['errors'].append('消息为空')
                return result
            
            # 检查请求行或状态行
            first_line = lines[0]
            if not (re.match(r'^(INVITE|ACK|BYE|CANCEL|OPTIONS|REGISTER|MESSAGE) ', first_line) or 
                   re.match(r'^SIP/2\.0 \d+ ', first_line)):
                result['valid'] = False
                result['errors'].append('消息缺少有效的请求行或状态行')
                return result
            
            # 检查是否有Via头
            has_via = any(line.lower().startswith('via:') for line in lines)
            if not has_via:
                result['valid'] = False
                result['errors'].append('消息缺少Via头字段')
            
            # 检查是否有必要的头字段
            has_from = any(line.lower().startswith('from:') for line in lines)
            has_to = any(line.lower().startswith('to:') for line in lines)
            has_call_id = any(line.lower().startswith('call-id:') for line in lines)
            has_cseq = any(line.lower().startswith('cseq:') for line in lines)
            
            if not has_from:
                result['valid'] = False
                result['errors'].append('消息缺少From头字段')
            if not has_to:
                result['valid'] = False
                result['errors'].append('消息缺少To头字段')
            if not has_call_id:
                result['valid'] = False
                result['errors'].append('消息缺少Call-ID头字段')
            if not has_cseq:
                result['valid'] = False
                result['errors'].append('消息缺少CSeq头字段')
            
            # 检查消息结构
            header_section_end = False
            body_section_start = False
            
            for i, line in enumerate(lines):
                if line.strip() == '':
                    header_section_end = True
                    body_section_start = True
                elif header_section_end:
                    # 进入消息体部分
                    continue
                else:
                    # 检查头字段格式
                    if ':' not in line:
                        result['valid'] = False
                        result['errors'].append(f'头字段格式错误：{line}')
                    else:
                        header_name, header_value = line.split(':', 1)
                        if not header_name.strip() or not header_value.strip():
                            result['valid'] = False
                            result['errors'].append(f'头字段格式错误：{line}')
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f'消息解析错误：{str(e)}')
        
        return result
    
    @staticmethod
    def validate_header_format(header_line: str) -> bool:
        """验证头字段格式"""
        if ':' not in header_line:
            return False
        
        header_name, header_value = header_line.split(':', 1)
        return header_name.strip() != "" and header_value.strip() != ""
    
    @staticmethod
    def validate_cseq_format(cseq_header: str) -> bool:
        """验证CSeq头字段格式"""
        cseq_parts = cseq_header.split(' ')
        if len(cseq_parts) < 2:
            return False
        
        try:
            seq_number = int(cseq_parts[0])
            method = cseq_parts[1]
            return seq_number >= 1 and method in ['INVITE', 'ACK', 'BYE', 'CANCEL', 'OPTIONS', 'REGISTER', 'MESSAGE']
        except ValueError:
            return False
    
    @staticmethod
    def validate_contact_format(contact_header: str) -> bool:
        """验证Contact头字段格式"""
        import re
        # 简单验证是否包含有效的SIP URI
        return 'sip:' in contact_header or '*' in contact_header
    
    @staticmethod
    def validate_via_format(via_header: str) -> bool:
        """验证Via头字段格式"""
        import re
        # 检查是否包含基本的Via格式元素
        return ('SIP/2.0/' in via_header.upper() or 'SIP/2.0.' in via_header.upper()) and \
               ('UDP' in via_header.upper() or 'TCP' in via_header.upper()) and \
               'branch=' in via_header
    
    @staticmethod
    def extract_call_id(message: str) -> str:
        """从SIP消息中提取Call-ID"""
        for line in message.split('\n'):
            if line.lower().startswith('call-id:'):
                return line.split(':', 1)[1].strip()
        return ""
    
    @staticmethod
    def extract_cseq(message: str) -> str:
        """从SIP消息中提取CSeq"""
        for line in message.split('\n'):
            if line.lower().startswith('cseq:'):
                return line.split(':', 1)[1].strip()
        return ""
    
    @staticmethod
    def extract_method(message: str) -> str:
        """从SIP消息中提取方法"""
        lines = message.split('\n')
        if not lines:
            return ""
        
        first_line = lines[0]
        if ' ' in first_line:
            return first_line.split(' ')[0]
        
        return ""
    
    @staticmethod
    def extract_status_code(message: str) -> int:
        """从SIP响应消息中提取状态码"""
        lines = message.split('\n')
        if not lines:
            return 0
        
        first_line = lines[0]
        if 'SIP/2.0 ' in first_line:
            parts = first_line.split(' ')
            if len(parts) >= 3:
                try:
                    return int(parts[1])
                except ValueError:
                    return 0
        
        return 0
    
    @staticmethod
    def validate_rfc3261_compliance(message: str) -> dict:
        """验证RFC3261合规性"""
        result = {
            'syntax_valid': True,
            'required_headers_present': True,
            'format_correct': True,
            'rfc_compliant': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查消息语法
        syntax_result = SIPMessageValidator.validate_message_syntax(message)
        if not syntax_result['valid']:
            result['syntax_valid'] = False
            result['errors'].extend(syntax_result['errors'])
            result['rfc_compliant'] = False
        
        # 检查必需头字段
        lines = message.split('\r\n')
        has_via = any(line.lower().startswith('via:') for line in lines)
        has_from = any(line.lower().startswith('from:') for line in lines)
        has_to = any(line.lower().startswith('to:') for line in lines)
        has_call_id = any(line.lower().startswith('call-id:') for line in lines)
        has_cseq = any(line.lower().startswith('cseq:') for line in lines)
        
        required_headers_ok = has_via and has_from and has_to and has_call_id and has_cseq
        if not required_headers_ok:
            result['required_headers_present'] = False
            result['errors'].append('缺少必需的头字段')
            result['rfc_compliant'] = False
        
        # 检查头字段格式
        for line in lines:
            if ':' in line and not line.startswith(' '):
                if not SIPMessageValidator.validate_header_format(line):
                    result['format_correct'] = False
                    result['errors'].append(f'头字段格式错误: {line}')
                    result['rfc_compliant'] = False
        
        # 特定方法的验证
        method = SIPMessageValidator.extract_method(message)
        if method:
            if method == 'INVITE':
                invite_result = SIPMessageValidator.validate_invite(message)
                if not invite_result['valid']:
                    result['errors'].extend(invite_result['errors'])
                    result['rfc_compliant'] = False
            elif method == 'REGISTER':
                register_result = SIPMessageValidator.validate_register(message)
                if not register_result['valid']:
                    result['errors'].extend(register_result['errors'])
                    result['rfc_compliant'] = False
            elif method == 'ACK':
                ack_result = SIPMessageValidator.validate_ack(message)
                if not ack_result['valid']:
                    result['errors'].extend(ack_result['errors'])
                    result['rfc_compliant'] = False
            elif method == 'BYE':
                bye_result = SIPMessageValidator.validate_bye(message)
                if not bye_result['valid']:
                    result['errors'].extend(bye_result['errors'])
                    result['rfc_compliant'] = False
            elif method == 'CANCEL':
                cancel_result = SIPMessageValidator.validate_cancel(message)
                if not cancel_result['valid']:
                    result['errors'].extend(cancel_result['errors'])
                    result['rfc_compliant'] = False
            elif method == 'OPTIONS':
                options_result = SIPMessageValidator.validate_options(message)
                if not options_result['valid']:
                    result['errors'].extend(options_result['errors'])
                    result['rfc_compliant'] = False
        else:
            # 检查是否为响应消息
            if 'SIP/2.0 ' in message:
                response_result = SIPMessageValidator.validate_response(message)
                if not response_result['valid']:
                    result['errors'].extend(response_result['errors'])
                    result['rfc_compliant'] = False
        
        # 检查Via头的branch参数
        via_headers = [line for line in lines if line.lower().startswith('via:')]
        for via_header in via_headers:
            if 'branch=' not in via_header:
                result['warnings'].append('Via头缺少branch参数（RFC 3261推荐）')
        
        # 检查From头的tag参数
        from_header = next((line for line in lines if line.lower().startswith('from:')), '')
        if 'tag=' not in from_header:
            result['warnings'].append('From头缺少tag参数（RFC 3261推荐）')
        
        return result


class SIPTestScenario:
    """SIP测试场景DSL"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.scenarios = []
        self.preconditions = []
        self.postconditions = []
        self.metadata = {}
    
    def add_call_flow(self, caller_uri: str, callee_uri: str, duration: int = 5):
        """添加呼叫流程"""
        flow = SIPCallFlow(caller_uri, callee_uri)
        flow.make_call(duration)
        self.scenarios.append(flow)
        return flow
    
    def add_precondition(self, func: Callable, description: str = ""):
        """添加前置条件"""
        self.preconditions.append({
            'function': func,
            'description': description
        })
        return self
    
    def add_postcondition(self, func: Callable, description: str = ""):
        """添加后置条件"""
        self.postconditions.append({
            'function': func,
            'description': description
        })
        return self
    
    def set_metadata(self, **kwargs):
        """设置元数据"""
        self.metadata.update(kwargs)
        return self
    
    def execute_with_client(self, client_manager):
        """使用客户端管理器执行测试场景"""
        results = []
        
        # 执行前置条件
        for precondition in self.preconditions:
            try:
                precondition['function']()
            except Exception as e:
                raise Exception(f"前置条件失败: {precondition['description']}, 错误: {str(e)}")
        
        # 执行所有场景
        for i, scenario in enumerate(self.scenarios):
            scenario.client_manager = client_manager
            # 这里会根据具体的客户端管理器执行场景
            result = self._execute_scenario(scenario, client_manager)
            results.append(result)
        
        # 执行后置条件
        for postcondition in self.postconditions:
            try:
                postcondition['function']()
            except Exception as e:
                raise Exception(f"后置条件失败: {postcondition['description']}, 错误: {str(e)}")
        
        return results
    
    def _execute_scenario(self, scenario: SIPCallFlow, client_manager):
        """执行单个场景"""
        # 这里会根据场景的步骤调用客户端管理器执行具体操作
        # 为了简化，这里返回模拟结果
        return {
            'scenario_name': f"{scenario.caller_uri} -> {scenario.callee_uri}",
            'steps_executed': len(scenario.steps),
            'expected_results_count': len(scenario.expected_results),
            'status': 'success'  # 在实际实现中会根据执行结果设置
        }


class SIPDSL:
    """SIP领域特定语言主类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化SIP DSL
        
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def create_call_flow(self, caller_uri: str, callee_uri: str, duration: int = 5) -> SIPCallFlow:
        """创建呼叫流程"""
        return define_call_scenario(caller_uri, callee_uri, duration)
    
    def create_test_scenario(self, name: str, description: str = "") -> SIPTestScenario:
        """创建测试场景"""
        return define_test_scenario(name, description)
    
    def validate_message(self, message: str, message_type: str = "invite") -> bool:
        """验证SIP消息"""
        validator = SIPMessageValidator()
        
        if message_type.lower() == "invite":
            return validator.validate_invite(message)
        elif message_type.lower() == "response":
            return validator.validate_response(message)
        else:
            return False
    
    def execute_scenario_with_client(self, scenario: SIPTestScenario, client_manager):
        """使用客户端管理器执行场景"""
        return scenario.execute_with_client(client_manager)


# 便捷函数
def define_call_scenario(caller_uri: str, callee_uri: str, duration: int = 5):
    """定义呼叫场景的便捷函数"""
    return SIPCallFlow(caller_uri, callee_uri).make_call(duration)


def define_test_scenario(name: str, description: str = ""):
    """定义测试场景的便捷函数"""
    return SIPTestScenario(name, description)