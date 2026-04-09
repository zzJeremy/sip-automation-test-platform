#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动SIP自动化测试后端服务
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

def start_backend():
    """启动后端Web服务"""
    try:
        from web_interface.web_app import app
        print('Web应用模块导入成功')
        print('正在启动Flask Web服务器...')
        print('访问地址: http://localhost:5000')
        
        # 运行Flask应用
        app.run(debug=False, host='0.0.0.0', port=5000)
        
    except ImportError as e:
        print(f'Web应用模块导入失败: {e}')
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f'启动后端服务失败: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_backend()