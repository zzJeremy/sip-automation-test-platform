#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
仅使用Flask运行应用（不使用SocketIO）以测试路由
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

if __name__ == '__main__':
    from web_interface.web_app import app
    
    print("启动Flask服务器（不使用SocketIO）...")
    print("访问地址: http://localhost:5000")
    
    # 使用Flask内置服务器，禁用重载器
    app.run(
        debug=False,
        host='0.0.0.0',
        port=5000,
        use_reloader=False
    )