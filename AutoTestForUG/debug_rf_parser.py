#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试Robot Framework适配器的解析功能
"""
from rf_adapter.robot_adapter import RobotFrameworkAdapter

def debug_parsing():
    """调试解析功能"""
    adapter = RobotFrameworkAdapter()
    
    # 测试简单的RF内容解析
    simple_rf = '''*** Test Cases ***
Simple Test
    Log    Hello World
    Should Be Equal    1    1
'''
    
    print('原始内容:')
    for i, line in enumerate(simple_rf.split('\n')):
        print(f'{i}: {repr(line)}')
    
    print('\n解析过程...')
    parsed = adapter.parse_robot_test_content(simple_rf)
    
    print('解析结果:')
    for section, content in parsed.items():
        print(f'{section}: {len(content)} 项')
        if content and section == 'test_cases':
            for i, tc in enumerate(content):
                print(f'  测试用例 {i}: {tc}')
    
if __name__ == "__main__":
    debug_parsing()