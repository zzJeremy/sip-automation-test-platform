"""
SIP客户端安全增强模块
提供安全的认证凭据管理和日志脱敏功能
"""

import hashlib
import hmac
import secrets
import logging
import re
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import base64


class SecureCredentialManager:
    """
    安全凭据管理器
    提供加密存储和安全访问认证凭据的功能
    """
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        初始化凭据管理器
        
        Args:
            encryption_key: 加密密钥，如果为None则生成新密钥
        """
        if encryption_key is None:
            self.encryption_key = Fernet.generate_key()
        else:
            self.encryption_key = encryption_key
        
        self.cipher_suite = Fernet(self.encryption_key)
        self.credentials_store = {}  # 内存中的加密凭据存储
    
    def store_credentials(self, identifier: str, username: str, password: str) -> bool:
        """
        安全存储认证凭据
        
        Args:
            identifier: 凭据标识符
            username: 用户名
            password: 密码
            
        Returns:
            bool: 存储是否成功
        """
        try:
            credential_data = {
                'username': username,
                'password': password,
                'timestamp': __import__('time').time()
            }
            
            # 序列化并加密凭据数据
            serialized_data = str(credential_data).encode('utf-8')
            encrypted_data = self.cipher_suite.encrypt(serialized_data)
            
            # 存储加密的凭据
            self.credentials_store[identifier] = encrypted_data
            return True
        except Exception as e:
            logging.error(f"存储凭据失败: {str(e)}")
            return False
    
    def retrieve_credentials(self, identifier: str) -> Optional[Dict[str, str]]:
        """
        检索认证凭据
        
        Args:
            identifier: 凭据标识符
            
        Returns:
            Dict: 包含用户名和密码的字典，如果失败则返回None
        """
        try:
            if identifier not in self.credentials_store:
                return None
            
            # 解密凭据数据
            encrypted_data = self.credentials_store[identifier]
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            
            # 反序列化凭据数据
            credential_data_str = decrypted_data.decode('utf-8')
            # 简单解析（在实际应用中可能需要更复杂的解析）
            import ast
            credential_data = ast.literal_eval(credential_data_str)
            
            return {
                'username': credential_data.get('username'),
                'password': credential_data.get('password')
            }
        except Exception as e:
            logging.error(f"检索凭据失败: {str(e)}")
            return None
    
    def remove_credentials(self, identifier: str) -> bool:
        """
        移除认证凭据
        
        Args:
            identifier: 凭据标识符
            
        Returns:
            bool: 移除是否成功
        """
        try:
            if identifier in self.credentials_store:
                del self.credentials_store[identifier]
            return True
        except Exception as e:
            logging.error(f"移除凭据失败: {str(e)}")
            return False


class SecureSIPLogger:
    """
    安全SIP日志记录器
    自动脱敏敏感信息如密码、认证凭据等
    """
    
    def __init__(self, name: str = "SecureSIPLogger", log_file: str = "secure_sip.log"):
        """
        初始化安全日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 创建文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def _sanitize_log_message(self, message: str) -> str:
        """
        脱敏日志消息中的敏感信息
        
        Args:
            message: 原始日志消息
            
        Returns:
            str: 脱敏后的日志消息
        """
        sanitized_message = message
        
        # 脱敏密码
        sanitized_message = re.sub(r'password=("[^"]*"|\'[^\']*\')', 'password="[HIDDEN]"', sanitized_message)
        sanitized_message = re.sub(r'(Password:\s*)(\S+)', r'\1[HIDDEN]', sanitized_message, flags=re.IGNORECASE)
        
        # 脱敏认证信息
        sanitized_message = re.sub(r'(Authorization:\s*.*?)(\S+)', lambda m: m.group(1) + '[HIDDEN]' if 'auth' in m.group(1).lower() else m.group(0), sanitized_message, flags=re.IGNORECASE)
        sanitized_message = re.sub(r'(Proxy-Authorization:\s*.*?)(\S+)', r'\1[HIDDEN]', sanitized_message, flags=re.IGNORECASE)
        
        # 脱敏URL中的密码
        sanitized_message = re.sub(r'(sips?://[^:]*:)([^@]*)@', r'\1[HIDDEN]@', sanitized_message)
        
        return sanitized_message
    
    def info(self, message: str):
        """记录INFO级别的日志"""
        sanitized_message = self._sanitize_log_message(str(message))
        self.logger.info(sanitized_message)
    
    def warning(self, message: str):
        """记录WARNING级别的日志"""
        sanitized_message = self._sanitize_log_message(str(message))
        self.logger.warning(sanitized_message)
    
    def error(self, message: str):
        """记录ERROR级别的日志"""
        sanitized_message = self._sanitize_log_message(str(message))
        self.logger.error(sanitized_message)
    
    def debug(self, message: str):
        """记录DEBUG级别的日志"""
        sanitized_message = self._sanitize_log_message(str(message))
        self.logger.debug(sanitized_message)
    
    def log_sip_message(self, direction: str, message: str):
        """记录SIP消息，自动脱敏敏感信息"""
        sanitized_message = self._sanitize_log_message(message)
        self.logger.debug(f"SIP消息 {direction}: {sanitized_message[:500]}...")


