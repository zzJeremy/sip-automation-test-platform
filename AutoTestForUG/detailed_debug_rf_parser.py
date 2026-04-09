#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
详细调试Robot Framework适配器的解析功能
"""
def debug_parse_robot_test_content(rf_content):
    """
    调试解析Robot Framework测试内容
    """
    sections = {
        'settings': [],
        'variables': [],
        'test_cases': [],
        'keywords': []
    }
    
    current_section = None
    current_test_case = None
    
    lines = rf_content.split('\n')
    for idx, line in enumerate(lines):
        print(f"处理第{idx}行: {repr(line)}")
        stripped_line = line.strip()
        print(f"  stripped_line: {repr(stripped_line)}")
        
        # 检查是否是新的节
        if stripped_line.startswith('*** ') and stripped_line.endswith(' ***'):
            section_name = stripped_line[4:-4].upper().replace(' ', '_')
            # 将大写节名转换为小写以匹配sections字典键
            if section_name == 'SETTINGS':
                current_section = 'settings'
            elif section_name == 'VARIABLES':
                current_section = 'variables'
            elif section_name == 'TEST_CASES':
                current_section = 'test_cases'
            elif section_name == 'KEYWORDS':
                current_section = 'keywords'
            print(f"  设置当前节为: {current_section}")
            continue
        
        if not stripped_line or stripped_line.startswith('#'):
            print("  跳过空行或注释")
            continue
            
        # 根据当前节处理内容
        print(f"  当前节: {current_section}")
        if current_section == 'test_cases':
            is_new_test_case = not line.startswith(' ') and not line.startswith('\t')
            print(f"  是否新测试用例 ({line.startswith(' ')} and {line.startswith('\t')}): {is_new_test_case}")
            
            if is_new_test_case:  # 新的测试用例名称
                print("  创建新测试用例")
                current_test_case = {
                    'name': stripped_line,
                    'steps': [],
                    'tags': []
                }
                sections[current_section].append(current_test_case)
                print(f"  当前测试用例: {current_test_case}")
            elif current_test_case and stripped_line.startswith('[Tags]'):
                print("  处理标签")
                # 解析标签
                tags = stripped_line.split('[Tags]')[1].strip().split()
                current_test_case['tags'] = tags
            elif current_test_case and stripped_line.startswith('...'):
                print("  处理连续行")
                # 连续行
                if current_test_case['steps']:
                    last_step = current_test_case['steps'][-1]
                    # 添加连续行内容到上一步骤
                    last_step['args'].extend(stripped_line[3:].strip().split())
            elif current_test_case and (line.startswith(' ') or line.startswith('\t')):  # 步骤行，以空格或制表符开头
                print("  处理步骤")
                # 解析步骤 - 表格格式
                parts = [part.strip() for part in line.split('\t') if part.strip()]
                print(f"  Tab分割结果: {parts}")
                if not parts:  # 尝试空格分割（Robot Framework通常使用2个或更多空格作为分隔符）
                    parts = [part.strip() for part in line.split('  ') if part.strip()]  # 至少2个空格
                    print(f"  两空格分割结果: {parts}")
                    
                    # 如果上面的分割没产生足够部分，尝试更灵活的分割方式
                    if len(parts) < 2:
                        # 按单个空格分割，然后合并连续的参数
                        all_parts = line.strip().split(' ')
                        all_parts = [p for p in all_parts if p]  # 移除空元素
                        print(f"  单空格分割结果: {all_parts}")
                        if len(all_parts) >= 2:
                            parts = all_parts
                
                print(f"  最终parts: {parts}")
                if parts:
                    if len(parts) >= 2:
                        keyword = parts[0]
                        args = parts[1:]
                        
                        # 清理参数中的引号和注释
                        cleaned_args = []
                        for arg in args:
                            if arg.startswith('${') and arg.endswith('}'):
                                # 变量引用
                                cleaned_args.append(arg)
                            elif arg.startswith('@{') and arg.endswith('}'):
                                # 列表变量
                                cleaned_args.append(arg)
                            else:
                                # 普通参数，移除可能的引号
                                cleaned_arg = arg.strip('"\'')
                                cleaned_args.append(cleaned_arg)
                        
                        step = {
                            'keyword': keyword,
                            'args': cleaned_args
                        }
                        current_test_case['steps'].append(step)
                        print(f"  添加步骤: {step}")
        
        print(f"  当前行处理完毕，sections[test_cases]长度: {len(sections['test_cases'])}")
        if sections['test_cases']:
            print(f"    最后一个测试用例步骤数: {len(sections['test_cases'][-1]['steps'])}")
        print()

    return sections

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
parsed = debug_parse_robot_test_content(simple_rf)

print('最终解析结果:')
for section, content in parsed.items():
    print(f'{section}: {len(content)} 项')
    if content and section == 'test_cases':
        for i, tc in enumerate(content):
            print(f'  测试用例 {i}: {tc}')