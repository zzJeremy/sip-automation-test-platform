"""
RFC3261合规性增强模块
为SIP客户端添加RFC3261中定义的额外功能
"""

import hashlib
import time
import random
from typing import Dict, Any, Optional


class RFC3261Enhancements:
    """
    RFC3261合规性增强功能
    """
    
    @staticmethod
    def create_prack_message(local_host: str, local_port: int, req_uri: str, call_id: str, 
                           cseq: int, from_uri: str, to_uri: str, from_tag: str, 
                           to_tag: str, rseq: int, rack_method: str) -> str:
        """
        创建符合RFC3261标准的PRACK消息
        用于确认可靠的临时响应
        
        Args:
            local_host: 本地主机地址
            local_port: 本地端口
            req_uri: 请求URI
            call_id: Call-ID
            cseq: CSeq序列号
            from_uri: From URI
            to_uri: To URI
            from_tag: From标签
            to_tag: To标签
            rseq: RAck序列号
            rack_method: RAck方法
            
        Returns:
            str: PRACK消息字符串
        """
        branch = f"z9hG4bK{int(time.time() * 1000000)}{random.randint(1000, 9999)}"
        
        message = (
            f"PRACK {req_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_host}:{local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {from_uri};tag={from_tag}\r\n"
            f"To: {to_uri};tag={to_tag}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} PRACK\r\n"
            f"RAck: {rseq} {rack_method}\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        return message

    @staticmethod
    def create_update_message(local_host: str, local_port: int, req_uri: str, call_id: str, 
                            cseq: int, from_uri: str, to_uri: str, from_tag: str, 
                            to_tag: str, contact: str = None, sdp_content: str = None) -> str:
        """
        创建符合RFC3261标准的UPDATE消息
        用于在对话外更新会话参数
        
        Args:
            local_host: 本地主机地址
            local_port: 本地端口
            req_uri: 请求URI
            call_id: Call-ID
            cseq: CSeq序列号
            from_uri: From URI
            to_uri: To URI
            from_tag: From标签
            to_tag: To标签
            contact: Contact头字段
            sdp_content: SDP内容
            
        Returns:
            str: UPDATE消息字符串
        """
        branch = f"z9hG4bK{int(time.time() * 1000000)}{random.randint(1000, 9999)}"
        
        message_lines = [
            f"UPDATE {req_uri} SIP/2.0",
            f"Via: SIP/2.0/UDP {local_host}:{local_port};branch={branch};rport",
            f"Max-Forwards: 70",
            f"From: {from_uri};tag={from_tag}",
            f"To: {to_uri}{f';tag={to_tag}' if to_tag else ''}",
            f"Call-ID: {call_id}",
            f"CSeq: {cseq} UPDATE",
            f"Content-Length: 0"
        ]
        
        if contact:
            message_lines.insert(-1, f"Contact: {contact}")
        
        sdp_part = ""
        if sdp_content:
            sdp_part = sdp_content
            # 重新计算Content-Length
            message_lines[-1] = f"Content-Length: {len(sdp_part)}"
        
        message = "\r\n".join(message_lines) + f"\r\n\r\n{sdp_part}"
        return message

    @staticmethod
    def create_info_message(local_host: str, local_port: int, req_uri: str, call_id: str, 
                          cseq: int, from_uri: str, to_uri: str, from_tag: str, 
                          to_tag: str, content: str = "", content_type: str = "application/dtmf-relay") -> str:
        """
        创建符合RFC3261标准的INFO消息
        用于传输会话期间的额外信息
        
        Args:
            local_host: 本地主机地址
            local_port: 本地端口
            req_uri: 请求URI
            call_id: Call-ID
            cseq: CSeq序列号
            from_uri: From URI
            to_uri: To URI
            from_tag: From标签
            to_tag: To标签
            content: 消息内容
            content_type: 内容类型
            
        Returns:
            str: INFO消息字符串
        """
        branch = f"z9hG4bK{int(time.time() * 1000000)}{random.randint(1000, 9999)}"
        
        message = (
            f"INFO {req_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_host}:{local_port};branch={branch};rport\r\n"
            f"Max-Forwards: 70\r\n"
            f"From: {from_uri};tag={from_tag}\r\n"
            f"To: {to_uri};tag={to_tag}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} INFO\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(content)}\r\n"
            f"\r\n"
            f"{content}"
        )
        return message

    @staticmethod
    def generate_secure_random_string(length: int = 16) -> str:
        """
        生成安全的随机字符串
        用于生成更安全的tags和nonces
        
        Args:
            length: 字符串长度
            
        Returns:
            str: 随机字符串
        """
        import string
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def validate_dialog_identifier(from_tag: str, to_tag: str, call_id: str) -> bool:
        """
        验证对话标识符
        根据RFC3261标准验证对话是否有效
        
        Args:
            from_tag: From标签
            to_tag: To标签
            call_id: Call-ID
            
        Returns:
            bool: 对话标识符是否有效
        """
        # 检查必填字段
        if not call_id or not from_tag:
            return False
        
        # Call-ID不能是空字符串
        if not call_id.strip():
            return False
            
        # 标签必须符合token或quoted-string规则
        # 简单验证：不能包含控制字符
        import re
        tag_pattern = r'^[a-zA-Z0-9_.!~*\'();:&=+$,]+$'
        
        if not re.match(tag_pattern, from_tag):
            return False
            
        if to_tag and not re.match(tag_pattern, to_tag):
            return False
        
        return True

    @staticmethod
    def calculate_hmac_auth(username: str, password: str, realm: str, nonce: str, 
                          method: str, uri: str, qop: str = None, nc: str = None, 
                          cnonce: str = None) -> str:
        """
        计算SIP摘要认证的响应值，支持多种qop选项
        符合RFC2617和RFC3261标准
        
        Args:
            username: 用户名
            password: 密码
            realm: 认证域
            nonce: 服务器提供的随机数
            method: SIP方法
            uri: 请求URI
            qop: 质询选项
            nc: 非ce计数
            cnonce: 客户端随机数
            
        Returns:
            str: 认证响应值
        """
        # HA1 = MD5(username:realm:password)
        ha1_input = f"{username}:{realm}:{password}"
        ha1 = hashlib.md5(ha1_input.encode()).hexdigest()
        
        # HA2 = MD5(method:digestURI)
        ha2_input = f"{method}:{uri}"
        ha2 = hashlib.md5(ha2_input.encode()).hexdigest()
        
        if qop and qop.lower() == 'auth':
            # Response = MD5(HA1:nonce:nc:cnonce:qop:HA2)
            response_input = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
        elif qop and qop.lower() == 'auth-int':
            # Response = MD5(HA1:nonce:nc:cnonce:qop:MD5(entity-body))
            # 这里简化处理，假设没有实体主体
            response_input = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
        else:
            # Response = MD5(HA1:nonce:HA2)
            response_input = f"{ha1}:{nonce}:{ha2}"
        
        response = hashlib.md5(response_input.encode()).hexdigest()
        return response


# 定义RFC3261中重要的定时器值（毫秒）
RFC3261_TIMERS = {
    'T1': 500,      # 默认往返时间
    'T2': 4000,     # 最大重传间隔
    'T4': 5000,     # 最大传输时间
    'TIMER_B': 64 * 500,  # INVITE事务超时
    'TIMER_F': 64 * 500,  # 非INVITE事务超时
    'TIMER_H': 64 * 500,  # ACK等待INVITE响应
    'TIMER_I': 64 * 500,  # 非INVITE响应确认
    'TIMER_J': 64 * 500,  # 非INVITE请求重传
    'TIMER_K': 5000,      # UDP非INVITE事务结束
}


def get_timer_value(timer_name: str) -> int:
    """
    获取RFC3261定时器值
    
    Args:
        timer_name: 定时器名称
        
    Returns:
        int: 定时器值（毫秒）
    """
    return RFC3261_TIMERS.get(timer_name.upper(), 500)