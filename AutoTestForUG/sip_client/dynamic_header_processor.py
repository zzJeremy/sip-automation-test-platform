"""
动态头字段处理器模块
解析和生成动态头字段，支持从响应中提取信息并用于后续请求
"""
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import json
import base64
from urllib.parse import urlparse, parse_qs


@dataclass
class SIPHeader:
    """SIP头字段数据类"""
    name: str
    value: str
    params: Dict[str, str] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


class DynamicHeaderProcessor:
    """
    动态头字段处理器，用于解析和生成SIP头字段
    支持从响应中提取信息并用于后续请求
    """
    
    def __init__(self):
        self.header_extractors = {}  # 提取器注册表
        self.header_generators = {}  # 生成器注册表
        self.variable_store = {}  # 变量存储
        self.response_history = []  # 响应历史
        self.register_default_extractors()
        self.register_default_generators()
    
    def register_default_extractors(self):
        """注册默认的头字段提取器"""
        self.header_extractors.update({
            'call-id': self._extract_call_id,
            'from-tag': self._extract_from_tag,
            'to-tag': self._extract_to_tag,
            'cseq': self._extract_cseq,
            'via-branch': self._extract_via_branch,
            'contact-uri': self._extract_contact_uri,
            'authorization': self._extract_authorization,
            'www-authenticate': self._extract_www_authenticate,
            'proxy-authenticate': self._extract_proxy_authenticate,
            'p-asserted-identity': self._extract_p_asserted_identity,
            'diversion': self._extract_diversion,
            'x-forwarded-for': self._extract_x_forwarded_for,
        })
    
    def register_default_generators(self):
        """注册默认的头字段生成器"""
        self.header_generators.update({
            'call-id': self._generate_call_id,
            'cseq': self._generate_cseq,
            'via': self._generate_via,
            'from': self._generate_from,
            'to': self._generate_to,
            'contact': self._generate_contact,
            'authorization': self._generate_authorization,
        })
    
    def register_extractor(self, header_name: str, extractor_func: Callable):
        """注册自定义头字段提取器"""
        self.header_extractors[header_name.lower()] = extractor_func
    
    def register_generator(self, header_name: str, generator_func: Callable):
        """注册自定义头字段生成器"""
        self.header_generators[header_name.lower()] = generator_func
    
    def extract_headers_from_response(self, response: str) -> Dict[str, Any]:
        """
        从SIP响应中提取头字段
        
        Args:
            response: SIP响应字符串
            
        Returns:
            提取的头字段字典
        """
        headers = {}
        lines = response.split('\r\n')
        
        # 跳过状态行
        start_idx = 1 if lines[0].startswith('SIP/') else 0
        
        for line in lines[start_idx:]:
            if ':' in line:
                header_name, header_value = line.split(':', 1)
                header_name = header_name.strip().lower()
                header_value = header_value.strip()
                
                headers[header_name] = header_value
                
                # 如果有对应的提取器，执行提取
                if header_name in self.header_extractors:
                    extracted = self.header_extractors[header_name](header_value)
                    if extracted is not None:
                        headers[f'{header_name}_extracted'] = extracted
        
        return headers
    
    def extract_specific_header(self, response: str, header_name: str) -> Optional[str]:
        """
        从SIP响应中提取特定头字段
        
        Args:
            response: SIP响应字符串
            header_name: 头字段名称
            
        Returns:
            头字段值，如果不存在则返回None
        """
        lines = response.split('\r\n')
        header_name_lower = header_name.lower()
        
        for line in lines:
            if ':' in line:
                name, value = line.split(':', 1)
                if name.strip().lower() == header_name_lower:
                    return value.strip()
        
        return None
    
    def _extract_call_id(self, header_value: str) -> Optional[str]:
        """提取Call-ID"""
        return header_value.strip()
    
    def _extract_from_tag(self, header_value: str) -> Optional[str]:
        """从From头字段提取tag"""
        match = re.search(r'tag=([^;\s]+)', header_value)
        return match.group(1) if match else None
    
    def _extract_to_tag(self, header_value: str) -> Optional[str]:
        """从To头字段提取tag"""
        match = re.search(r'tag=([^;\s]+)', header_value)
        return match.group(1) if match else None
    
    def _extract_cseq(self, header_value: str) -> Optional[Dict[str, Any]]:
        """提取CSeq信息"""
        parts = header_value.strip().split()
        if len(parts) >= 2:
            return {
                'number': int(parts[0]),
                'method': parts[1]
            }
        return None
    
    def _extract_via_branch(self, header_value: str) -> Optional[str]:
        """从Via头字段提取branch"""
        match = re.search(r'branch=([^;\s]+)', header_value)
        return match.group(1) if match else None
    
    def _extract_contact_uri(self, header_value: str) -> Optional[str]:
        """从Contact头字段提取URI"""
        # 移除参数部分，只保留URI
        uri_match = re.search(r'<([^>]+)>|([^;,\s]+)', header_value)
        if uri_match:
            uri = uri_match.group(1) or uri_match.group(2)
            return uri.strip()
        return None
    
    def _extract_authorization(self, header_value: str) -> Optional[Dict[str, str]]:
        """提取Authorization信息"""
        auth_params = {}
        # 解析类似这样的字符串: Digest username="user", realm="realm", ...
        pattern = r'(\w+)=("([^"]+)"|([^,\s]+))'
        matches = re.findall(pattern, header_value)
        
        for key, _, quoted_val, unquoted_val in matches:
            value = quoted_val if quoted_val else unquoted_val
            auth_params[key.lower()] = value
        
        return auth_params
    
    def _extract_www_authenticate(self, header_value: str) -> Optional[Dict[str, str]]:
        """提取WWW-Authenticate信息"""
        return self._extract_authorization(header_value)
    
    def _extract_proxy_authenticate(self, header_value: str) -> Optional[Dict[str, str]]:
        """提取Proxy-Authenticate信息"""
        return self._extract_authorization(header_value)
    
    def _extract_p_asserted_identity(self, header_value: str) -> Optional[str]:
        """提取P-Asserted-Identity"""
        return header_value.strip()
    
    def _extract_diversion(self, header_value: str) -> Optional[str]:
        """提取Diversion信息"""
        return header_value.strip()
    
    def _extract_x_forwarded_for(self, header_value: str) -> Optional[str]:
        """提取X-Forwarded-For"""
        return header_value.strip()
    
    def store_response(self, response: str, context: str = None):
        """存储响应以供后续处理"""
        self.response_history.append({
            'response': response,
            'context': context,
            'timestamp': __import__('time').time(),
            'extracted_headers': self.extract_headers_from_response(response)
        })
    
    def get_stored_value(self, key: str) -> Optional[Any]:
        """获取存储的值"""
        return self.variable_store.get(key)
    
    def set_stored_value(self, key: str, value: Any):
        """设置存储的值"""
        self.variable_store[key] = value
    
    def get_latest_response_header(self, header_name: str) -> Optional[str]:
        """获取最新响应中的指定头字段"""
        if not self.response_history:
            return None
        
        latest_response = self.response_history[-1]['response']
        return self.extract_specific_header(latest_response, header_name)
    
    def generate_request_with_dynamic_headers(self, template_request: str, 
                                           context: Dict[str, Any] = None) -> str:
        """
        使用动态头字段生成请求
        
        Args:
            template_request: 请求模板，可能包含变量
            context: 上下文信息
            
        Returns:
            生成的请求字符串
        """
        if context is None:
            context = {}
        
        # 替换模板中的变量
        request = template_request
        
        # 支持的变量格式: {{variable_name}} 或 ${variable_name}
        variable_pattern = r'\{\{(\w+)\}\}|\$\{(\w+)\}'
        
        def replace_variable(match):
            var_name = match.group(1) or match.group(2)
            
            # 从上下文获取值
            if var_name in context:
                return str(context[var_name])
            
            # 从变量存储获取值
            stored_value = self.get_stored_value(var_name)
            if stored_value is not None:
                return str(stored_value)
            
            # 从最新响应获取值
            if var_name.startswith('latest_'):
                header_name = var_name[7:]  # 移除'latest_'前缀
                header_value = self.get_latest_response_header(header_name)
                if header_value:
                    return header_value
            
            # 如果没有找到值，保持原样
            return match.group(0)
        
        import re
        request = re.sub(variable_pattern, replace_variable, request)
        
        return request
    
    def _generate_call_id(self, context: Dict[str, Any] = None) -> str:
        """生成Call-ID"""
        import uuid
        return f"{uuid.uuid4()}@{context.get('local_host', 'localhost')}"
    
    def _generate_cseq(self, context: Dict[str, Any] = None) -> str:
        """生成CSeq"""
        cseq_num = context.get('cseq', 1) if context else 1
        method = context.get('method', 'INVITE') if context else 'INVITE'
        return f"{cseq_num} {method}"
    
    def _generate_via(self, context: Dict[str, Any] = None) -> str:
        """生成Via头字段"""
        if context is None:
            context = {}
        
        protocol = context.get('transport', 'UDP')
        host = context.get('local_host', '127.0.0.1')
        port = context.get('local_port', '5060')
        branch = f"z9hG4bK{__import__('time').time()}_{__import__('random').randint(1000, 9999)}"
        
        return f"SIP/2.0/{protocol} {host}:{port};branch={branch}"
    
    def _generate_from(self, context: Dict[str, Any] = None) -> str:
        """生成From头字段"""
        if context is None:
            context = {}
        
        uri = context.get('from_uri', 'sip:user@localhost')
        tag = context.get('from_tag', f"tag{__import__('time').time()}")
        
        return f'"{context.get("from_display_name", "User")}" <{uri}>;tag={tag}'
    
    def _generate_to(self, context: Dict[str, Any] = None) -> str:
        """生成To头字段"""
        if context is None:
            context = {}
        
        uri = context.get('to_uri', 'sip:user@localhost')
        tag = context.get('to_tag')  # To头通常没有tag，除非是响应
        
        result = f'"{context.get("to_display_name", "User")}" <{uri}>'
        if tag:
            result += f';tag={tag}'
        
        return result
    
    def _generate_contact(self, context: Dict[str, Any] = None) -> str:
        """生成Contact头字段"""
        if context is None:
            context = {}
        
        uri = f"sip:{context.get('contact_user', 'user')}@{context.get('contact_host', 'localhost')}:{context.get('contact_port', '5060')}"
        expires = context.get('expires', 3600)
        
        return f'<{uri}>;expires={expires}'
    
    def _generate_authorization(self, context: Dict[str, Any] = None) -> Optional[str]:
        """生成Authorization头字段"""
        if context is None:
            context = {}
        
        # 检查是否有认证所需的信息
        if not all(k in context for k in ['username', 'realm', 'password', 'method', 'uri']):
            return None
        
        import hashlib
        
        username = context['username']
        realm = context['realm']
        password = context['password']
        method = context['method']
        uri = context['uri']
        nonce = context.get('nonce', '')
        qop = context.get('qop', '')
        cnonce = context.get('cnonce', '')
        nc = context.get('nc', '00000001')
        
        # 计算HA1
        a1 = f"{username}:{realm}:{password}"
        ha1 = hashlib.md5(a1.encode()).hexdigest()
        
        # 计算HA2
        a2 = f"{method}:{uri}"
        ha2 = hashlib.md5(a2.encode()).hexdigest()
        
        # 计算响应
        if qop:
            to_hash = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
        else:
            to_hash = f"{ha1}:{nonce}:{ha2}"
        
        response = hashlib.md5(to_hash.encode()).hexdigest()
        
        # 构建Authorization头
        auth_parts = [
            f'username="{username}"',
            f'realm="{realm}"',
            f'nonce="{nonce}"',
            f'uri="{uri}"',
            f'response="{response}"',
            'algorithm=MD5'
        ]
        
        if qop:
            auth_parts.extend([f'qop={qop}', f'nc={nc}', f'cnonce="{cnonce}"'])
        
        return f'Digest {",".join(auth_parts)}'
    
    def generate_header(self, header_name: str, context: Dict[str, Any] = None) -> Optional[str]:
        """
        生成指定的头字段
        
        Args:
            header_name: 头字段名称
            context: 上下文信息
            
        Returns:
            生成的头字段值，如果无法生成则返回None
        """
        generator = self.header_generators.get(header_name.lower())
        if generator:
            return generator(context)
        return None
    
    def process_request_template(self, template: str, response_context: Dict[str, Any] = None) -> str:
        """
        处理请求模板，将响应中的信息用于生成新的请求
        
        Args:
            template: 请求模板
            response_context: 响应上下文，包含从先前响应中提取的信息
            
        Returns:
            处理后的请求
        """
        if response_context is None:
            response_context = {}
        
        # 合并变量存储和响应上下文
        full_context = {**self.variable_store, **response_context}
        
        return self.generate_request_with_dynamic_headers(template, full_context)
    
    def parse_sdp(self, sdp_body: str) -> Dict[str, Any]:
        """
        解析SDP内容
        
        Args:
            sdp_body: SDP内容
            
        Returns:
            解析后的SDP信息字典
        """
        sdp_info = {
            'session': {},
            'media': []
        }
        
        lines = sdp_body.split('\r\n')
        
        current_media = None
        for line in lines:
            if not line.strip():
                continue
                
            if '=' in line:
                prefix, content = line[0], line[2:]
                
                if prefix == 'm':  # 媒体行
                    current_media = {
                        'type': content.split()[0],
                        'port': content.split()[1],
                        'protocol': content.split()[2],
                        'formats': content.split()[3:],
                        'attributes': []
                    }
                    sdp_info['media'].append(current_media)
                elif prefix == 'a':  # 属性行
                    if current_media is not None:
                        current_media['attributes'].append(content)
                    else:
                        sdp_info['session'].setdefault('attributes', []).append(content)
                else:  # 其他会话级行
                    sdp_info['session'][prefix] = content
        
        return sdp_info
    
    def update_context_with_sdp(self, sdp_info: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用SDP信息更新上下文
        
        Args:
            sdp_info: 解析后的SDP信息
            context: 当前上下文
            
        Returns:
            更新后的上下文
        """
        # 提取会话级信息
        session = sdp_info.get('session', {})
        if 'o' in session:  # Origin字段
            origin_parts = session['o'].split()
            if len(origin_parts) >= 2:
                context['sdp_session_id'] = origin_parts[1]
        
        # 提取媒体信息
        media_list = sdp_info.get('media', [])
        if media_list:
            first_media = media_list[0]
            context['media_type'] = first_media.get('type', '')
            context['media_port'] = first_media.get('port', '')
            context['media_protocol'] = first_media.get('protocol', '')
            
            # 提取属性
            for attr in first_media.get('attributes', []):
                if attr.startswith('rtpmap:'):
                    # 解析rtpmap属性: rtpmap:0 PCMU/8000
                    parts = attr.split()
                    if len(parts) >= 2:
                        rtpmap_parts = parts[0].split(':')
                        if len(rtpmap_parts) >= 2:
                            payload_type = rtpmap_parts[1]
                            codec_info = parts[1]
                            context['codec'] = codec_info
                            context['payload_type'] = payload_type
        
        return context


# 使用示例
if __name__ == "__main__":
    processor = DynamicHeaderProcessor()
    
    # 示例SIP响应
    response = """SIP/2.0 200 OK\r
Via: SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bK12345\r
From: "Alice" <sip:alice@domain.com>;tag=12345\r
To: "Bob" <sip:bob@domain.com>;tag=67890\r
Call-ID: abcdef12345@127.0.0.1\r
CSeq: 1 INVITE\r
Contact: <sip:bob@192.168.1.100:5060>\r
Content-Length: 0\r\n\r"""
    
    # 存储响应
    processor.store_response(response, "INVITE_response")
    
    # 提取头字段
    headers = processor.extract_headers_from_response(response)
    print("Extracted headers:", headers)
    
    # 获取特定头字段
    call_id = processor.get_latest_response_header('Call-ID')
    print("Call-ID from response:", call_id)
    
    # 示例请求模板
    request_template = """INVITE sip:{{to_uri}} SIP/2.0\r
Via: {{via}}\r
From: {{from}}\r
To: {{to}}\r
Call-ID: {{call_id}}\r
CSeq: {{cseq}}\r
Contact: {{contact}}\r
Content-Type: application/sdp\r
Content-Length: {{content_length}}\r\n\r
{{sdp_body}}"""
    
    # 生成请求上下文
    context = {
        'to_uri': 'bob@domain.com',
        'via': 'SIP/2.0/UDP 127.0.0.1:5061;branch=z9hG4bKnew123',
        'from': '"Alice" <sip:alice@domain.com>;tag=new123',
        'to': '"Bob" <sip:bob@domain.com>',
        'call_id': call_id,  # 使用从响应中提取的Call-ID
        'cseq': '2 INVITE',
        'contact': '<sip:alice@127.0.0.1:5061>',
        'content_length': '0',
        'sdp_body': ''
    }
    
    # 生成请求
    generated_request = processor.generate_request_with_dynamic_headers(request_template, context)
    print("Generated request:", generated_request)