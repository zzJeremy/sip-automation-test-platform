#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIP 482错误处理增强模块
提供改进的SIP消息处理和482错误预防机制
"""

import socket
import time
import logging
import hashlib
import random
from urllib.parse import urlparse
import configparser

class SIP482Handler:
    def __init__(self):
        # 存储活跃的Call-ID以避免重复
        self.active_call_ids = set()
        self.call_history = {}  # 存储呼叫历史以避免重复请求
        
        # 设置日志
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def generate_unique_call_params(self):
        """生成唯一的呼叫参数以避免冲突"""
        timestamp = int(time.time())
        random_suffix = random.randint(100000, 999999)
        
        call_id = f"{timestamp}.{random_suffix}@{self.local_host}"
        branch = f"z9hG4bK{timestamp}{random_suffix}"
        from_tag = f"tag{timestamp}{random_suffix}"
        
        return call_id, branch, from_tag
    
    def is_call_id_active(self, call_id):
        """检查Call-ID是否活跃以避免重复"""
        return call_id in self.active_call_ids
    
    def register_call_id(self, call_id):
        """注册新的Call-ID"""
        self.active_call_ids.add(call_id)
        self.call_history[call_id] = {
            'timestamp': time.time(),
            'status': 'active'
        }
    
    def unregister_call_id(self, call_id):
        """注销Call-ID"""
        if call_id in self.active_call_ids:
            self.active_call_ids.remove(call_id)
            if call_id in self.call_history:
                self.call_history[call_id]['status'] = 'completed'
                self.call_history[call_id]['end_time'] = time.time()
    
    def detect_loop_patterns(self, response):
        """检测可能的循环模式"""
        # 检查响应中是否有循环检测相关的信息
        if '482' in response or 'Loop' in response or 'Merged' in response:
            self.logger.warning("检测到可能的循环或合并请求模式")
            return True
        return False
    
    def handle_482_error(self, sock, caller_uri, callee_uri, original_params):
        """处理482错误的特殊逻辑"""
        self.logger.info("处理482错误 - 尝试使用新参数重新发送请求")
        
        # 生成新的唯一参数
        new_call_id, new_branch, new_from_tag = self.generate_unique_call_params()
        
        # 检查新Call-ID是否已经存在
        attempts = 0
        while self.is_call_id_active(new_call_id) and attempts < 5:
            new_call_id, new_branch, new_from_tag = self.generate_unique_call_params()
            attempts += 1
        
        if attempts >= 5:
            self.logger.error("无法生成唯一的Call-ID，可能系统中存在太多活跃请求")
            return False
        
        # 使用新参数重新构建请求
        # 这里需要根据具体的请求类型重新构建消息
        # 由于我们不知道原始请求类型，我们返回新参数供调用者使用
        return {
            'call_id': new_call_id,
            'branch': new_branch,
            'from_tag': new_from_tag
        }
    
    def safe_send_request(self, sock, message, server_addr, max_retries=3):
        """安全发送SIP请求，处理可能的错误"""
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"发送SIP请求 (尝试 {attempt + 1}): {message.split()[0] if message.split() else 'UNKNOWN'}")
                sock.sendto(message.encode('utf-8'), server_addr)
                
                response_data, response_addr = sock.recvfrom(4096)
                response_str = response_data.decode('utf-8')
                
                # 检查是否为482错误
                if self.detect_loop_patterns(response_str):
                    self.logger.warning(f"收到482响应 (尝试 {attempt + 1})，准备重试")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # 等待一段时间再重试
                        continue
                    else:
                        self.logger.error("达到最大重试次数，仍收到482错误")
                        return response_str, False  # 返回响应和失败标志
                
                return response_str, True  # 返回响应和成功标志
                
            except socket.timeout:
                self.logger.warning(f"请求超时 (尝试 {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 等待更长时间再重试
                    continue
                else:
                    self.logger.error("达到最大重试次数，请求超时")
                    return "TIMEOUT", False
            except Exception as e:
                self.logger.error(f"发送请求时出错 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return f"ERROR: {e}", False
        
        return "MAX_RETRIES_EXCEEDED", False

# 在SIPTestClient中集成482处理逻辑的示例
def integrate_482_handling_in_client():
    """
    这个函数展示了如何将482处理逻辑集成到SIPTestClient中
    """
    print("482处理逻辑集成示例:")
    print("1. 在发送每个SIP请求前生成唯一参数")
    print("2. 跟踪活跃的Call-ID以避免冲突") 
    print("3. 检测482错误并自动重试")
    print("4. 实现适当的延迟以避免触发循环检测")
    
    # 示例伪代码
    example_code = '''
# 在SIPTestClient中添加482处理
class EnhancedSIPTestClient(SIPTestClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sip_482_handler = SIP482Handler()
    
    def make_call_with_482_handling(self, caller_uri, callee_uri, duration=10):
        # 生成唯一参数
        call_id, branch, from_tag = self.sip_482_handler.generate_unique_call_params()
        
        # 检查Call-ID是否活跃
        if self.sip_482_handler.is_call_id_active(call_id):
            self.logger.warning("Call-ID已存在，生成新参数")
            call_id, branch, from_tag = self.sip_482_handler.generate_unique_call_params()
        
        # 注册Call-ID
        self.sip_482_handler.register_call_id(call_id)
        
        try:
            # 使用安全发送方法
            response, success = self.sip_482_handler.safe_send_request(
                sock, invite_message, (self.sip_server_host, self.sip_server_port)
            )
            
            if not success and "482" in response:
                # 处理482错误
                new_params = self.sip_482_handler.handle_482_error(
                    sock, caller_uri, callee_uri, {'call_id': call_id}
                )
                if new_params:
                    # 使用新参数重试
                    pass
                    
        finally:
            # 注销Call-ID
            self.sip_482_handler.unregister_call_id(call_id)
    '''
    
    print("\n示例代码:")
    print(example_code)

if __name__ == "__main__":
    handler = SIP482Handler()
    integrate_482_handling_in_client()