class SecurityUtils:
    """
    安全工具类
    提供各种安全相关的实用函数
    """
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """
        使用PBKDF2哈希密码
        
        Args:
            password: 原始密码
            salt: 盐值，如果为None则生成新盐值
            
        Returns:
            tuple: (哈希值, 盐值)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        pwdhash = hashlib.pbkdf2_hmac('sha256',
                                      password.encode('utf-8'),
                                      salt.encode('ascii'),
                                      100000)
        return base64.b64encode(pwdhash).decode('ascii'), salt
    
    @staticmethod
    def verify_password(stored_hash: str, provided_password: str, salt: str) -> bool:
        """
        验证密码
        
        Args:
            stored_hash: 存储的哈希值
            provided_password: 提供的密码
            salt: 盐值
            
        Returns:
            bool: 密码是否匹配
        """
        pwdhash, _ = SecurityUtils.hash_password(provided_password, salt)
        return hmac.compare_digest(pwdhash, stored_hash)
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        生成安全令牌
        
        Args:
            length: 令牌长度
            
        Returns:
            str: 生成的安全令牌
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def sanitize_sip_uri(uri: str) -> str:
        """
        脱敏SIP URI中的敏感信息
        
        Args:
            uri: 原始SIP URI
            
        Returns:
            str: 脱敏后的SIP URI
        """
        # 脱敏URI中的密码部分
        return re.sub(r'(sips?://[^:]*:)([^@]*)@', r'\1[HIDDEN]@', uri)


class SecureSIPMessageBuilder:
    """
    安全的SIP消息构建器
    在构建SIP消息时确保安全性
    """
    
    def __init__(self, secure_logger: Optional[SecureSIPLogger] = None):
        """
        初始化安全SIP消息构建器
        
        Args:
            secure_logger: 安全日志记录器
        """
        self.secure_logger = secure_logger or SecureSIPLogger()
    
    def create_secure_register_message(self, username: str, domain: str, local_host: str, local_port: int, 
                                     server_host: str, server_port: int, expires: int = 3600) -> str:
        """
        创建安全的REGISTER请求消息
        不在日志中暴露密码等敏感信息
        
        Args:
            username: 用户名
            domain: 域名
            local_host: 本地主机
            local_port: 本地端口
            server_host: 服务器主机
            server_port: 服务器端口
            expires: 过期时间
            
        Returns:
            str: REGISTER请求消息
        """
        import time
        import random
        
        call_id = f"{int(time.time())}.{random.randint(10000, 99999)}"
        branch = f"z9hG4bK{int(time.time() * 1000000)}{random.randint(1000, 9999)}"
        from_tag = f"tag{int(time.time() * 1000)}"
        
        # 确保expires值在合理范围内
        normalized_expires = min(max(expires, 0), 3600)
        
        # 构建REGISTER请求
        message = (
            f"REGISTER sip:{domain} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_host}:{local_port};branch={branch};rport\r\n"
            f"From: <sip:{username}@{domain}>;tag={from_tag}\r\n"
            f"To: <sip:{username}@{domain}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 REGISTER\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: Secure AutoTestForUG SIP Client 1.0\r\n"
            f"Contact: <sip:{username}@{local_host}:{local_port}>\r\n"
            f"Expires: {normalized_expires}\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        # 记录日志但不包含敏感信息
        self.secure_logger.info(f"创建安全的REGISTER消息，用户: {username}, 域: {domain}")
        
        return message
    
    def create_secure_invite_message(self, caller_uri: str, callee_uri: str, local_host: str, local_port: int,
                                   server_host: str, server_port: int) -> str:
        """
        创建安全的INVITE请求消息
        
        Args:
            caller_uri: 主叫URI
            callee_uri: 被叫URI
            local_host: 本地主机
            local_port: 本地端口
            server_host: 服务器主机
            server_port: 服务器端口
            
        Returns:
            str: INVITE请求消息
        """
        import time
        import random
        
        call_id = f"{int(time.time())}.{random.randint(10000, 99999)}"
        branch = f"z9hG4bK{int(time.time() * 1000000)}{random.randint(1000, 9999)}"
        from_tag = f"tag{int(time.time() * 1000)}"
        
        # 基本SDP内容
        sdp_content = (
            "v=0\r\n"
            "o=- {timestamp} {timestamp} IN IP4 {local_host}\r\n"
            "s=Secure AutoTestForUG Call\r\n"
            "c=IN IP4 {local_host}\r\n"
            "t=0 0\r\n"
            "m=audio {local_port} RTP/AVP 0 8 101\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
            "a=rtpmap:8 PCMA/8000\r\n"
            "a=rtpmap:101 telephone-event/8000\r\n"
            "a=sendrecv\r\n"
        ).format(timestamp=int(time.time()), local_host=local_host, local_port=local_port+1000)
        
        message = (
            f"INVITE {callee_uri} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_host}:{local_port};branch={branch};rport\r\n"
            f"From: <{caller_uri}>;tag={from_tag}\r\n"
            f"To: <{callee_uri}>\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: Secure AutoTestForUG SIP Client 1.0\r\n"
            f"Contact: <{caller_uri}>\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp_content)}\r\n"
            f"\r\n"
            f"{sdp_content}"
        )
        
        # 记录日志但不包含敏感信息
        sanitized_caller = SecurityUtils.sanitize_sip_uri(caller_uri)
        sanitized_callee = SecurityUtils.sanitize_sip_uri(callee_uri)
        self.secure_logger.info(f"创建安全的INVITE消息，主叫: {sanitized_caller}, 被叫: {sanitized_callee}")
        
        return message


# 全局安全凭据管理器实例
secure_credential_manager = SecureCredentialManager()

# 全局安全日志记录器实例
secure_sip_logger = SecureSIPLogger()