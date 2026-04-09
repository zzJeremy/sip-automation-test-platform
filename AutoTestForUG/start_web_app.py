#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动Web应用的脚本
禁用热重载以确保新添加的路由能正确加载
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

if __name__ == '__main__':
    from web_interface.web_app import socketio, app
    
    print("启动Web服务器 (禁用热重载)...")
    print("访问地址: http://localhost:5000")
    
    # 禁用debug模式和重载器
    socketio.run(app, 
                debug=False, 
                host='0.0.0.0', 
                port=5000,
                use_reloader=False)