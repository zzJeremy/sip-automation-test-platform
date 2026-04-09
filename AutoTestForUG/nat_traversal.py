"""
NAT穿越功能实现
包括STUN客户端和相关网络地址转换处理
"""

import socket
import struct
import random
import time
from typing import Tuple, Optional


class STUNClient:
    """
    STUN客户端实现，用于NAT穿越
    符合RFC 3489和RFC 5389标准
    """
    
    # STUN消息类型
    BINDING_REQUEST = 0x0001
    BINDING_RESPONSE = 0x0101
    
    # STUN属性类型
    MAPPED_ADDRESS = 0x0001
    RESPONSE_ADDRESS = 0x0002
    CHANGE_REQUEST = 0x0003
    SOURCE_ADDRESS = 0x0004
    CHANGED_ADDRESS = 0x0005
    USERNAME = 0x0006
    PASSWORD = 0x0007
    MESSAGE_INTEGRITY = 0x0008
    ERROR_CODE = 0x0009
    UNKNOWN_ATTRIBUTES = 0x000a
    REFLECTED_FROM = 0x000b
    XOR_MAPPED_ADDRESS = 0x0020
    XOR_ONLY = 0x0021
    SERVER = 0x8022
    
    def __init__(self, stun_server: str = "stun.l.google.com", stun_port: int = 19302):
        self.stun_server = stun_server
        self.stun_port = stun_port
    
    def create_binding_request(self) -> bytes:
        """
        创建STUN绑定请求
        """
        # 消息类型(绑定请求) + 消息长度 + 事务ID
        msg_type = self.BINDING_REQUEST
        msg_len = 0  # 无属性
        transaction_id = b''.join([struct.pack('!H', random.randint(0, 0xFFFF)) for _ in range(4)])
        
        # 构建消息头
        msg_header = struct.pack('!HH16s', msg_type, msg_len, transaction_id)
        return msg_header
    
    def parse_response(self, data: bytes) -> dict:
        """
        解析STUN响应
        """
        if len(data) < 20:
            raise ValueError("Invalid STUN response")
        
        # 解析消息头
        msg_type, msg_len = struct.unpack('!HH', data[:4])
        transaction_id = data[4:20]
        
        if msg_type != self.BINDING_RESPONSE:
            raise ValueError(f"Invalid response type: {msg_type:#x}")
        
        # 解析属性
        attributes = {}
        offset = 20
        
        while offset < len(data):
            if offset + 4 > len(data):
                break
                
            attr_type, attr_len = struct.unpack('!HH', data[offset:offset+4])
            offset += 4
            
            if offset + attr_len > len(data):
                break
                
            attr_value = data[offset:offset+attr_len]
            offset += attr_len
            
            # 对齐到4字节边界
            offset = (offset + 3) & ~3
            
            attributes[attr_type] = attr_value
        
        # 解析映射地址
        mapped_address = None
        if self.MAPPED_ADDRESS in attributes:
            mapped_address = self._parse_address(attributes[self.MAPPED_ADDRESS])
        elif self.XOR_MAPPED_ADDRESS in attributes:
            mapped_address = self._xor_parse_address(attributes[self.XOR_MAPPED_ADDRESS], transaction_id)
        
        return {
            'mapped_address': mapped_address,
            'transaction_id': transaction_id.hex()
        }
    
    def _parse_address(self, data: bytes) -> Tuple[str, int]:
        """
        解析地址属性
        """
        if len(data) < 8:
            raise ValueError("Invalid address attribute")
        
        reserved, family, port = struct.unpack('!BBH', data[:4])
        ip_bytes = data[4:8]
        ip = '.'.join(str(b) for b in ip_bytes)
        
        return (ip, port)
    
    def _xor_parse_address(self, data: bytes, transaction_id: bytes) -> Tuple[str, int]:
        """
        解析XOR映射地址属性
        """
        if len(data) < 8:
            raise ValueError("Invalid XOR address attribute")
        
        reserved, family, xor_port = struct.unpack('!BBH', data[:4])
        xor_ip = data[4:8]
        
        # XOR操作还原真实地址
        port = xor_port ^ 0x2112  # STUN魔数的前16位
        
        magic_cookie = b'\x21\x12\xa4\x42'
        combined = magic_cookie + transaction_id
        ip_parts = []
        for i in range(4):
            xor_byte = xor_ip[i]
            real_byte = xor_byte ^ combined[i]
            ip_parts.append(real_byte)
        
        ip = '.'.join(str(part) for part in ip_parts)
        return (ip, port)
    
    def get_mapped_address(self) -> Optional[Tuple[str, int]]:
        """
        获取映射地址
        """
        try:
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            
            # 发送绑定请求
            request = self.create_binding_request()
            sock.sendto(request, (self.stun_server, self.stun_port))
            
            # 接收响应
            response, server_addr = sock.recvfrom(1024)
            sock.close()
            
            # 解析响应
            result = self.parse_response(response)
            return result.get('mapped_address')
        
        except Exception as e:
            print(f"STUN请求失败: {e}")
            return None


