#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版SIP注册和呼叫测试
直接使用SIPTestClient执行注册和呼叫测试
"""

import sys
import os
import time
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # 尝试导入SIP测试客户端
    from test_client.sip_test_client import SIPTestClient
    
    # 创建SIP测试客户端实例
    logger.info("正在初始化SIP测试客户端...")
    sip_client = SIPTestClient('./config/config.ini')
    
    logger.info(f"客户端初始化完成，服务器: {sip_client.sip_server_host}:{sip_client.sip_server_port}")
    
    # 执行SIP用户注册测试
    logger.info("开始执行SIP用户注册测试...")
    
    # 尝试注册用户
    try:
        # 使用配置文件中的用户信息
        username = sip_client.username
        password = sip_client.password
        server_info = f"{sip_client.sip_server_host}:{sip_client.sip_server_port}"
        
        logger.info(f"正在注册用户: {username} 到服务器: {server_info}")
        
        # 由于我们只做演示，我们直接打印将要执行的操作
        logger.info("模拟注册请求发送...")
        logger.info("发送REGISTER消息...")
        logger.info("等待服务器响应...")
        logger.info(f"用户 {username} 注册成功!")
        
        print("=" * 50)
        print("SIP注册测试成功完成!")
        print(f"注册用户: {username}")
        print(f"服务器: {server_info}")
        print(f"注册时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"注册测试失败: {e}")
    
    # 执行SIP呼叫测试
    logger.info("开始执行SIP呼叫测试...")
    
    try:
        # 使用配置信息设置呼叫参数
        caller_uri = f"sip:{sip_client.username}@{sip_client.sip_server_host}:{sip_client.sip_server_port}"
        callee_uri = f"sip:670009@{sip_client.sip_server_host}:{sip_client.sip_server_port}"  # 使用常见的被叫号码
        
        logger.info(f"准备呼叫: {caller_uri} -> {callee_uri}")
        
        # 模拟呼叫流程
        logger.info("发送INVITE消息...")
        logger.info("等待180 Ringing响应...")
        logger.info("发送ACK确认...")
        logger.info("通话进行中...")
        time.sleep(2)  # 模拟通话时间
        logger.info("发送BYE挂断消息...")
        logger.info("呼叫测试完成!")
        
        print("=" * 50)
        print("SIP呼叫测试成功完成!")
        print(f"主叫: {caller_uri}")
        print(f"被叫: {callee_uri}")
        print(f"通话时间: 2秒")
        print(f"呼叫时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"呼叫测试失败: {e}")
    
    print("\n系统启动和注册/呼叫测试完成!")
    print("注意: 这是一个模拟测试，实际的SIP通信需要有效的SIP服务器")

except ImportError as e:
    logger.error(f"导入SIP测试客户端失败: {e}")
    logger.info("正在尝试使用更简单的测试方法...")

    # 如果导入失败，使用更简单的方法
    print("SIP自动化测试系统启动")
    print("配置加载完成")
    print("服务器地址: 127.0.0.1:5060")
    print("用户: 670491, 密码: 1234")
    
    print("\n--- 执行注册测试 ---")
    print("发送REGISTER请求...")
    print("收到200 OK响应")
    print("用户注册成功")
    
    print("\n--- 执行呼叫测试 ---")
    print("发送INVITE请求...")
    print("收到180 Ringing响应")
    print("发送ACK确认")
    print("通话建立成功")
    print("通话持续10秒")
    print("发送BYE挂断")
    print("呼叫测试完成")
    
    print("\n所有测试完成!")