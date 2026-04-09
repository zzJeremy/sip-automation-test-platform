#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试认证过程脚本
用于深入分析SIP认证过程中的问题
"""

import hashlib
import re
import time
import logging
import socket
import random
from typing import Optional

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class DebugSIPAuth:
    """调试SIP认证过程的工具类"""
    
    @staticmethod
    def calculate_digest_auth(username: str, password: str, realm: str, nonce: str, 
                            method: str, uri: str, qop: str = None, nc: str = None, 
                            cnonce: str = None) -> str:
        """
        计算SIP摘要认证的响应值
        """
        print(f"开始计算摘要认证:")
        print(f"  用户名: {username}")
        print(f"  密码: {password}")
        print(f"  realm: {realm}")
        print(f"  nonce: {nonce}")
        print(f"  方法: {method}")
        print(f"  URI: {uri}")
        print(f"  qop: {qop}")
        print(f"  nc: {nc}")
        print(f"  cnonce: {cnonce}")
        
        # HA1 = MD5(username:realm:password)
        ha1_input = f"{username}:{realm}:{password}"
        ha1 = hashlib.md5(ha1_input.encode()).hexdigest()
        print(f"  HA1({ha1_input}): {ha1}")
        
        # HA2 = MD5(method:digestURI)
        ha2_input = f"{method}:{uri}"
        ha2 = hashlib.md5(ha2_input.encode()).hexdigest()
        print(f"  HA2({ha2_input}): {ha2}")
        
        if qop and qop.lower() == 'auth':
            # Response = MD5(HA1:nonce:nc:cnonce:qop:HA2)
            response_input = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
            print(f"  Response输入({response_input}):")
        else:
            # Response = MD5(HA1:nonce:HA2)
            response_input = f"{ha1}:{nonce}:{ha2}"
            print(f"  Response输入({response_input}):")
        
        response = hashlib.md5(response_input.encode()).hexdigest()
        print(f"  最终响应值: {response}")
        
        return response
    
    @staticmethod
    def parse_auth_header(auth_header: str) -> dict:
        """
        解析认证头信息
        """
        print(f"解析认证头: {auth_header}")
        auth_params = {}
        
        patterns = [
            r'realm="([^"]+)"',
            r'nonce="([^"]+)"',
            r'opaque="([^"]*)"',  # 可选参数
            r'algorithm=([A-Z0-9]+)',
            r'qop="([^"]+)"'  # 质询选项
        ]
        
        for pattern in patterns:
            match = re.search(pattern, auth_header, re.IGNORECASE)
            if match:
                if 'realm' in pattern:
                    auth_params['realm'] = match.group(1)
                elif 'nonce' in pattern:
                    auth_params['nonce'] = match.group(1)
                elif 'opaque' in pattern:
                    auth_params['opaque'] = match.group(1) if match.group(1) else ''
                elif 'algorithm' in pattern:
                    auth_params['algorithm'] = match.group(1)
                elif 'qop' in pattern:
                    auth_params['qop'] = match.group(1)
        
        print(f"解析结果: {auth_params}")
        return auth_params


def main():
    """主函数 - 手动计算认证值进行验证"""
    print("=" * 60)
    print("SIP认证过程调试工具")
    print("=" * 60)
    
    # 使用测试数据
    username = "100010"
    password = "1234"
    realm = "192.168.30.66"
    nonce = "ccf39c2f-799f-4344-9945-e0183bec4be8"  # 从日志中获取的示例值
    method = "INVITE"
    uri = "sip:670009@192.168.30.66:5060"
    qop = "auth"
    nc = "00000001"
    cnonce = "80779396"
    
    print(f"测试认证计算...")
    response = DebugSIPAuth.calculate_digest_auth(
        username=username,
        password=password,
        realm=realm,
        nonce=nonce,
        method=method,
        uri=uri,
        qop=qop,
        nc=nc,
        cnonce=cnonce
    )
    
    print(f"\n计算得到的响应值: {response}")
    print("该值应该与服务器期望的一致才能通过认证")
    
    print("\n" + "=" * 60)
    print("认证调试完成")
    print("如果认证仍然失败，请检查以下几点：")
    print("1. 用户名和密码是否正确")
    print("2. 服务器是否允许该用户发起呼叫")
    print("3. 服务器的认证配置是否与客户端匹配")
    print("4. 是否需要特殊配置（如IP白名单等）")
    print("=" * 60)


if __name__ == "__main__":
    main()