def enable_nat_traversal(sip_client):
    """
    为SIP客户端启用NAT穿越功能
    """
    # 获取公共IP和端口
    stun_client = STUNClient()
    public_addr = stun_client.get_mapped_address()
    
    if public_addr:
        public_ip, public_port = public_addr
        print(f"NAT穿越检测成功: {public_ip}:{public_port}")
        
        # 更新SIP客户端的联系地址
        original_create_contact = getattr(sip_client, 'create_contact_header', None)
        
        def create_contact_with_nat():
            # 使用公共地址作为Contact头
            return f"<sip:{public_ip}:{public_port}>"
        
        if original_create_contact:
            setattr(sip_client, '_original_create_contact', original_create_contact)
        
        setattr(sip_client, 'create_contact_header', create_contact_with_nat)
        
        # 更新客户端属性
        sip_client.nat_public_ip = public_ip
        sip_client.nat_public_port = public_port
        sip_client.has_nat_traversal = True
        
        return True
    else:
        print("NAT穿越检测失败，继续使用本地地址")
        sip_client.has_nat_traversal = False
        return False


def update_via_header_for_nat(via_header: str, public_ip: str = None, public_port: int = None) -> str:
    """
    为NAT环境更新Via头
    """
    if not public_ip or not public_port:
        return via_header
    
    # 替换Via头中的地址信息
    lines = via_header.split('\r\n')
    updated_lines = []
    
    for line in lines:
        if line.startswith('Via:') or line.startswith('v:'):
            # 更新传输地址
            if ';' in line:
                parts = line.split(';')
                main_part = parts[0]
                params = ';'.join(parts[1:])
                
                # 在参数中添加received和rport信息
                if f'{public_ip}:{public_port}' in main_part:
                    updated_line = line
                else:
                    # 替换地址部分
                    prefix = main_part.split()[0]  # SIP/2.0/UDP
                    updated_main = f"{prefix} {public_ip}:{public_port}"
                    updated_line = f"{updated_main};{params}"
                    
                    # 添加received和rport参数
                    if 'received=' not in updated_line:
                        updated_line += f';received={public_ip}'
                    if 'rport=' not in updated_line and public_port:
                        updated_line += f';rport={public_port}'
            else:
                updated_line = line
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)
    
    return '\r\n'.join(updated_lines)


def create_nat_compatible_sip_message(original_message: str, public_ip: str = None, public_port: int = None) -> str:
    """
    创建兼容NAT的SIP消息
    """
    if not public_ip or not public_port:
        return original_message
    
    # 分离头部和主体
    parts = original_message.split('\r\n\r\n', 1)
    headers = parts[0]
    body = parts[1] if len(parts) > 1 else ""
    
    # 更新Via头
    updated_headers = update_via_header_for_nat(headers, public_ip, public_port)
    
    # 如果有Contact头，也进行更新
    header_lines = updated_headers.split('\r\n')
    final_headers = []
    for line in header_lines:
        if line.startswith('Contact:') or line.startswith('m:'):
            # 更新Contact头为公共地址
            if public_ip and public_port:
                # 简单替换Contact地址
                if '<sip:' in line and '>' in line:
                    start_idx = line.find('<sip:')
                    end_idx = line.find('>', start_idx)
                    if start_idx != -1 and end_idx != -1:
                        original_contact = line[start_idx:end_idx+1]
                        # 提取用户名部分
                        sip_prefix = original_contact[:original_contact.find('@')+1]
                        new_contact = f"{sip_prefix}{public_ip}:{public_port}>"
                        updated_line = line.replace(original_contact, new_contact)
                        final_headers.append(updated_line)
                    else:
                        final_headers.append(line)
                else:
                    final_headers.append(line)
            else:
                final_headers.append(line)
        else:
            final_headers.append(line)
    
    final_message = '\r\n'.join(final_headers)
    if body:
        final_message += '\r\n\r\n' + body
    
    return final_message


# 示例用法
if __name__ == "__main__":
    # 测试STUN客户端
    stun = STUNClient()
    mapped_addr = stun.get_mapped_address()
    
    if mapped_addr:
        print(f"映射地址: {mapped_addr[0]}:{mapped_addr[1]}")
    else:
        print("无法获取映射地址")