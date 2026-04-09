#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
执行简单呼叫测试脚本
用于执行从100010到670010的呼叫测试
"""

import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from test_client.sip_test_client import SIPTestClient


def setup_logging():
    """设置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('./logs/simple_call_test.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """主函数 - 执行100010到670010的呼叫测试"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("开始执行100010到670010的简单呼叫测试")
    
    try:
        # 创建SIP测试客户端
        # 使用默认配置文件
        sip_client = SIPTestClient()
        
        # 设置主叫和被叫URI
        caller_uri = "sip:100010@192.168.30.66:5060"  # 主叫用户100010
        callee_uri = "sip:670010@192.168.30.66:5060"  # 被叫用户670010
        
        logger.info(f"准备执行呼叫: {caller_uri} -> {callee_uri}")
        
        # 执行呼叫测试，通话时长设为10秒
        call_success = sip_client.make_call(caller_uri, callee_uri, duration=10)
        
        if call_success:
            logger.info("呼叫测试成功完成！")
            print("SUCCESS: 呼叫100010到670010成功")
        else:
            logger.error("呼叫测试失败！")
            print("FAILURE: 呼叫100010到670010失败")
            
        return call_success
        
    except Exception as e:
        logger.error(f"执行呼叫测试时发生错误: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        print(f"ERROR: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)