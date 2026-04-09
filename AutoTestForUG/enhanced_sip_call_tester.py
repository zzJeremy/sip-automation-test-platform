"""
增强版SIP基础通话测试客户端
严格按照RFC3261标准实现SIP呼叫功能
支持完整的呼叫流程：INVITE -> 180/200 OK -> ACK -> BYE
包含PRACK、UPDATE、INFO等扩展方法
"""

import socket
import time
import logging
import random
import re
from enum import Enum
from typing import Dict, Any, Optional

try:
    from .error_handler import error_handler, retry_on_failure, SIPTestLogger, validate_sip_uri
    from .rfc3261_enhancements import RFC3261Enhancements, get_timer_value
    from .nat_traversal import STUNClient, create_nat_compatible_sip_message, enable_nat_traversal
except ImportError:
    from error_handler import error_handler, retry_on_failure, SIPTestLogger, validate_sip_uri
    from rfc3261_enhancements import RFC3261Enhancements, get_timer_value
    from nat_traversal import STUNClient, create_nat_compatible_sip_message, enable_nat_traversal


class SIPClientState(Enum):
    """SIP客户端状态枚举"""
    UNREGISTERED = "unregistered"
    REGISTERING = "registering"
    REGISTERED = "registered"
    UNREGISTERING = "unregistering"
    IDLE = "idle"
    CALLING = "calling"
    RINGING = "ringing"
    IN_CALL = "in_call"
    HANGING_UP = "hanging_up"
    ERROR = "error"
    UNKNOWN = "unknown"


