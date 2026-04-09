#!/usr/bin/env python3
"""
清理SIP服务器上的活动呼叫脚本
用于解决503 "Maximum Calls In Progress"错误
"""

import sys
import os
import time
import logging
import socket
from typing import Dict, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from test_client.sip_test_client import SIPTestClient, SIPMessageBuilder
from main import setup_logging





def cleanup_active_calls(sip_client: SIPTestClient, max_attempts: int = 3):
    """
    清理SIP客户端中的活动呼叫
    
    Args:
        sip_client: SIP测试客户端实例
        max_attempts: 最大尝试次数
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"开始清理活动呼叫，当前活跃呼叫数: {len(sip_client.active_calls)}")
    
    if not sip_client.active_calls:
        logger.info("没有活跃的呼叫需要清理")
        return True
    
    success_count = 0
    failed_count = 0
    
    for call_id, call_info in list(sip_client.active_calls.items()):
        logger.info(f"正在清理呼叫 {call_id}: {call_info['caller']} -> {call_info['callee']}")
        
        attempt = 0
        while attempt < max_attempts:
            try:
                # 使用SIPMessageBuilder构造BYE请求来结束呼叫
                bye_message = SIPMessageBuilder.create_bye_message(
                    caller_uri=call_info['caller'],
                    callee_uri=call_info['callee'],
                    call_id=call_id,
                    local_host=sip_client.local_host,
                    local_port=sip_client.local_port,
                    cseq=3  # 假设INVITE使用了CSeq=2，BYE使用CSeq=3
                )
                
                # 创建UDP套接字发送BYE请求
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(5)  # 5秒超时
                
                logger.info(f"发送BYE请求到 {sip_client.sip_server_host}:{sip_client.sip_server_port}")
                sock.sendto(bye_message.encode('utf-8'), 
                           (sip_client.sip_server_host, sip_client.sip_server_port))
                
                # 等待服务器确认
                try:
                    response_data, server_addr = sock.recvfrom(4096)
                    response_str = response_data.decode('utf-8')
                    logger.info(f"收到服务器响应: {response_str[:100]}...")
                    
                    # 解析响应
                    parsed_response = SIPMessageBuilder.parse_response(response_str)
                    if parsed_response and parsed_response.get('status_code') == '200':
                        logger.info(f"成功结束呼叫 {call_id}")
                        success_count += 1
                    else:
                        logger.warning(f"BYE请求未收到200 OK响应: {parsed_response.get('status_code', 'Unknown')}")
                        
                except socket.timeout:
                    logger.warning(f"BYE确认超时，呼叫 {call_id} 可能已结束")
                    success_count += 1  # 假设呼叫已结束
                
                sock.close()
                
                # 从活跃呼叫列表中移除
                if call_id in sip_client.active_calls:
                    sip_client.active_calls[call_id]["status"] = "terminated"
                    sip_client.active_calls[call_id]["end_time"] = time.time()
                    del sip_client.active_calls[call_id]
                
                break  # 成功结束，跳出重试循环
                
            except Exception as e:
                attempt += 1
                logger.error(f"结束呼叫 {call_id} 失败 (尝试 {attempt}/{max_attempts}): {str(e)}")
                
                if attempt >= max_attempts:
                    logger.error(f"结束呼叫 {call_id} 最终失败")
                    failed_count += 1
                else:
                    time.sleep(1)  # 等待1秒后重试
    
    logger.info(f"清理完成: 成功 {success_count} 个，失败 {failed_count} 个")
    logger.info(f"剩余活跃呼叫数: {len(sip_client.active_calls)}")
    
    return failed_count == 0


def main():
    """主函数 - 清理SIP服务器上的活动呼叫"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("开始执行SIP活动呼叫清理")
    
    try:
        # 创建SIP测试客户端
        sip_client = SIPTestClient()
        
        logger.info(f"连接到SIP服务器: {sip_client.sip_server_host}:{sip_client.sip_server_port}")
        
        # 清理活动呼叫
        cleanup_success = cleanup_active_calls(sip_client)
        
        if cleanup_success:
            logger.info("SIP活动呼叫清理成功完成！")
            print("SUCCESS: 活动呼叫清理完成")
        else:
            logger.warning("SIP活动呼叫清理部分失败")
            print("PARTIAL_SUCCESS: 活动呼叫清理部分完成")
        
        # 显示清理后的状态
        logger.info(f"清理后剩余活跃呼叫数: {len(sip_client.active_calls)}")
        
        return True
        
    except Exception as e:
        logger.error(f"执行SIP活动呼叫清理时发生错误: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        print(f"ERROR: {str(e)}")
        return False


if __name__ == "__main__":
    main()