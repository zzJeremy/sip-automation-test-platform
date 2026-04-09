"""
SIP基础通话测试客户端
严格按照RFC3261标准实现SIP呼叫功能
支持完整的呼叫流程：INVITE -> 180/200 OK -> ACK -> BYE
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
except ImportError:
    from error_handler import error_handler, retry_on_failure, SIPTestLogger, validate_sip_uri
    from rfc3261_enhancements import RFC3261Enhancements, get_timer_value


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


class BasicSIPCallTester:
    """
    基础SIP通话测试器
    严格按照RFC3261标准实现SIP呼叫流程
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
        self._supported_methods = ["INVITE", "ACK", "CANCEL", "BYE", "OPTIONS"]
        self._supported_options = ["100rel", "precondition", "timer"]
        
        # 设置日志
        self.logger = SIPTestLogger("BasicSIPCallTester", "basic_sip_call_tester.log")
        
        # 初始化客户端状态
        self._state = SIPClientState.UNREGISTERED
        self.current_call_id = None
        self.is_registered = False
        self.registration_expires = 0
        self.current_call_info = {}
    
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
    
    def create_invite_message(self, caller_uri: str, callee_uri: str, call_id: str, 
                             proxy_auth_nonce: str = "", proxy_auth_realm: str = "", 
                             proxy_username: str = "", proxy_password: str = "", cseq: int = 1) -> str:
        """
        创建符合RFC3261标准的INVITE请求消息
        包含所有必需的头字段，支持代理认证
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
            f"CSeq: {cseq} INVITE\r\n"
            f"Contact: <sip:{self.local_host}:{self.local_port}>\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp_content)}\r\n"
            f"Allow: {', '.join(self._supported_methods)}\r\n"
            f"Supported: {', '.join(self._supported_options)}\r\n"
            f"User-Agent: BasicSIPCallTester RFC3261 Compliant\r\n"
        )
        
        # 如果提供了代理认证信息，则添加Proxy-Authorization头部
        if proxy_auth_nonce and proxy_auth_realm and proxy_username and proxy_password:
            import hashlib
            
            # 计算代理认证信息 - RFC 2617标准
            # HA1 = MD5(username:realm:password)
            ha1_input = f"{proxy_username}:{proxy_auth_realm}:{proxy_password}"
            ha1 = hashlib.md5(ha1_input.encode()).hexdigest()
            
            # HA2 = MD5(method:digestURI) 
            ha2_input = f"INVITE:{callee_uri}"
            ha2 = hashlib.md5(ha2_input.encode()).hexdigest()
            
            # response = MD5(HA1:nonce:HA2)
            response_input = f"{ha1}:{proxy_auth_nonce}:{ha2}"
            response = hashlib.md5(response_input.encode()).hexdigest()
            
            auth_header = (
                f'Proxy-Authorization: Digest username="{proxy_username}", '
                f'realm="{proxy_auth_realm}", nonce="{proxy_auth_nonce}", uri="{callee_uri}", '
                f'response="{response}", algorithm=MD5\r\n'
            )
            message += auth_header
        
        message += "\r\n"
        message += sdp_content
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
    def make_basic_call(self, caller_uri: str, callee_uri: str, call_duration: int = 5, 
                       proxy_username: str = "", proxy_password: str = "") -> bool:
        """
        执行符合RFC3261标准的基础SIP呼叫
        
        Args:
            caller_uri: 主叫URI (e.g., "sip:alice@127.0.0.1:5060")
            callee_uri: 被叫URI (e.g., "sip:bob@127.0.0.1:5060")
            call_duration: 通话持续时间（秒）
            proxy_username: 代理服务器用户名（可选）
            proxy_password: 代理服务器密码（可选）
            
        Returns:
            bool: 呼叫是否成功
        """
        # 验证SIP URI格式
        if not self.validate_uri(caller_uri) or not self.validate_uri(callee_uri):
            self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(f"无效的SIP URI格式: {caller_uri} -> {callee_uri}"))
            self.set_state(SIPClientState.ERROR, f"无效的SIP URI格式: {caller_uri} -> {callee_uri}")
            return False
        
        # 检查是否已注册
        if not self.is_registered:
            self.logger.logger.warning("客户端尚未注册，仍可尝试呼叫")
        
        call_id = self.generate_call_id()
        self.current_call_id = call_id
        self.current_call_info = {
            'caller': caller_uri,
            'callee': callee_uri,
            'start_time': time.time(),
            'duration': call_duration
        }
        
        self.logger.log_test_start(f"基础呼叫 {caller_uri} -> {callee_uri}", {"call_id": call_id, "duration": call_duration})
        
        # 设置状态为CALLING
        self.set_state(SIPClientState.CALLING, f"开始呼叫 {caller_uri} -> {callee_uri}")
        
        start_time = time.time()
        
        try:
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)  # 10秒超时
            
            # 步骤1: 发送初始INVITE
            invite_message = self.create_invite_message(caller_uri, callee_uri, call_id)
            self.logger.logger.debug(f"发送初始INVITE消息: {invite_message[:200]}...")
            
            sock.sendto(invite_message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 步骤2: 等待响应
            to_tag = ""  # 用于存储To头字段的tag
            try:
                response_data, server_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                self.logger.logger.debug(f"收到响应: {response_str[:200]}...")
                
                # 解析响应
                parsed_response = self.parse_response(response_str)
                status_code = parsed_response.get('status_code', 0)
                
                # 获取To头字段的tag（如果存在）
                to_header = parsed_response.get('headers', {}).get('To', '')
                if ';tag=' in to_header:
                    to_tag = to_header.split(';tag=')[1].split(';')[0]
                
                # 检查是否为401/407认证挑战
                if status_code in [401, 407]:
                    self.logger.logger.info(f"收到认证挑战 {status_code}，提取认证信息")
                    
                    # 提取认证信息
                    realm, nonce = self.extract_auth_info(response_str)
                    
                    if not realm or not nonce:
                        error_msg = f"无法从认证挑战响应中提取认证信息: {response_str[:100]}"
                        self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                        self.set_state(SIPClientState.ERROR, f"无法提取认证信息: {error_msg}")
                        sock.close()
                        return False
                    
                    # 检查是否提供了代理认证凭据
                    if not proxy_username or not proxy_password:
                        error_msg = f"需要代理认证，但未提供认证凭据。收到状态码: {status_code} {parsed_response.get('reason_phrase', '')}"
                        self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                        self.set_state(SIPClientState.ERROR, f"缺少代理认证凭据: {error_msg}")
                        sock.close()
                        return False
                    
                    self.logger.logger.info(f"使用认证信息重新发送INVITE请求，realm: {realm}")
                    
                    # 使用认证信息重新发送INVITE请求
                    # 获取CSeq信息并递增
                    cseq_header = parsed_response.get('headers', {}).get('CSeq', '1 INVITE')
                    cseq_num = int(cseq_header.split()[0]) + 1  # 递增CSeq
                    authenticated_invite_message = self.create_invite_message(
                        caller_uri=caller_uri,
                        callee_uri=callee_uri,
                        call_id=call_id,
                        proxy_auth_nonce=nonce,
                        proxy_auth_realm=realm,
                        proxy_username=proxy_username,
                        proxy_password=proxy_password,
                        cseq=cseq_num
                    )
                    
                    sock.sendto(authenticated_invite_message.encode('utf-8'), (self.server_host, self.server_port))
                    
                    # 接收认证后的响应
                    try:
                        response_data, server_addr = sock.recvfrom(4096)
                        response_str = response_data.decode('utf-8')
                        self.logger.logger.debug(f"收到认证后响应: {response_str[:200]}...")
                        
                        # 解析认证后响应
                        parsed_response = self.parse_response(response_str)
                        status_code = parsed_response.get('status_code', 0)
                        
                        # 获取To头字段的tag（如果存在）
                        to_header = parsed_response.get('headers', {}).get('To', '')
                        if ';tag=' in to_header:
                            to_tag = to_header.split(';tag=')[1].split(';')[0]
                        
                    except socket.timeout:
                        error_msg = "等待认证后响应超时"
                        self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                        self.set_state(SIPClientState.ERROR, f"等待认证后响应超时")
                        sock.close()
                        return False
                
                # 处理临时响应 (1xx)
                if 100 <= status_code < 200:
                    self.logger.logger.info(f"收到临时响应: {status_code} {parsed_response.get('reason_phrase', '')}")
                    self.set_state(SIPClientState.RINGING, f"收到临时响应 {status_code}")
                    
                    # 如果是Trying (100)或其他临时响应，继续等待最终响应
                    if status_code != 100:  # 180 Ringing, 183 Session Progress等
                        # 等待最终响应
                        response_data, server_addr = sock.recvfrom(4096)
                        response_str = response_data.decode('utf-8')
                        parsed_response = self.parse_response(response_str)
                        status_code = parsed_response.get('status_code', 0)
                        
                        # 再次检查To头字段的tag
                        to_header = parsed_response.get('headers', {}).get('To', '')
                        if ';tag=' in to_header:
                            to_tag = to_header.split(';tag=')[1].split(';')[0]
                
                # 处理临时响应 (1xx) - 在认证处理之后
                # 循环处理所有临时响应，直到收到最终响应
                while 100 <= status_code < 200:
                    self.logger.logger.info(f"收到临时响应: {status_code} {parsed_response.get('reason_phrase', '')}")
                    self.set_state(SIPClientState.RINGING, f"收到临时响应 {status_code}")
                    
                    # 对于临时响应（100-199），继续等待下一个响应
                    try:
                        response_data, server_addr = sock.recvfrom(4096)
                        response_str = response_data.decode('utf-8')
                        self.logger.logger.debug(f"收到后续响应: {response_str[:200]}...")
                        
                        # 解析下一个响应
                        parsed_response = self.parse_response(response_str)
                        status_code = parsed_response.get('status_code', 0)
                        
                        # 更新To头字段的tag
                        to_header = parsed_response.get('headers', {}).get('To', '')
                        if ';tag=' in to_header:
                            to_tag = to_header.split(';tag=')[1].split(';')[0]
                    except socket.timeout:
                        error_msg = "等待SIP响应超时"
                        self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                        self.set_state(SIPClientState.IDLE, f"等待响应超时，返回空闲状态")
                        sock.close()
                        return False
                
                # 检查是否为200 OK最终响应
                if status_code == 200:
                    self.logger.logger.info("收到200 OK响应，发送ACK确认")
                    self.set_state(SIPClientState.IN_CALL, f"建立通话连接，通话ID: {call_id}")
                    
                    # 获取CSeq信息
                    cseq_header = parsed_response.get('headers', {}).get('CSeq', '1 INVITE')
                    cseq_num = int(cseq_header.split()[0])
                    
                    # 发送ACK
                    ack_message = self.create_ack_message(
                        caller_uri=caller_uri, 
                        callee_uri=callee_uri, 
                        call_id=call_id, 
                        cseq=cseq_num,
                        to_tag=to_tag
                    )
                    sock.sendto(ack_message.encode('utf-8'), (self.server_host, self.server_port))
                    
                    # 保持通话
                    self.logger.logger.info(f"保持通话 {call_duration} 秒")
                    time.sleep(call_duration)
                    
                    # 发送BYE结束通话
                    self.logger.logger.info("发送BYE请求结束通话")
                    self.set_state(SIPClientState.HANGING_UP, f"准备结束通话，通话ID: {call_id}")
                    
                    # RFC3261规定：对于新的请求（如BYE），应该使用递增的CSeq值
                    # INVITE的CSeq为1，因此BYE的CSeq应该是2
                    bye_cseq = cseq_num + 1 if cseq_num >= 1 else 2
                    bye_message = self.create_bye_message(
                        caller_uri=caller_uri, 
                        callee_uri=callee_uri, 
                        call_id=call_id, 
                        cseq=bye_cseq,
                        from_tag=caller_uri.split('tag=')[1] if 'tag=' in caller_uri else "",
                        to_tag=to_tag
                    )
                    sock.sendto(bye_message.encode('utf-8'), (self.server_host, self.server_port))
                    
                    # 尝试接收BYE确认
                    try:
                        response_data, server_addr = sock.recvfrom(4096)
                        response_str = response_data.decode('utf-8')
                        bye_parsed = self.parse_response(response_str)
                        bye_status = bye_parsed.get('status_code', 0)
                        
                        if bye_status == 200:
                            self.logger.logger.info("收到BYE确认，通话成功完成")
                        else:
                            self.logger.logger.info(f"收到BYE响应: {bye_status} {bye_parsed.get('reason_phrase', '')}")
                    except socket.timeout:
                        self.logger.logger.info("BYE确认超时，但通话已尝试结束")
                    
                    sock.close()
                    
                    # 通话结束后回到空闲状态
                    self.set_state(SIPClientState.IDLE, f"通话结束，通话ID: {call_id}")
                    self.current_call_id = None
                    self.current_call_info = {}
                    
                    total_time = time.time() - start_time
                    self.logger.log_test_success(f"基础呼叫 {caller_uri} -> {callee_uri}", total_time)
                    return True
                # 检查是否为407代理认证响应（可能在转发过程中出现）
                elif status_code == 407:
                    self.logger.logger.info(f"收到认证挑战 {status_code}，提取认证信息")
                    
                    # 提取认证信息
                    realm, nonce = self.extract_auth_info(response_str)
                    
                    if not realm or not nonce or not proxy_username or not proxy_password:
                        error_msg = f"无法从认证挑战响应中提取认证信息或缺少代理认证凭据: {response_str[:100]}"
                        self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                        self.set_state(SIPClientState.ERROR, f"无法提取认证信息: {error_msg}")
                        sock.close()
                        return False
                    
                    self.logger.logger.info(f"使用认证信息重新发送INVITE请求，realm: {realm}")
                    
                    # 获取CSeq信息并递增
                    cseq_header = parsed_response.get('headers', {}).get('CSeq', '1 INVITE')
                    cseq_num = int(cseq_header.split()[0]) + 1  # 递增CSeq
                    
                    # 使用认证信息重新发送INVITE请求（可能是在转发过程中的认证）
                    authenticated_invite_message = self.create_invite_message(
                        caller_uri=caller_uri,
                        callee_uri=callee_uri,
                        call_id=call_id,
                        proxy_auth_nonce=nonce,
                        proxy_auth_realm=realm,
                        proxy_username=proxy_username,
                        proxy_password=proxy_password,
                        cseq=cseq_num
                    )
                    
                    sock.sendto(authenticated_invite_message.encode('utf-8'), (self.server_host, self.server_port))
                    
                    # 接收认证后的响应
                    try:
                        response_data, server_addr = sock.recvfrom(4096)
                        response_str = response_data.decode('utf-8')
                        self.logger.logger.debug(f"收到认证后响应: {response_str[:200]}...")
                        
                        # 解析认证后响应
                        parsed_response = self.parse_response(response_str)
                        status_code = parsed_response.get('status_code', 0)
                        
                        # 获取To头字段的tag（如果存在）
                        to_header = parsed_response.get('headers', {}).get('To', '')
                        if ';tag=' in to_header:
                            to_tag = to_header.split(';tag=')[1].split(';')[0]
                        
                        # 再次检查是否为200 OK最终响应
                        if status_code == 200:
                            self.logger.logger.info("收到200 OK响应，发送ACK确认")
                            self.set_state(SIPClientState.IN_CALL, f"建立通话连接，通话ID: {call_id}")
                            
                            # 获取CSeq信息
                            cseq_header = parsed_response.get('headers', {}).get('CSeq', f'{cseq_num} INVITE')
                            cseq_num = int(cseq_header.split()[0])
                            
                            # 发送ACK
                            ack_message = self.create_ack_message(
                                caller_uri=caller_uri, 
                                callee_uri=callee_uri, 
                                call_id=call_id, 
                                cseq=cseq_num,
                                to_tag=to_tag
                            )
                            sock.sendto(ack_message.encode('utf-8'), (self.server_host, self.server_port))
                            
                            # 保持通话
                            self.logger.logger.info(f"保持通话 {call_duration} 秒")
                            time.sleep(call_duration)
                            
                            # 发送BYE结束通话
                            self.logger.logger.info("发送BYE请求结束通话")
                            self.set_state(SIPClientState.HANGING_UP, f"准备结束通话，通话ID: {call_id}")
                            
                            # RFC3261规定：对于新的请求（如BYE），应该使用递增的CSeq值
                            # INVITE的CSeq为当前值，因此BYE的CSeq应该是当前值+1
                            bye_cseq = cseq_num + 1
                            bye_message = self.create_bye_message(
                                caller_uri=caller_uri, 
                                callee_uri=callee_uri, 
                                call_id=call_id, 
                                cseq=bye_cseq,
                                from_tag=caller_uri.split('tag=')[1] if 'tag=' in caller_uri else "",
                                to_tag=to_tag
                            )
                            sock.sendto(bye_message.encode('utf-8'), (self.server_host, self.server_port))
                            
                            # 尝试接收BYE确认
                            try:
                                response_data, server_addr = sock.recvfrom(4096)
                                response_str = response_data.decode('utf-8')
                                bye_parsed = self.parse_response(response_str)
                                bye_status = bye_parsed.get('status_code', 0)
                                
                                if bye_status == 200:
                                    self.logger.logger.info("收到BYE确认，通话成功完成")
                                else:
                                    self.logger.logger.info(f"收到BYE响应: {bye_status} {bye_parsed.get('reason_phrase', '')}")
                            except socket.timeout:
                                self.logger.logger.info("BYE确认超时，但通话已尝试结束")
                            
                            sock.close()
                            
                            # 通话结束后回到空闲状态
                            self.set_state(SIPClientState.IDLE, f"通话结束，通话ID: {call_id}")
                            self.current_call_id = None
                            self.current_call_info = {}
                            
                            total_time = time.time() - start_time
                            self.logger.log_test_success(f"基础呼叫 {caller_uri} -> {callee_uri}", total_time)
                            return True
                        else:
                            # 如果认证后仍未收到200 OK，处理可能的临时响应
                            if 100 <= status_code < 200:
                                # 循环处理所有临时响应，直到收到最终响应
                                while 100 <= status_code < 200:
                                    self.logger.logger.info(f"收到临时响应: {status_code} {parsed_response.get('reason_phrase', '')}")
                                    self.set_state(SIPClientState.RINGING, f"收到临时响应 {status_code}")
                                    
                                    # 对于临时响应（100-199），继续等待下一个响应
                                    try:
                                        response_data, server_addr = sock.recvfrom(4096)
                                        response_str = response_data.decode('utf-8')
                                        self.logger.logger.debug(f"收到后续响应: {response_str[:200]}...")
                                        
                                        # 解析下一个响应
                                        parsed_response = self.parse_response(response_str)
                                        status_code = parsed_response.get('status_code', 0)
                                        
                                        # 更新To头字段的tag
                                        to_header = parsed_response.get('headers', {}).get('To', '')
                                        if ';tag=' in to_header:
                                            to_tag = to_header.split(';tag=')[1].split(';')[0]
                                    except socket.timeout:
                                        error_msg = "等待SIP响应超时"
                                        self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                                        self.set_state(SIPClientState.IDLE, f"等待响应超时，返回空闲状态")
                                        sock.close()
                                        return False
                                
                                # 最终检查是否为200 OK响应
                                if status_code == 200:
                                    self.logger.logger.info("收到200 OK响应，发送ACK确认")
                                    self.set_state(SIPClientState.IN_CALL, f"建立通话连接，通话ID: {call_id}")
                                    
                                    # 获取CSeq信息
                                    cseq_header = parsed_response.get('headers', {}).get('CSeq', f'{cseq_num} INVITE')
                                    cseq_num = int(cseq_header.split()[0])
                                    
                                    # 发送ACK
                                    ack_message = self.create_ack_message(
                                        caller_uri=caller_uri, 
                                        callee_uri=callee_uri, 
                                        call_id=call_id, 
                                        cseq=cseq_num,
                                        to_tag=to_tag
                                    )
                                    sock.sendto(ack_message.encode('utf-8'), (self.server_host, self.server_port))
                                    
                                    # 保持通话
                                    self.logger.logger.info(f"保持通话 {call_duration} 秒")
                                    time.sleep(call_duration)
                                    
                                    # 发送BYE结束通话
                                    self.logger.logger.info("发送BYE请求结束通话")
                                    self.set_state(SIPClientState.HANGING_UP, f"准备结束通话，通话ID: {call_id}")
                                    
                                    # RFC3261规定：对于新的请求（如BYE），应该使用递增的CSeq值
                                    # INVITE的CSeq为当前值，因此BYE的CSeq应该是当前值+1
                                    bye_cseq = cseq_num + 1
                                    bye_message = self.create_bye_message(
                                        caller_uri=caller_uri, 
                                        callee_uri=callee_uri, 
                                        call_id=call_id, 
                                        cseq=bye_cseq,
                                        from_tag=caller_uri.split('tag=')[1] if 'tag=' in caller_uri else "",
                                        to_tag=to_tag
                                    )
                                    sock.sendto(bye_message.encode('utf-8'), (self.server_host, self.server_port))
                                    
                                    # 尝试接收BYE确认
                                    try:
                                        response_data, server_addr = sock.recvfrom(4096)
                                        response_str = response_data.decode('utf-8')
                                        bye_parsed = self.parse_response(response_str)
                                        bye_status = bye_parsed.get('status_code', 0)
                                        
                                        if bye_status == 200:
                                            self.logger.logger.info("收到BYE确认，通话成功完成")
                                        else:
                                            self.logger.logger.info(f"收到BYE响应: {bye_status} {bye_parsed.get('reason_phrase', '')}")
                                    except socket.timeout:
                                        self.logger.logger.info("BYE确认超时，但通话已尝试结束")
                                    
                                    sock.close()
                                    
                                    # 通话结束后回到空闲状态
                                    self.set_state(SIPClientState.IDLE, f"通话结束，通话ID: {call_id}")
                                    self.current_call_id = None
                                    self.current_call_info = {}
                                    
                                    total_time = time.time() - start_time
                                    self.logger.log_test_success(f"基础呼叫 {caller_uri} -> {callee_uri}", total_time)
                                    return True
                                else:
                                    error_msg = f"认证后仍未收到预期的200 OK响应，收到: {status_code} {parsed_response.get('reason_phrase', '')}"
                                    self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                                    self.set_state(SIPClientState.IDLE, f"呼叫失败，返回空闲状态")
                                    sock.close()
                                    return False
                            else:
                                error_msg = f"认证后收到非200非临时响应: {status_code} {parsed_response.get('reason_phrase', '')}"
                                self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                                self.set_state(SIPClientState.IDLE, f"呼叫失败，返回空闲状态")
                                sock.close()
                                return False
                    except socket.timeout:
                        error_msg = "等待认证后响应超时"
                        self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                        self.set_state(SIPClientState.ERROR, f"等待认证后响应超时")
                        sock.close()
                        return False
                else:
                    error_msg = f"未收到预期的200 OK响应，收到: {status_code} {parsed_response.get('reason_phrase', '')}"
                    self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                    self.set_state(SIPClientState.IDLE, f"呼叫失败，返回空闲状态")
                    sock.close()
                    return False
                    
            except socket.timeout:
                error_msg = "等待SIP响应超时"
                self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", Exception(error_msg))
                self.set_state(SIPClientState.IDLE, f"等待响应超时，返回空闲状态")
                sock.close()
                return False
                
        except Exception as e:
            error_msg = f"基础呼叫执行失败: {str(e)}"
            self.logger.log_test_failure(f"基础呼叫 {caller_uri} -> {callee_uri}", e)
            self.set_state(SIPClientState.ERROR, f"基础呼叫执行异常: {str(e)}")
            return False


def main():
    """基础通话测试主函数"""
    # 创建基础SIP通话测试器
    tester = BasicSIPCallTester(
        server_host="127.0.0.1",
        server_port=5060,
        local_host="127.0.0.1",
        local_port=5080
    )
    
    # 执行基础呼叫测试
    success = tester.make_basic_call(
        caller_uri="sip:alice@127.0.0.1:5060",
        callee_uri="sip:bob@127.0.0.1:5060",
        call_duration=5  # 通话5秒
    )
    
    if success:
        print("基础SIP呼叫测试成功完成！")
    else:
        print("基础SIP呼叫测试失败！")


if __name__ == "__main__":
    main()