class EnhancedSIPCallTester:
    """
    增强版SIP通话测试器
    严格按照RFC3261标准实现SIP呼叫流程，增加扩展功能
    """
    
    def __init__(self, server_host: str = "127.0.0.1", server_port: int = 5060, 
                 local_host: str = "127.0.0.1", local_port: int = 5080):
        """
        初始化基础SIP通话测试器
        
        Args:
            server_host: SIP服务器地址
            server_port: SIP服务器端口
            local_host: 本地地址
            local_port: 本地端口
        """
        self.server_host = server_host
        self.server_port = server_port
        self.local_host = local_host
        self.local_port = local_port
        
        # RFC3261要求的必要头字段存储
        self._supported_methods = ["INVITE", "ACK", "CANCEL", "BYE", "OPTIONS", "PRACK", "UPDATE", "INFO", "REFER", "NOTIFY", "SUBSCRIBE", "MESSAGE"]
        self._supported_options = ["100rel", "precondition", "timer", "eventlist", "refer-events", "replaces"]
        
        # 设置日志
        self.logger = SIPTestLogger("EnhancedSIPCallTester", "enhanced_sip_call_tester.log")
        
        # 初始化客户端状态
        self._state = SIPClientState.UNREGISTERED
        self.current_call_id = None
        self.is_registered = False
        self.registration_expires = 0
        self.current_call_info = {}
        self.dialog_info = {}  # 存储对话信息
        
    def generate_branch(self) -> str:
        """
        生成符合RFC3261的branch ID
        必须以"z9hG4bK"开头以标识这是一个RFC3261兼容的分支
        """
        return f"z9hG4bK{int(time.time() * 1000000)}{random.randint(1000, 9999)}"
    
    def generate_call_id(self) -> str:
        """生成唯一的Call-ID，符合RFC3261规范"""
        return f"{int(time.time())}.{random.randint(10000, 99999)}@{self.local_host}"
    
    def generate_tag(self) -> str:
        """生成唯一的tag，用于From/To头字段"""
        return f"tag{int(time.time() * 1000)}"
    
    def validate_uri(self, uri: str) -> bool:
        """验证SIP URI格式，符合RFC3261规范"""
        return validate_sip_uri(uri)
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析SIP响应消息，符合RFC3261规范
        """
        lines = response.split('\r\n')
        if not lines:
            return {}
        
        # 解析状态行
        status_line = lines[0]
        parts = status_line.split(' ', 2)
        if len(parts) >= 3:
            protocol, status_code, reason_phrase = parts
        else:
            return {}
        
        parsed_response = {
            'protocol': protocol,
            'status_code': int(status_code),
            'reason_phrase': reason_phrase,
            'headers': {},
            'body': ''
        }
        
        # 解析头字段
        body_started = False
        body_lines = []
        for line in lines[1:]:
            if line.strip() == '':
                body_started = True
                continue
            
            if not body_started:
                if line.startswith(' ') or line.startswith('\t'):
                    # 连续行，附加到上一个头字段
                    if parsed_response['headers']:
                        last_header = list(parsed_response['headers'].keys())[-1]
                        parsed_response['headers'][last_header] += ' ' + line.strip()
                else:
                    # 新的头字段
                    if ':' in line:
                        header_name, header_value = line.split(':', 1)
                        parsed_response['headers'][header_name.strip()] = header_value.strip()
            else:
                body_lines.append(line)
        
        parsed_response['body'] = '\r\n'.join(body_lines)
        return parsed_response
    
    def create_invite_message(self, caller_uri: str, callee_uri: str, call_id: str) -> str:
        """
        创建符合RFC3261标准的INVITE请求消息
        包含所有必需的头字段
        """
        branch = self.generate_branch()
        from_tag = self.generate_tag()
        
        # 简化的SDP内容，符合RFC4566标准
        sdp_content = (
            "v=0\r\n"
            "o=- {timestamp} {version} IN IP4 {local_host}\r\n"
            "s=SIP Call\r\n"
            "c=IN IP4 {local_host}\r\n"
            "t=0 0\r\n"
            "m=audio {rtp_port} RTP/AVP 0 8 101\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
            "a=rtpmap:8 PCMA/8000\r\n"
            "a=rtpmap:101 telephone-event/8000\r\n"
            "a=fmtp:101 0-15\r\n"
            "a=sendrecv\r\n"
        ).format(
            timestamp=int(time.time()),
            version=int(time.time()),  # SDP版本号
            local_host=self.local_host, 
            rtp_port=self.local_port+1000  # 使用不同端口用于RTP
        )
        
        # 构建INVITE消息，包含RFC3261必需的头字段
        message = (
            f"INVITE {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {caller_uri};tag={from_tag}\r\n"
            f"To: {callee_uri}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Contact: <sip:{self.local_host}:{self.local_port}>\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp_content)}\r\n"
            f"Allow: {', '.join(self._supported_methods)}\r\n"
            f"Supported: {', '.join(self._supported_options)}\r\n"
            f"User-Agent: EnhancedSIPCallTester RFC3261 Compliant\r\n"
            f"\r\n"
            f"{sdp_content}"
        )
        return message
    
    def create_ack_message(self, caller_uri: str, callee_uri: str, call_id: str, cseq: int = 1, to_tag: str = "") -> str:
        """
        创建符合RFC3261标准的ACK消息
        """
        branch = self.generate_branch()
        from_tag = caller_uri.split('tag=')[1] if 'tag=' in caller_uri else self.generate_tag()
        
        message = (
            f"ACK {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {caller_uri};tag={from_tag}\r\n"
            f"To: {callee_uri}{f';tag={to_tag}' if to_tag else ''}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} ACK\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return message
    
    def create_bye_message(self, caller_uri: str, callee_uri: str, call_id: str, cseq: int = 2, from_tag: str = "", to_tag: str = "") -> str:
        """
        创建符合RFC3261标准的BYE消息
        """
        branch = self.generate_branch()
        
        message = (
            f"BYE {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {caller_uri}{f';tag={from_tag}' if from_tag else ''}\r\n"
            f"To: {callee_uri}{f';tag={to_tag}' if to_tag else ''}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} BYE\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return message
    
    def create_cancel_message(self, caller_uri: str, callee_uri: str, call_id: str, cseq: int) -> str:
        """
        创建符合RFC3261标准的CANCEL消息
        用于取消未完成的请求（如长时间未响应的INVITE）
        """
        branch = self.generate_branch()
        from_tag = caller_uri.split('tag=')[1] if 'tag=' in caller_uri else self.generate_tag()
        
        message = (
            f"CANCEL {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {caller_uri};tag={from_tag}\r\n"
            f"To: {callee_uri}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} CANCEL\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return message

    def create_register_message(self, username: str, domain: str, password: str = "", expires: int = 3600, 
                               nonce: str = "", realm: str = "", cseq: int = 1) -> str:
        """
        创建符合RFC3261标准的REGISTER请求消息
        包含认证信息处理
        """
        branch = self.generate_branch()
        call_id = self.generate_call_id()
        contact_uri = f"sip:{self.local_host}:{self.local_port}"
        
        # 如果提供了认证信息，则构建认证头部
        auth_header = ""
        if nonce and realm and password:
            # 计算认证信息 - RFC 2617标准
            import hashlib
            
            # HA1 = MD5(username:realm:password)
            ha1_input = f"{username}:{realm}:{password}"
            ha1 = hashlib.md5(ha1_input.encode()).hexdigest()
            
            # HA2 = MD5(method:digestURI) 
            ha2_input = f"REGISTER:sip:{domain}"
            ha2 = hashlib.md5(ha2_input.encode()).hexdigest()
            
            # response = MD5(HA1:nonce:HA2)
            response_input = f"{ha1}:{nonce}:{ha2}"
            response = hashlib.md5(response_input.encode()).hexdigest()
            
            auth_header = (
                f'Authorization: Digest username="{username}", '
                f'realm="{realm}", nonce="{nonce}", uri="sip:{domain}", '
                f'response="{response}", algorithm=MD5\r\n'
            )
        
        message = (
            f"REGISTER sip:{domain} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: <sip:{username}@{domain}>;tag={self.generate_tag()}\r\n"
            f"To: <sip:{username}@{domain}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} REGISTER\r\n"
            f"Contact: <{contact_uri}>;expires={expires}\r\n"
            f"Expires: {expires}\r\n"
            f"Content-Length: 0\r\n"
        )
        
        if auth_header:
            message = message.replace("Content-Length: 0\r\n", f"{auth_header}Content-Length: 0\r\n")
        
        message += "\r\n"
        return message

    def create_prack_message(self, rseq: int, method: str, req_uri: str, call_id: str, 
                           cseq: int, from_uri: str, to_uri: str, from_tag: str, 
                           to_tag: str) -> str:
        """
        创建符合RFC3261标准的PRACK消息
        用于确认可靠的临时响应
        """
        return RFC3261Enhancements.create_prack_message(
            self.local_host, self.local_port, req_uri, call_id, 
            cseq, from_uri, to_uri, from_tag, to_tag, rseq, method
        )

    def create_update_message(self, req_uri: str, call_id: str, cseq: int, 
                            from_uri: str, to_uri: str, from_tag: str, 
                            to_tag: str, contact: str = None, sdp_content: str = None) -> str:
        """
        创建符合RFC3261标准的UPDATE消息
        用于在对话外更新会话参数
        """
        return RFC3261Enhancements.create_update_message(
            self.local_host, self.local_port, req_uri, call_id, 
            cseq, from_uri, to_uri, from_tag, to_tag, contact, sdp_content
        )

    def create_info_message(self, req_uri: str, call_id: str, cseq: int, 
                          from_uri: str, to_uri: str, from_tag: str, 
                          to_tag: str, content: str = "", 
                          content_type: str = "application/dtmf-relay") -> str:
        """
        创建符合RFC3261标准的INFO消息
        用于传输会话期间的额外信息
        """
        return RFC3261Enhancements.create_info_message(
            self.local_host, self.local_port, req_uri, call_id, 
            cseq, from_uri, to_uri, from_tag, to_tag, content, content_type
        )

    def create_refer_message(self, referred_by: str, refer_to: str, call_id: str, 
                           cseq: int, from_uri: str, to_uri: str, from_tag: str, 
                           to_tag: str, expires: int = 3600) -> str:
        """
        创建符合RFC3261和RFC3515标准的REFER消息
        用于引用第三方参与对话
        
        Args:
            referred_by: 引用发起者
            refer_to: 引用目标
            call_id: Call-ID
            cseq: CSeq序列号
            from_uri: From URI
            to_uri: To URI
            from_tag: From标签
            to_tag: To标签
            expires: 过期时间
            
        Returns:
            str: REFER消息字符串
        """
        branch = self.generate_branch()
        
        message = (
            f"REFER {to_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {from_uri};tag={from_tag}\r\n"
            f"To: {to_uri};tag={to_tag}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} REFER\r\n"
            f"Referred-By: {referred_by}\r\n"
            f"Refer-To: {refer_to}\r\n"
            f"Event: refer\r\n"
            f"Subscription-State: terminated;reason=noresource\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return message

    def create_subscribe_message(self, event: str, call_id: str, 
                               cseq: int, from_uri: str, to_uri: str, from_tag: str, 
                               to_tag: str, expires: int = 3600) -> str:
        """
        创建符合RFC3261和RFC3265标准的SUBSCRIBE消息
        用于订阅事件包
        
        Args:
            event: 事件包名称
            call_id: Call-ID
            cseq: CSeq序列号
            from_uri: From URI
            to_uri: To URI
            from_tag: From标签
            to_tag: To标签
            expires: 过期时间
            
        Returns:
            str: SUBSCRIBE消息字符串
        """
        branch = self.generate_branch()
        
        message = (
            f"SUBSCRIBE {to_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {from_uri};tag={from_tag}\r\n"
            f"To: {to_uri};tag={to_tag}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} SUBSCRIBE\r\n"
            f"Event: {event}\r\n"
            f"Expires: {expires}\r\n"
            f"Contact: <sip:{self.local_host}:{self.local_port}>\r\n"
            f"Accept: application/pidf+xml, application/xpidf+xml, application/simple-message-summary\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return message

    def create_notify_message(self, subscription_state: str, event: str, call_id: str, 
                            cseq: int, from_uri: str, to_uri: str, from_tag: str, 
                            to_tag: str, content: str = "", content_type: str = "") -> str:
        """
        创建符合RFC3261和RFC3265标准的NOTIFY消息
        用于通知订阅者事件状态变化
        
        Args:
            subscription_state: 订阅状态
            event: 事件包名称
            call_id: Call-ID
            cseq: CSeq序列号
            from_uri: From URI
            to_uri: To URI
            from_tag: From标签
            to_tag: To标签
            content: 消息内容
            content_type: 内容类型
            
        Returns:
            str: NOTIFY消息字符串
        """
        branch = self.generate_branch()
        
        content_length = len(content)
        message = (
            f"NOTIFY {to_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {from_uri};tag={from_tag}\r\n"
            f"To: {to_uri};tag={to_tag}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} NOTIFY\r\n"
            f"Event: {event}\r\n"
            f"Subscription-State: {subscription_state}\r\n"
            f"Content-Length: {content_length}\r\n"
        )
        
        if content_type:
            message += f"Content-Type: {content_type}\r\n"
        
        message += "\r\n"
        
        if content:
            message += content
        
        return message

    def create_message_message(self, call_id: str, cseq: int, from_uri: str, to_uri: str, 
                             from_tag: str, to_tag: str, content: str, 
                             content_type: str = "text/plain") -> str:
        """
        创建符合RFC3428标准的MESSAGE消息
        用于发送即时消息
        
        Args:
            call_id: Call-ID
            cseq: CSeq序列号
            from_uri: From URI
            to_uri: To URI
            from_tag: From标签
            to_tag: To标签
            content: 消息内容
            content_type: 内容类型
            
        Returns:
            str: MESSAGE消息字符串
        """
        branch = self.generate_branch()
        
        message = (
            f"MESSAGE {to_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_host}:{self.local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {from_uri};tag={from_tag}\r\n"
            f"To: {to_uri};tag={to_tag}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} MESSAGE\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(content)}\r\n"
            f"\r\n"
            f"{content}"
        )
        return message

    def extract_auth_info(self, response: str) -> tuple:
        """
        从401/407响应中提取认证信息
        返回 (realm, nonce)
        """
        realm = ""
        nonce = ""
        
        for line in response.split('\r\n'):
            line_lower = line.lower().strip()
            if 'www-authenticate:' in line_lower and 'digest' in line_lower:
                # 提取realm
                import re
                realm_match = re.search(r'realm="([^"]*)"', line, re.IGNORECASE)
                if realm_match:
                    realm = realm_match.group(1)
                
                # 提取nonce
                nonce_match = re.search(r'nonce="([^"]*)"', line, re.IGNORECASE)
                if nonce_match:
                    nonce = nonce_match.group(1)
                
                break
            elif 'proxy-authenticate:' in line_lower and 'digest' in line_lower:
                # 提取realm
                import re
                realm_match = re.search(r'realm="([^"]*)"', line, re.IGNORECASE)
                if realm_match:
                    realm = realm_match.group(1)
                
                # 提取nonce
                nonce_match = re.search(r'nonce="([^"]*)"', line, re.IGNORECASE)
                if nonce_match:
                    nonce = nonce_match.group(1)
                
                break
        
        return realm, nonce

    # 状态管理方法
    def get_state(self) -> SIPClientState:
        """获取当前客户端状态"""
        return self._state

    def set_state(self, new_state: SIPClientState, context: str = ""):
        """设置客户端状态"""
        old_state = self._state
        self._state = new_state
        self.logger.log_state_change(old_state.value, new_state.value, context)

    def is_in_call(self) -> bool:
        """检查客户端是否正在通话中"""
        return self._state == SIPClientState.IN_CALL

    def is_registered(self) -> bool:
        """检查客户端是否已注册"""
        return self._state == SIPClientState.REGISTERED

    def reset_state(self):
        """重置客户端状态到初始状态"""
        self.current_call_id = None
        self.current_call_info = {}
        self.dialog_info = {}
        self.set_state(SIPClientState.UNREGISTERED, "重置客户端状态")
    
    @error_handler
    @retry_on_failure(max_retries=3, delay=2.0)
    def register_user(self, username: str, domain: str, password: str = "", expires: int = 3600) -> bool:
        """
        执行SIP用户注册
        
        Args:
            username: 用户名
            domain: 域名 (例如 "example.com")
            password: 密码（可选，如果服务器不需要认证则可以为空）
            expires: 注册有效期（秒）
            
        Returns:
            bool: 注册是否成功
        """
        self.set_state(SIPClientState.REGISTERING, f"开始注册用户 {username}@{domain}")
        self.logger.log_test_start(f"用户注册 {username}@{domain}", {"expires": expires})
        
        start_time = time.time()
        
        try:
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)  # 10秒超时
            
            # 初始注册请求（不带认证信息）
            register_message = self.create_register_message(username, domain, "", expires, "", "", 1)
            self.logger.logger.debug(f"发送初始REGISTER消息: {register_message[:200]}...")
            
            sock.sendto(register_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                self.logger.logger.debug(f"收到初始响应: {response_str[:200]}...")
                
                # 解析响应
                parsed_response = self.parse_response(response_str)
                status_code = parsed_response.get('status_code', 0)
                
                # 如果收到401/407认证挑战，则重新发送带认证信息的请求
                if status_code in [401, 407]:
                    self.logger.logger.info(f"收到认证挑战 {status_code}，提取认证信息")
                    
                    # 提取认证信息
                    realm, nonce = self.extract_auth_info(response_str)
                    
                    if not realm or not nonce:
                        error_msg = f"无法从响应中提取认证信息: {response_str[:100]}"
                        self.logger.log_test_failure(f"用户注册 {username}@{domain}", Exception(error_msg))
                        self.set_state(SIPClientState.ERROR, f"无法提取认证信息: {error_msg}")
                        sock.close()
                        return False
                    
                    # 使用认证信息重新发送REGISTER请求
                    self.logger.logger.info(f"使用认证信息重新发送REGISTER请求，realm: {realm}")
                    authenticated_register_message = self.create_register_message(
                        username, domain, password, expires, nonce, realm, 2
                    )
                    
                    sock.sendto(authenticated_register_message.encode('utf-8'), (self.server_host, self.server_port))
                    
                    # 接收认证后的响应
                    try:
                        response_data, server_addr = sock.recvfrom(4096)
                        response_str = response_data.decode('utf-8')
                        self.logger.logger.debug(f"收到认证后响应: {response_str[:200]}...")
                        
                        # 解析最终响应
                        parsed_response = self.parse_response(response_str)
                        status_code = parsed_response.get('status_code', 0)
                        
                        if status_code == 200:
                            self.logger.logger.info(f"用户 {username} 注册成功")
                            self.set_state(SIPClientState.REGISTERED, f"用户 {username} 注册成功")
                            self.is_registered = True
                            self.registration_expires = time.time() + expires
                            sock.close()
                            total_time = time.time() - start_time
                            self.logger.log_test_success(f"用户注册 {username}@{domain}", total_time)
                            return True
                        else:
                            error_msg = f"注册失败，收到状态码: {status_code} {parsed_response.get('reason_phrase', '')}"
                            self.logger.log_test_failure(f"用户注册 {username}@{domain}", Exception(error_msg))
                            self.set_state(SIPClientState.ERROR, f"注册失败: {error_msg}")
                            sock.close()
                            return False
                            
                    except socket.timeout:
                        error_msg = "等待认证后响应超时"
                        self.logger.log_test_failure(f"用户注册 {username}@{domain}", Exception(error_msg))
                        self.set_state(SIPClientState.ERROR, f"等待认证后响应超时")
                        sock.close()
                        return False
                
                # 如果初始响应就是200 OK，则表示不需要认证
                elif status_code == 200:
                    self.logger.logger.info(f"用户 {username} 无需认证直接注册成功")
                    self.set_state(SIPClientState.REGISTERED, f"用户 {username} 无需认证直接注册成功")
                    self.is_registered = True
                    self.registration_expires = time.time() + expires
                    sock.close()
                    total_time = time.time() - start_time
                    self.logger.log_test_success(f"用户注册 {username}@{domain}", total_time)
                    return True
                
                else:
                    error_msg = f"注册失败，收到状态码: {status_code} {parsed_response.get('reason_phrase', '')}"
                    self.logger.log_test_failure(f"用户注册 {username}@{domain}", Exception(error_msg))
                    self.set_state(SIPClientState.ERROR, f"注册失败: {error_msg}")
                    sock.close()
                    return False
                    
            except socket.timeout:
                error_msg = "等待注册响应超时"
                self.logger.log_test_failure(f"用户注册 {username}@{domain}", Exception(error_msg))
                self.set_state(SIPClientState.ERROR, f"等待注册响应超时")
                sock.close()
                return False
                
        except Exception as e:
            error_msg = f"用户注册执行失败: {str(e)}"
            self.logger.log_test_failure(f"用户注册 {username}@{domain}", e)
            self.set_state(SIPClientState.ERROR, f"注册执行异常: {str(e)}")
            return False

    @error_handler
    @retry_on_failure(max_retries=3, delay=2.0)
    def make_basic_call(self, caller_uri: str, callee_uri: str, duration: int = 5) -> bool:
        """
        执行基础SIP呼叫
        
        Args:
            caller_uri: 主叫URI
            callee_uri: 被叫URI
            duration: 通话时长（秒）
            
        Returns:
            bool: 呼叫是否成功
        """
        self.set_state(SIPClientState.CALLING, f"开始呼叫 {caller_uri} -> {callee_uri}")
        call_id = self.generate_call_id()
        self.current_call_id = call_id
        self.logger.log_test_start(f"呼叫 {caller_uri} -> {callee_uri}", {"duration": duration, "call_id": call_id})
        
        start_time = time.time()
        
        try:
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(30)  # 30秒超时
            
            # 发送INVITE请求
            invite_message = self.create_invite_message(caller_uri, callee_uri, call_id)
            self.logger.logger.debug(f"发送INVITE消息: {invite_message[:200]}...")
            
            sock.sendto(invite_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            self.logger.logger.debug(f"收到响应: {response_str[:200]}...")
            
            # 解析响应
            parsed_response = self.parse_response(response_str)
            status_code = parsed_response.get('status_code', 0)
            
            if status_code == 180:
                # 收到振铃响应
                self.logger.logger.info("收到180 Ringing响应")
                self.set_state(SIPClientState.RINGING, "对方振铃")
                
                # 继续等待200 OK
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                parsed_response = self.parse_response(response_str)
                status_code = parsed_response.get('status_code', 0)
            
            if status_code == 200:
                # 收到OK响应
                self.logger.logger.info("收到200 OK响应，呼叫建立成功")
                
                # 提取To标签
                to_tag = ""
                if 'To' in parsed_response['headers']:
                    to_header = parsed_response['headers']['To']
                    if ';tag=' in to_header:
                        to_tag = to_header.split(';tag=')[1].split(';')[0]
                
                self.set_state(SIPClientState.IN_CALL, "通话中")
                
                # 发送ACK确认
                ack_message = self.create_ack_message(
                    caller_uri, callee_uri, call_id, 
                    cseq=1, to_tag=to_tag
                )
                self.logger.logger.debug(f"发送ACK消息: {ack_message[:200]}...")
                sock.sendto(ack_message.encode('utf-8'), (self.server_host, self.server_port))
                
                # 保持通话指定时间
                time.sleep(duration)
                
                # 发送BYE结束通话
                bye_message = self.create_bye_message(
                    caller_uri, callee_uri, call_id, 
                    cseq=2, from_tag=caller_uri.split('tag=')[1] if 'tag=' in caller_uri else '', 
                    to_tag=to_tag
                )
                self.logger.logger.debug(f"发送BYE消息: {bye_message[:200]}...")
                sock.sendto(bye_message.encode('utf-8'), (self.server_host, self.server_port))
                
                # 等待BYE响应
                try:
                    response_data, server_addr = sock.recvfrom(4096)
                    response_str = response_data.decode('utf-8')
                    self.logger.logger.debug(f"收到BYE响应: {response_str[:200]}...")
                except socket.timeout:
                    self.logger.logger.warning("等待BYE响应超时")
                
                sock.close()
                
                self.set_state(SIPClientState.IDLE, "通话结束")
                total_time = time.time() - start_time
                self.logger.log_test_success(f"呼叫 {caller_uri} -> {callee_uri}", total_time)
                return True
            else:
                error_msg = f"呼叫失败，收到状态码: {status_code} {parsed_response.get('reason_phrase', '')}"
                self.logger.log_test_failure(f"呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                sock.close()
                self.set_state(SIPClientState.ERROR, f"呼叫失败: {error_msg}")
                return False
                
        except socket.timeout:
            error_msg = "等待SIP响应超时"
            self.logger.log_test_failure(f"呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
            sock.close()
            self.set_state(SIPClientState.ERROR, f"等待响应超时: {error_msg}")
            return False
        except Exception as e:
            error_msg = f"呼叫执行失败: {str(e)}"
            self.logger.log_test_failure(f"呼叫 {caller_uri} -> {callee_uri}", e)
            self.set_state(SIPClientState.ERROR, f"呼叫执行异常: {str(e)}")
            return False

    def send_prack(self, rseq: int, method: str, call_info: Dict[str, Any]) -> bool:
        """
        发送PRACK消息以确认可靠的临时响应
        
        Args:
            rseq: RAck序列号
            method: RAck方法
            call_info: 呼叫信息字典
            
        Returns:
            bool: 发送是否成功
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            prack_message = self.create_prack_message(
                rseq, method, call_info.get('req_uri', ''), 
                call_info.get('call_id', ''), 
                call_info.get('cseq', 1), 
                call_info.get('from_uri', ''), 
                call_info.get('to_uri', ''), 
                call_info.get('from_tag', ''), 
                call_info.get('to_tag', '')
            )
            
            sock.sendto(prack_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            sock.close()
            return True
        except Exception as e:
            self.logger.logger.error(f"发送PRACK失败: {str(e)}")
            return False

    def send_update(self, call_info: Dict[str, Any], sdp_content: str = None) -> bool:
        """
        发送UPDATE消息以更新会话参数
        
        Args:
            call_info: 呼叫信息字典
            sdp_content: 新的SDP内容（可选）
            
        Returns:
            bool: 发送是否成功
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            update_message = self.create_update_message(
                call_info.get('req_uri', ''), 
                call_info.get('call_id', ''), 
                call_info.get('cseq', 1), 
                call_info.get('from_uri', ''), 
                call_info.get('to_uri', ''), 
                call_info.get('from_tag', ''), 
                call_info.get('to_tag', ''), 
                sdp_content=sdp_content
            )
            
            sock.sendto(update_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            sock.close()
            return True
        except Exception as e:
            self.logger.logger.error(f"发送UPDATE失败: {str(e)}")
            return False

    def send_info(self, call_info: Dict[str, Any], content: str, content_type: str = "application/dtmf-relay") -> bool:
        """
        发送INFO消息以传输会话期间的额外信息
        
        Args:
            call_info: 呼叫信息字典
            content: 消息内容
            content_type: 内容类型
            
        Returns:
            bool: 发送是否成功
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            info_message = self.create_info_message(
                call_info.get('req_uri', ''), 
                call_info.get('call_id', ''), 
                call_info.get('cseq', 1), 
                call_info.get('from_uri', ''), 
                call_info.get('to_uri', ''), 
                call_info.get('from_tag', ''), 
                call_info.get('to_tag', ''), 
                content, content_type
            )
            
            sock.sendto(info_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            sock.close()
            return True
        except Exception as e:
            self.logger.logger.error(f"发送INFO失败: {str(e)}")
            return False

    def send_refer(self, call_info: Dict[str, Any], refer_to: str, referred_by: str = None) -> bool:
        """
        发送REFER消息以引用第三方参与对话
        
        Args:
            call_info: 呼叫信息字典
            refer_to: 引用目标
            referred_by: 引用发起者（可选）
            
        Returns:
            bool: 发送是否成功
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            if not referred_by:
                referred_by = call_info.get('from_uri', '')
            
            refer_message = self.create_refer_message(
                referred_by, refer_to,
                call_info.get('call_id', ''), 
                call_info.get('cseq', 1), 
                call_info.get('from_uri', ''), 
                call_info.get('to_uri', ''), 
                call_info.get('from_tag', ''), 
                call_info.get('to_tag', '')
            )
            
            sock.sendto(refer_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            sock.close()
            return True
        except Exception as e:
            self.logger.logger.error(f"发送REFER失败: {str(e)}")
            return False

    def send_subscribe(self, call_info: Dict[str, Any], event: str, expires: int = 3600) -> bool:
        """
        发送SUBSCRIBE消息以订阅事件包
        
        Args:
            call_info: 呼叫信息字典
            event: 事件包名称
            expires: 过期时间
            
        Returns:
            bool: 发送是否成功
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            subscribe_message = self.create_subscribe_message(
                event,
                call_info.get('call_id', ''), 
                call_info.get('cseq', 1), 
                call_info.get('from_uri', ''), 
                call_info.get('to_uri', ''), 
                call_info.get('from_tag', ''), 
                call_info.get('to_tag', ''),
                expires
            )
            
            sock.sendto(subscribe_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            sock.close()
            return True
        except Exception as e:
            self.logger.logger.error(f"发送SUBSCRIBE失败: {str(e)}")
            return False

    def send_notify(self, call_info: Dict[str, Any], subscription_state: str, event: str, 
                   content: str = "", content_type: str = "") -> bool:
        """
        发送NOTIFY消息以通知订阅者事件状态变化
        
        Args:
            call_info: 呼叫信息字典
            subscription_state: 订阅状态
            event: 事件包名称
            content: 消息内容
            content_type: 内容类型
            
        Returns:
            bool: 发送是否成功
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            notify_message = self.create_notify_message(
                subscription_state, event,
                call_info.get('call_id', ''), 
                call_info.get('cseq', 1), 
                call_info.get('from_uri', ''), 
                call_info.get('to_uri', ''), 
                call_info.get('from_tag', ''), 
                call_info.get('to_tag', ''),
                content, content_type
            )
            
            sock.sendto(notify_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            sock.close()
            return True
        except Exception as e:
            self.logger.logger.error(f"发送NOTIFY失败: {str(e)}")
            return False

    def send_message(self, call_info: Dict[str, Any], content: str, 
                    content_type: str = "text/plain", from_uri: str = None, to_uri: str = None) -> bool:
        """
        发送MESSAGE消息以发送即时消息
        
        Args:
            call_info: 呼叫信息字典
            content: 消息内容
            content_type: 内容类型
            from_uri: 发送方URI（可选）
            to_uri: 接收方URI（可选）
            
        Returns:
            bool: 发送是否成功
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            # 使用传入的URI或者从call_info中获取
            msg_from_uri = from_uri or call_info.get('from_uri', '')
            msg_to_uri = to_uri or call_info.get('to_uri', '')
            
            message = self.create_message_message(
                call_info.get('call_id', ''), 
                call_info.get('cseq', 1), 
                msg_from_uri, 
                msg_to_uri, 
                call_info.get('from_tag', ''), 
                call_info.get('to_tag', ''),
                content, content_type
            )
            
            sock.sendto(message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 接收响应
            response_data, server_addr = sock.recvfrom(4096)
            response_str = response_data.decode('utf-8')
            
            sock.close()
            return True
        except Exception as e:
            self.logger.logger.error(f"发送MESSAGE失败: {str(e)}")
            return False


def main():
    """主函数，用于测试增强版SIP客户端"""
    print("增强版SIP客户端测试")
    
    # 创建测试实例
    tester = EnhancedSIPCallTester(server_host="127.0.0.1", server_port=5060)
    
    # 测试生成各种消息
    call_id = tester.generate_call_id()
    from_uri = "sip:alice@127.0.0.1:5060"
    to_uri = "sip:bob@127.0.0.1:5060"
    
    print(f"生成的Call-ID: {call_id}")
    print(f"生成的Tag: {tester.generate_tag()}")
    
    # 测试PRACK消息生成
    prack_msg = tester.create_prack_message(1, "INVITE", to_uri, call_id, 1, from_uri, to_uri, "tag123", "tag456")
    print(f"PRACK消息示例:\n{prack_msg}")
    
    # 测试UPDATE消息生成
    update_msg = tester.create_update_message(to_uri, call_id, 1, from_uri, to_uri, "tag123", "tag456")
    print(f"UPDATE消息示例:\n{update_msg}")
    
    # 测试INFO消息生成
    info_msg = tester.create_info_message(to_uri, call_id, 1, from_uri, to_uri, "tag123", "tag456", "Signal=1234", "application/dtmf-relay")
    print(f"INFO消息示例:\n{info_msg}")
    
    print("测试完成")


if __name__ == "__main__":
    main()