#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动本地SIP服务器脚本
用于启动一个本地的SIP测试服务器，以便进行SIP呼叫测试
"""

import sys
import os
import threading
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_server.sip_test_server import SIPTestServer


def main():
    """主函数 - 启动本地SIP服务器"""
    print("正在启动本地SIP测试服务器...")
    
    # 创建SIP测试服务器实例
    server = SIPTestServer()
    
    try:
        # 启动服务器
        server.start()
        print(f"SIP测试服务器已在 {server.host}:{server.port} 上启动")
        print("服务器正在运行，按 Ctrl+C 停止服务器...")
        
        # 保持服务器运行
        try:
            while server.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止SIP服务器...")
            server.stop()
            print("SIP服务器已停止")
            
    except Exception as e:
        print(f"启动SIP服务器失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()