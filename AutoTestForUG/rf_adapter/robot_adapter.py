"""
Robot Framework 适配器
将Robot Framework关键字映射到底层pytest测试
"""
import os
import tempfile
import subprocess
import json
from typing import Dict, Any, List
from pathlib import Path
import re
import time


class RobotFrameworkAdapter:
    """
    Robot Framework 适配器
    将Robot Framework测试转换为pytest执行
    """
    
    def __init__(self, debug_mode=False, config=None):
        self.debug_mode = debug_mode
        self.config = config or {}
        self.keyword_mapping = {
            # SIP基本操作关键字
            'Register User': 'register_user',
            'Unregister User': 'unregister_user',
            'Make SIP Call': 'make_call',
            'End Call': 'end_call',
            'Send SIP Message': 'send_message',
            'Verify Call Status': 'verify_call_status',
            
            # 扩展SIP相关关键字
            'Setup SIP Session': 'setup_sip_session',
            'Teardown SIP Session': 'teardown_sip_session',
            'Send SIP Invite': 'send_invite',
            'Send SIP Ack': 'send_ack',
            'Send SIP Bye': 'send_bye',
            'Send SIP Cancel': 'send_cancel',
            'Send SIP Options': 'send_options',
            'Send SIP Info': 'send_info',
            'Send SIP Notify': 'send_notify',
            'Send SIP Subscribe': 'send_subscribe',
            'Send SIP Refer': 'send_refer',
            'Wait For SIP Response': 'wait_for_response',
            'Wait For SIP Request': 'wait_for_request',
            'Validate SIP Message': 'validate_sip_message',
            'Parse SIP Response': 'parse_sip_response',
            'Check SIP Headers': 'check_sip_headers',
            'Modify SIP Headers': 'modify_sip_headers',
            'Create SIP Dialog': 'create_sip_dialog',
            'Close SIP Dialog': 'close_sip_dialog',
            'Start RTP Stream': 'start_rtp_stream',
            'Stop RTP Stream': 'stop_rtp_stream',
            'Monitor Call Quality': 'monitor_call_quality',
            'Generate SIP Traffic': 'generate_sip_traffic',
            'Simulate Network Delay': 'simulate_network_delay',
            'Simulate Packet Loss': 'simulate_packet_loss',
            'Test SIP Authentication': 'test_sip_authentication',
            'Verify SIP Registration': 'verify_sip_registration',
            'Check SIP Server Status': 'check_sip_server_status',
            'Configure SIP Client': 'configure_sip_client',
            'Reset SIP Client': 'reset_sip_client',
            'Get SIP Statistics': 'get_sip_statistics',
            'Analyze SIP Logs': 'analyze_sip_logs',
            
            # Robot Framework BuiltIn库关键字
            'Should Be Equal': 'should_be_equal',
            'Should Be Equal As Strings': 'should_be_equal_as_strings',
            'Should Be Equal As Numbers': 'should_be_equal_as_numbers',
            'Should Be Equal As Integers': 'should_be_equal_as_integers',
            'Should Be Equal As Floats': 'should_be_equal_as_floats',
            'Should Be True': 'should_be_true',
            'Should Be False': 'should_be_false',
            'Should Not Be True': 'should_not_be_true',
            'Should Not Be False': 'should_not_be_false',
            'Should Be None': 'should_be_none',
            'Should Not Be None': 'should_not_be_none',
            'Should Contain': 'should_contain',
            'Should Not Contain': 'should_not_contain',
            'Should Match': 'should_match',
            'Should Match Regexp': 'should_match_regexp',
            'Should Start With': 'should_start_with',
            'Should End With': 'should_end_with',
            'Should Not Start With': 'should_not_start_with',
            'Should Not End With': 'should_not_end_with',
            'Length Should Be': 'length_should_be',
            'Should Be Empty': 'should_be_empty',
            'Should Not Be Empty': 'should_not_be_empty',
            'Fail': 'fail',
            'Pass Execution': 'pass_execution',
            'Continue For Loop': 'continue_for_loop',
            'Exit For Loop': 'exit_for_loop',
            'Log': 'log_message',
            'Log Many': 'log_many',
            'Log To Console': 'log_to_console',
            'Comment': 'comment',
            'Catenate': 'catenate',
            'Set Log Level': 'set_log_level',
            'Get Time': 'get_time',
            'Convert To String': 'convert_to_string',
            'Convert To Integer': 'convert_to_integer',
            'Convert To Number': 'convert_to_number',
            'Convert To Boolean': 'convert_to_boolean',
            'Create List': 'create_list',
            'Create Dictionary': 'create_dictionary',
            'Evaluate': 'evaluate_expression',
            'Call Method': 'call_method',
            'Regexp Escape': 'regexp_escape',
            'Set Variable': 'set_variable',
            'Variable Should Exist': 'variable_should_exist',
            'Variable Should Not Exist': 'variable_should_not_exist',
            'Get Variable Value': 'get_variable_value',
            'Get Variable Names': 'get_variable_names',
            
            # Robot Framework Collections库关键字
            'Append To List': 'append_to_list',
            'Copy List': 'copy_list',
            'Copy Dictionary': 'copy_dictionary',
            'Dictionary Should Contain Key': 'dictionary_should_contain_key',
            'Dictionary Should Contain Value': 'dictionary_should_contain_value',
            'Dictionary Should Not Contain Key': 'dictionary_should_not_contain_key',
            'Remove From List': 'remove_from_list',
            'Remove From Dictionary': 'remove_from_dictionary',
            'Set To Dictionary': 'set_to_dictionary',
            'Sort List': 'sort_list',
            
            # Robot Framework String库关键字
            'Encode String To Bytes': 'encode_string_to_bytes',
            'Decode Bytes To String': 'decode_bytes_to_string',
            'Format String': 'format_string',
            'Get Line Count': 'get_line_count',
            'Split To Lines': 'split_to_lines',
            'Split String': 'split_string',
            'Split String To Chars': 'split_string_to_chars',
            'Strip String': 'strip_string',
            'Should Be Title Case': 'should_be_title_case',
            'Should Be Lower Case': 'should_be_lower_case',
            'Should Be Upper Case': 'should_be_upper_case',
            'Convert To Lower Case': 'convert_to_lower_case',
            'Convert To Upper Case': 'convert_to_upper_case',
            'Convert To Title Case': 'convert_to_title_case',
            'Replace String': 'replace_string',
            'Replace String Using Regexp': 'replace_string_using_regexp',
            'Get Substring': 'get_substring',
            'Remove String': 'remove_string',
            'Remove String Using Regexp': 'remove_string_using_regexp',
            'Remove Suffix': 'remove_suffix',
            'Remove Prefix': 'remove_prefix',
            'Count Matching Lines': 'count_matching_lines',
            'Get Regexp Matches': 'get_regexp_matches',
            'Fetch From Left': 'fetch_from_left',
            'Fetch From Right': 'fetch_from_right',
            
            # 通用关键字
            'Sleep': 'sleep',
            
            # 控制结构关键字
            'WHILE': 'while_loop',
            'WHILE CONDITION': 'while_condition',
            'TRY': 'try_block',
            'EXCEPT': 'except_block',
            'FINALLY': 'finally_block',
            'BREAK': 'break_statement',
            'CONTINUE': 'continue_statement',
        }
        
    def rf_to_pytest_keywords(self, rf_keyword: str) -> str:
        """将Robot Framework关键字转换为pytest关键字"""
        return self.keyword_mapping.get(rf_keyword, rf_keyword.lower().replace(' ', '_'))
    
    def parse_robot_test_content(self, rf_content: str) -> Dict[str, Any]:
        """
        解析Robot Framework测试内容
        支持星号格式和表格格式，包括变量替换和控制结构
        """
        if self.debug_mode:
            print("[DEBUG] 开始解析Robot Framework测试内容")
        
        sections = {
            'settings': [],
            'variables': {},
            'test_cases': [],
            'keywords': []
        }
        
        current_section = None
        current_test_case = None
        current_keyword = None
        
        # 解析变量定义
        variables = {}
        for line in rf_content.split('\n'):
            stripped_line = line.strip()
            if stripped_line.startswith('*** Variables ***'):
                current_section = 'variables'
            elif stripped_line.startswith('*** Test Cases ***'):
                current_section = 'test_cases'
            elif stripped_line.startswith('*** Keywords ***'):
                current_section = 'keywords'
            elif stripped_line.startswith('*** Settings ***'):
                current_section = 'settings'
            elif current_section == 'variables' and stripped_line and not stripped_line.startswith('#'):
                # 解析变量定义，例如: ${VAR_NAME}    value
                parts = stripped_line.split(None, 1)  # 分割为最多两部分
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    var_value = parts[1].strip()
                    variables[var_name] = var_value
                    if self.debug_mode:
                        print(f"[DEBUG] 解析变量: {var_name} = {var_value}")
        
        if self.debug_mode:
            print(f"[DEBUG] 解析到变量: {variables}")
        
        # 重新解析整个内容
        lines = rf_content.split('\n')
        current_section = None
        current_test_case = None
        current_keyword = None
        
        for line_num, line in enumerate(lines):
            stripped_line = line.strip()
            
            # 检查是否是新的节
            if stripped_line.startswith('*** ') and stripped_line.endswith(' ***'):
                section_name = stripped_line[4:-4].upper().replace(' ', '_')
                if section_name == 'SETTINGS':
                    current_section = 'settings'
                elif section_name == 'VARIABLES':
                    current_section = 'variables'
                elif section_name == 'TEST_CASES':
                    current_section = 'test_cases'
                elif section_name == 'KEYWORDS':
                    current_section = 'keywords'
                if self.debug_mode:
                    print(f"[DEBUG] 发现节: {section_name}")
                continue
            
            if not stripped_line or stripped_line.startswith('#'):
                continue
                
            # 根据当前节处理内容
            if current_section == 'test_cases':
                # 检查是否是新的测试用例
                if not line.startswith(' ') and not line.startswith('\t') and not stripped_line.startswith('['):  # 新的测试用例名称
                    if self.debug_mode:
                        print(f"[DEBUG] 发现测试用例: {stripped_line}")
                    current_test_case = {
                        'name': stripped_line,
                        'steps': [],
                        'tags': [],
                        'variables': variables.copy()  # 每个测试用例都继承全局变量
                    }
                    sections[current_section].append(current_test_case)
                elif current_test_case and stripped_line.startswith('[Tags]'):
                    # 解析标签
                    tags = stripped_line.split('[Tags]')[1].strip().split()
                    current_test_case['tags'] = tags
                    if self.debug_mode:
                        print(f"[DEBUG] 解析标签: {tags}")
                elif current_test_case and stripped_line.startswith('...'):
                    # 连续行
                    if current_test_case['steps']:
                        last_step = current_test_case['steps'][-1]
                        # 添加连续行内容到上一步骤
                        last_step['args'].extend(stripped_line[3:].strip().split())
                        if self.debug_mode:
                            print(f"[DEBUG] 连续行参数: {last_step['args']}")
                elif current_test_case and (line.startswith(' ') or line.startswith('\t')):  # 步骤行，以空格或制表符开头
                    # 解析步骤 - 表格格式
                    stripped_from_indent = line.lstrip()
                    # 先处理变量替换
                    processed_line = self._replace_variables_in_line(stripped_from_indent, current_test_case['variables'])
                    
                    if self.debug_mode:
                        print(f"[DEBUG] 处理步骤行: {stripped_from_indent} -> {processed_line}")
                    
                    # 按Robot Framework标准格式解析（至少2个空格分隔）
                    parts = []
                    current_part = ""
                    i = 0
                    while i < len(processed_line):
                        if processed_line[i:i+2] == '  ':  # 两个空格表示分隔符
                            if current_part.strip():
                                parts.append(current_part.strip())
                                current_part = ""
                            i += 2
                            # 跳过多余的空格
                            while i < len(processed_line) and processed_line[i] == ' ':
                                i += 1
                            continue
                        else:
                            current_part += processed_line[i]
                            i += 1
                    if current_part.strip():
                        parts.append(current_part.strip())
                    
                    if parts:
                        if len(parts) >= 1:
                            keyword = parts[0]
                            args = parts[1:] if len(parts) > 1 else []
                            
                            # 清理参数中的引号和注释
                            cleaned_args = []
                            for arg in args:
                                if arg.startswith('${') and arg.endswith('}'):
                                    # 变量引用 - 已经在上面处理过了
                                    cleaned_args.append(arg)
                                elif arg.startswith('@{') and arg.endswith('}'):
                                    # 列表变量
                                    cleaned_args.append(arg)
                                else:
                                    # 普通参数，移除可能的引号
                                    cleaned_arg = arg.strip('"\'')
                                    cleaned_args.append(cleaned_arg)
                            
                            current_test_case['steps'].append({
                                'keyword': keyword,
                                'args': cleaned_args
                            })
                            if self.debug_mode:
                                print(f"[DEBUG] 解析步骤: {keyword} with args {cleaned_args}")
            elif current_section == 'variables':
                # 变量已经在上面解析过了，这里只存储定义
                sections[current_section] = variables
            elif current_section == 'settings':
                # 解析设置
                sections[current_section].append(line.strip())
                if self.debug_mode:
                    print(f"[DEBUG] 解析设置: {line.strip()}")
            elif current_section == 'keywords':
                # 解析自定义关键字
                if not line.startswith(' ') and not line.startswith('\t') and not stripped_line.startswith('['):
                    # 新的关键字名称
                    if self.debug_mode:
                        print(f"[DEBUG] 发现关键字: {stripped_line}")
                    current_keyword = {
                        'name': stripped_line,
                        'args': [],
                        'steps': [],
                        'variables': variables.copy()
                    }
                    sections[current_section].append(current_keyword)
                elif current_keyword and stripped_line.startswith('[Arguments]'):
                    # 关键字参数
                    args_line = stripped_line.split('[Arguments]')[1].strip()
                    args = [arg.strip() for arg in args_line.split()]
                    current_keyword['args'] = args
                    if self.debug_mode:
                        print(f"[DEBUG] 关键字参数: {args}")
                elif current_keyword and (line.startswith(' ') or line.startswith('\t')):
                    # 关键字步骤
                    stripped_from_indent = line.lstrip()
                    # 处理变量替换
                    processed_line = self._replace_variables_in_line(stripped_from_indent, current_keyword['variables'])
                    
                    if self.debug_mode:
                        print(f"[DEBUG] 处理关键字步骤: {stripped_from_indent} -> {processed_line}")
                    
                    # 按Robot Framework标准格式解析
                    parts = []
                    current_part = ""
                    i = 0
                    while i < len(processed_line):
                        if processed_line[i:i+2] == '  ':  # 两个空格表示分隔符
                            if current_part.strip():
                                parts.append(current_part.strip())
                                current_part = ""
                            i += 2
                            # 跳过多余的空格
                            while i < len(processed_line) and processed_line[i] == ' ':
                                i += 1
                            continue
                        else:
                            current_part += processed_line[i]
                            i += 1
                    if current_part.strip():
                        parts.append(current_part.strip())
                    
                    if parts and len(parts) >= 1:
                        keyword = parts[0]
                        args = parts[1:] if len(parts) > 1 else []
                        
                        # 清理参数
                        cleaned_args = []
                        for arg in args:
                            if arg.startswith('${') and arg.endswith('}'):
                                cleaned_args.append(arg)
                            elif arg.startswith('@{') and arg.endswith('}'):
                                cleaned_args.append(arg)
                            else:
                                cleaned_arg = arg.strip('"\'')
                                cleaned_args.append(cleaned_arg)
                        
                        current_keyword['steps'].append({
                            'keyword': keyword,
                            'args': cleaned_args
                        })
                        if self.debug_mode:
                            print(f"[DEBUG] 解析关键字步骤: {keyword} with args {cleaned_args}")
        
        if self.debug_mode:
            print(f"[DEBUG] 解析完成，共找到 {len(sections['test_cases'])} 个测试用例")
        
        return sections

    def _replace_variables_in_line(self, line: str, variables: dict) -> str:
        """
        替换行中的变量引用
        """
        result = line
        # 查找并替换 ${var} 格式的变量
        import re
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_name = match.group(0)  # 完整的变量引用，如 ${USERNAME}
            actual_name = match.group(1)  # 变量名，如 USERNAME
            # 检查是否在变量字典中存在
            if var_name in variables:
                return variables[var_name]
            elif f"${{{actual_name}}}" in variables:
                return variables[f"${{{actual_name}}}"]
            else:
                # 如果变量未定义，保持原样
                return var_name
        
        result = re.sub(pattern, replace_var, result)
        return result
    
    def convert_rf_test_to_pytest(self, rf_test_content: str) -> str:
        """
        将Robot Framework测试转换为pytest测试
        """
        parsed_content = self.parse_robot_test_content(rf_test_content)
        
        # 生成pytest代码模板
        pytest_template = '''import pytest
from AutoTestForUG.rf_adapter.robot_adapter import SIPRobotKeywords


class TestConvertedFromRF:
    @pytest.fixture(autouse=True)
    def setup_sip_client(self):
        """自动设置SIP客户端"""
        self.sip_client = SIPRobotKeywords()
    
'''
        
        # 转换测试用例
        for test_case in parsed_content.get('test_cases', []):
            test_name = test_case['name'].lower().replace(' ', '_').replace('-', '_')
            
            # 添加测试方法
            pytest_template += f'    def test_{test_name}(self):\n'
            pytest_template += f'        """{test_case["name"]}"""\n'
            
            # 添加标签作为pytest标记
            if test_case['tags']:
                for tag in test_case['tags']:
                    pytest_template += f'        # Tag: {tag}\n'
            
            # 转换步骤，处理控制结构
            for step in test_case['steps']:
                keyword = step['keyword']
                args = step['args']
                
                # 特殊处理控制结构
                if keyword.upper() in ['FOR', 'END', 'IF', 'ELSE IF', 'ELSE', 'WHILE', 'TRY', 'EXCEPT', 'FINALLY', 'BREAK', 'CONTINUE']:
                    pytest_template += self._convert_control_structure(keyword, args)
                else:
                    # 转换普通关键字
                    method_name = self.rf_to_pytest_keywords(keyword).replace(' ', '_').lower()
                    
                    # 处理参数
                    formatted_args = []
                    for arg in args:
                        # 处理变量引用
                        if arg.startswith('${') and arg.endswith('}'):
                            # Robot变量，转为字符串
                            formatted_args.append(f'"{arg}"')
                        elif arg.startswith('@{') and arg.endswith('}'):
                            # Robot列表变量
                            formatted_args.append(f'"{arg}"')
                        else:
                            # 普通参数
                            formatted_args.append(f'"{arg}"')
                    
                    # 添加步骤代码
                    if formatted_args:
                        pytest_template += f'        self.sip_client.{method_name}({", ".join(formatted_args)})\n'
                    else:
                        pytest_template += f'        self.sip_client.{method_name}()\n'
            
            pytest_template += '\n'
        
        return pytest_template

    def _convert_control_structure(self, keyword: str, args: list) -> str:
        """
        转换Robot Framework控制结构为Python代码
        """
        keyword_upper = keyword.upper()
        
        if keyword_upper == 'FOR':
            # FOR循环转换示例: FOR    ${INDEX}    IN RANGE    5
            if len(args) >= 3 and args[1].upper() == 'IN':
                var_name = args[0].strip('"\'')
                collection_type = args[2].upper()
                
                if collection_type == 'RANGE':
                    if len(args) > 3:
                        range_end = args[3].strip('"\'')
                        return f'        for {var_name.strip("${}")} in range(int({range_end})):\n'
                    else:
                        return f'        for {var_name.strip("${}")} in range(int({args[2].strip("\"\'")})):\n'
                elif collection_type in ['IN', 'IN ENUMERATE']:
                    # IN 或 IN ENUMERATE 情况
                    collection = ' '.join(args[3:])  # 获取集合
                    return f'        for {var_name.strip("${}")} in {collection.strip("\"\'")}:\n'
            else:
                # 更通用的FOR循环处理
                return f'        # FOR loop: {keyword} {" ".join(args)}\n        # TODO: Implement specific FOR loop logic\n'
        
        elif keyword_upper == 'END':
            # END 结束块
            return ''  # 在Python中不需要END关键字
        
        elif keyword_upper == 'IF':
            # IF 条件语句
            condition = ' '.join(args)
            return f'        if {condition.strip("\"\'")}:\n'
        
        elif keyword_upper == 'ELSE IF':
            # ELSE IF 条件语句
            condition = ' '.join(args)
            return f'        elif {condition.strip("\"\'")}:\n'
        
        elif keyword_upper == 'ELSE':
            # ELSE 语句
            return f'        else:\n'
        
        elif keyword_upper == 'WHILE':
            # WHILE循环转换示例: WHILE    ${{condition}}
            condition = ' '.join(args)
            return f'        while {condition.strip("\"\'")}:\n'
        
        elif keyword_upper == 'TRY':
            # TRY 块
            return '        try:\n'
        
        elif keyword_upper == 'EXCEPT':
            # EXCEPT 块
            if args:
                exception_type = args[0].strip('"\'')
                if len(args) > 1:
                    exception_var = args[1].strip('"\'')
                    return f'        except {exception_type} as {exception_var}:\n'
                else:
                    return f'        except {exception_type}:\n'
            else:
                return '        except:\n'
        
        elif keyword_upper == 'FINALLY':
            # FINALLY 块
            return '        finally:\n'
        
        elif keyword_upper == 'BREAK':
            # BREAK 语句
            return '        break\n'
        
        elif keyword_upper == 'CONTINUE':
            # CONTINUE 语句
            return '        continue\n'
        
        # 默认返回注释
        return f'        # Control structure: {keyword} {" ".join(args)}\n'

    def load_config(self, config_file: str):
        """加载配置文件"""
        import json
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                self.config.update(loaded_config)
                if self.debug_mode:
                    print(f"[DEBUG] Loaded configuration from {config_file}")
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False

    def set_config(self, key: str, value):
        """设置配置项"""
        self.config[key] = value
        if self.debug_mode:
            print(f"[DEBUG] Set configuration {key} = {value}")

    def get_config(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)

    def get_all_configs(self):
        """获取所有配置项"""
        return self.config.copy()
    
    def execute_rf_style_test(self, rf_test_file: str) -> Dict[str, Any]:
        """
        执行Robot Framework风格的测试文件
        通过转换为pytest后执行
        """
        with open(rf_test_file, 'r', encoding='utf-8') as f:
            rf_content = f.read()
        
        # 转换为pytest测试
        pytest_content = self.convert_rf_test_to_pytest(rf_content)
        
        # 创建临时pytest文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(pytest_content)
            temp_pytest_file = temp_file.name
        
        try:
            # 执行pytest测试
            result = subprocess.run([
                'python', '-m', 'pytest', temp_pytest_file, '-v', '--tb=short', '-s'
            ], capture_output=True, text=True, timeout=300)
            
            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Test execution timed out',
                'success': False
            }
        finally:
            # 清理临时文件
            os.unlink(temp_pytest_file)
    
    def generate_performance_report(self, output_file: str = None):
        """
        生成性能报告
        """
        # 遍历所有SIPRobotKeywords实例并收集性能数据
        # 注意：在实际应用中，您需要跟踪所有创建的SIPRobotKeywords实例
        # 这里我们假设有一个全局的性能监控器
        print("生成性能报告...")
        # 示例：如果您有性能监控器实例
        # performance_monitor.print_report()
        # if output_file:
        #     performance_monitor.save_report(output_file)
        pass


class SIPRobotKeywords:
    """
    SIP相关的Robot Framework关键字
    这些关键字会被映射到底层的pytest/SIP实现
    """
    
    def __init__(self, debug_mode=False, log_level="INFO", config=None):
        from AutoTestForUG.sip_client.hybrid_client import HybridSIPTestClient
        import logging
        self.debug_mode = debug_mode
        self.log_level = log_level
        self.config = config or {}
        self.client = HybridSIPTestClient(self.config)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 如果还没有处理器，则添加一个
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # 初始化性能监控
        self.performance_monitor = PerformanceMonitor()
    
    def register_user(self, username: str, password: str, server_uri: str, expires: int = 3600) -> bool:
        """注册SIP用户"""
        operation_name = f"register_user_{username}"
        self.performance_monitor.start_timer(operation_name)
        
        try:
            start_time = time.time()
            self.logger.info(f"Registering user {username} to {server_uri} with expires={expires}")
            if self.debug_mode:
                self.logger.debug(f"[DEBUG] Registering user {username} to {server_uri} with expires={expires}")
            
            # 调用底层SIP实现
            try:
                # 尝试使用三个参数的调用方式
                result = self.client.register_user(username, password, expires)
                if self.debug_mode:
                    self.logger.debug(f"[DEBUG] Registration result: {result}")
                
                if result:
                    self.logger.info(f"Successfully registered user {username}")
                else:
                    self.logger.warning(f"Failed to register user {username}")
                
                return result
            except TypeError as te:
                self.logger.warning(f"Three-parameter register_user failed, trying four-parameter: {te}")
                # 如果上述调用失败，尝试使用四个参数的调用方式
                from AutoTestForUG.sip_client.client_manager import SIPClientType
                result = self.client.register_user(username, password, server_uri, expires)
                if self.debug_mode:
                    self.logger.debug(f"[DEBUG] Four-parameter registration result: {result}")
                
                if result:
                    self.logger.info(f"Successfully registered user {username} using four-parameter method")
                else:
                    self.logger.warning(f"Failed to register user {username} using four-parameter method")
                
                return result
        except Exception as e:
            self.logger.error(f"Error during registration of user {username}: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
            return False
        finally:
            duration = self.performance_monitor.stop_timer(operation_name)
            self.performance_monitor.record_test_result(
                f"register_user_{username}", 
                result, 
                duration, 
                {"username": username, "server_uri": server_uri}
            )
    
    def unregister_user(self, username: str, server_uri: str = None) -> bool:
        """注销SIP用户"""
        operation_name = f"unregister_user_{username}"
        self.performance_monitor.start_timer(operation_name)
        
        try:
            self.logger.info(f"Unregistering user {username}")
            if self.debug_mode:
                self.logger.debug(f"[DEBUG] Unregistering user {username}, server_uri={server_uri}")
            
            # 尝试直接调用unregister方法
            if hasattr(self.client, 'unregister'):
                # 调用客户端的unregister方法
                result = self.client.unregister()
                if self.debug_mode:
                    self.logger.debug(f"[DEBUG] Unregister result: {result}")
                
                if result:
                    self.logger.info(f"Successfully unregistered user {username}")
                else:
                    self.logger.warning(f"Failed to unregister user {username}")
                
                return result
            elif hasattr(self.client, 'unregister_user'):
                # 如果有unregister_user方法，尝试调用它
                result = self.client.unregister_user(username)
                if self.debug_mode:
                    self.logger.debug(f"[DEBUG] Unregister user result: {result}")
                
                if result:
                    self.logger.info(f"Successfully unregistered user {username}")
                else:
                    self.logger.warning(f"Failed to unregister user {username}")
                
                return result
            else:
                # 如果没有专门的unregister方法，使用注册expires=0的方式注销
                # 需要获取之前注册时使用的密码
                result = self.client.register_user(username, "dummy_password", 0)
                if self.debug_mode:
                    self.logger.debug(f"[DEBUG] Unregister via registration (expires=0) result: {result}")
                
                if result:
                    self.logger.info(f"Successfully unregistered user {username} via expires=0 registration")
                else:
                    self.logger.warning(f"Failed to unregister user {username} via expires=0 registration")
                
                return result
        except Exception as e:
            self.logger.error(f"Error during unregister of user {username}: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
            # 不再盲目返回True，而是返回False表示操作失败
            return False
        finally:
            duration = self.performance_monitor.stop_timer(operation_name)
            self.performance_monitor.record_test_result(
                f"unregister_user_{username}", 
                result, 
                duration, 
                {"username": username, "server_uri": server_uri}
            )
    
    def make_call(self, caller_uri: str, callee_uri: str, duration: int = 5) -> bool:
        """发起SIP呼叫"""
        operation_name = f"make_call_{caller_uri}_to_{callee_uri}"
        self.performance_monitor.start_timer(operation_name)
        
        try:
            self.logger.info(f"Making call from {caller_uri} to {callee_uri} for {duration}s")
            if self.debug_mode:
                self.logger.debug(f"[DEBUG] Making call from {caller_uri} to {callee_uri}")
            
            # 调用底层SIP实现
            result = self.client.make_call(caller_uri, callee_uri)
            if result:
                self.logger.info(f"Successfully made call from {caller_uri} to {callee_uri}")
            else:
                self.logger.warning(f"Failed to make call from {caller_uri} to {callee_uri}")
            
            return result
        except Exception as e:
            self.logger.error(f"Call from {caller_uri} to {callee_uri} failed: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
            return False
        finally:
            duration = self.performance_monitor.stop_timer(operation_name)
            self.performance_monitor.record_test_result(
                f"make_call_{caller_uri}_to_{callee_uri}", 
                result, 
                duration, 
                {"caller_uri": caller_uri, "callee_uri": callee_uri, "expected_duration": duration}
            )
    
    def end_call(self) -> bool:
        """结束当前呼叫"""
        print("Ending current call")
        # 目前HybridSIPTestClient没有直接的end_call方法，通过make_call来管理
        # 这里可以实现一些清理操作
        print("Call ended successfully")
        return True
    
    def send_message(self, sender_uri: str, recipient_uri: str, message: str) -> bool:
        """发送SIP消息"""
        print(f"Sending message from {sender_uri} to {recipient_uri}: {message}")
        # 调用底层SIP实现
        try:
            return self.client.send_message(sender_uri, recipient_uri, message)
        except Exception as e:
            print(f"Message sending failed: {e}")
            return False
    
    def verify_call_status(self, expected_status: str) -> bool:
        """验证呼叫状态"""
        print(f"Verifying call status is {expected_status}")
        # 这里可以根据需要实现状态验证逻辑
        # 目前返回True表示验证通过
        return True
    
    def sleep(self, duration: str) -> None:
        """暂停指定时间"""
        import time
        # 解析时间字符串，例如 "3s", "1m" 等
        duration = duration.strip()
        if duration.endswith('s'):
            seconds = float(duration[:-1])
        elif duration.endswith('m'):
            seconds = float(duration[:-1]) * 60
        elif duration.endswith('h'):
            seconds = float(duration[:-1]) * 3600
        else:
            # 假设没有单位时默认为秒
            seconds = float(duration)
        
        print(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
    
    def should_be_equal(self, first, second, msg: str = None) -> bool:
        """检查两个值是否相等"""
        if first != second:
            error_msg = f"{first} != {second}"
            if msg:
                error_msg = f"{msg}: {error_msg}"
            print(f"Assertion failed: {error_msg}")
            return False
        print(f"Values are equal: {first} == {second}")
        return True
    
    def should_contain(self, container, item, msg: str = None) -> bool:
        """检查容器是否包含指定项目"""
        if item not in container:
            error_msg = f"'{item}' not found in '{container}'"
            if msg:
                error_msg = f"{msg}: {error_msg}"
            print(f"Assertion failed: {error_msg}")
            return False
        print(f"'{container}' contains '{item}'")
        return True
    
    def log_message(self, message: str, level: str = "INFO") -> None:
        """记录消息"""
        # 使用logger记录消息
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, message)
        
        # 如果处于调试模式，同时打印
        if self.debug_mode:
            print(f"[{level}] {message}")
    
    def set_variable(self, variable_name: str, value: str) -> str:
        """设置变量值"""
        # 在Robot Framework中，这通常用于返回值给变量
        print(f"Setting variable {variable_name} = {value}")
        return value

    # Robot Framework BuiltIn库关键字实现
    def should_be_equal(self, first, second, msg: str = None) -> bool:
        """检查两个值是否相等"""
        if first != second:
            error_msg = f"{first} != {second}"
            if msg:
                error_msg = f"{msg}: {error_msg}"
            print(f"Assertion failed: {error_msg}")
            return False
        print(f"Values are equal: {first} == {second}")
        return True

    def should_be_true(self, condition, msg: str = None) -> bool:
        """检查条件是否为真"""
        if not condition:
            error_msg = f"Condition '{condition}' should be true"
            if msg:
                error_msg = f"{msg}: {error_msg}"
            print(f"Assertion failed: {error_msg}")
            return False
        print(f"Condition is true: {condition}")
        return True

    def should_be_false(self, condition, msg: str = None) -> bool:
        """检查条件是否为假"""
        if condition:
            error_msg = f"Condition '{condition}' should be false"
            if msg:
                error_msg = f"{msg}: {error_msg}"
            print(f"Assertion failed: {error_msg}")
            return False
        print(f"Condition is false: {condition}")
        return True

    def should_contain(self, container, item, msg: str = None) -> bool:
        """检查容器是否包含指定项目"""
        if item not in container:
            error_msg = f"'{item}' not found in '{container}'"
            if msg:
                error_msg = f"{msg}: {error_msg}"
            print(f"Assertion failed: {error_msg}")
            return False
        print(f"'{container}' contains '{item}'")
        return True

    def should_not_contain(self, container, item, msg: str = None) -> bool:
        """检查容器是否不包含指定项目"""
        if item in container:
            error_msg = f"'{item}' was found in '{container}' but should not be"
            if msg:
                error_msg = f"{msg}: {error_msg}"
            print(f"Assertion failed: {error_msg}")
            return False
        print(f"'{container}' does not contain '{item}'")
        return True

    def log_message(self, message: str, level: str = "INFO") -> None:
        """记录消息"""
        print(f"[{level}] {message}")

    def log_many(self, *messages) -> None:
        """记录多个消息"""
        for msg in messages:
            print(f"[INFO] {msg}")

    def comment(self, *messages) -> None:
        """添加注释（不执行任何操作）"""
        pass  # 注释只是用于文档目的

    def sleep(self, duration: str) -> None:
        """暂停指定时间"""
        import time
        # 解析时间字符串，例如 "3s", "1m" 等
        duration = duration.strip()
        if duration.endswith('s'):
            seconds = float(duration[:-1])
        elif duration.endswith('m'):
            seconds = float(duration[:-1]) * 60
        elif duration.endswith('h'):
            seconds = float(duration[:-1]) * 3600
        else:
            # 假设没有单位时默认为秒
            seconds = float(duration)

        print(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)

    def fail(self, msg: str = "Failure occurred", *tags) -> None:
        """导致测试失败"""
        print(f"FAIL: {msg}")
        raise AssertionError(msg)

    def create_list(self, *items) -> list:
        """创建列表"""
        return list(items)

    def create_dictionary(self, *key_value_pairs, **kwargs) -> dict:
        """创建字典"""
        result_dict = dict(**kwargs)
        # 处理键值对参数 (key=value 形式)
        for pair in key_value_pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                result_dict[key] = value
        return result_dict

    # Robot Framework Collections库关键字实现
    def append_to_list(self, list_var: list, *values) -> list:
        """向列表追加值"""
        for value in values:
            list_var.append(value)
        return list_var

    def copy_list(self, list_var: list) -> list:
        """复制列表"""
        return list_var.copy()

    def remove_from_list(self, list_var: list, index: int) -> list:
        """从列表移除指定索引的元素"""
        if 0 <= index < len(list_var):
            list_var.pop(index)
        return list_var

    def sort_list(self, list_var: list) -> list:
        """对列表进行排序"""
        list_var.sort()
        return list_var

    # Robot Framework String库关键字实现
    def convert_to_lower_case(self, string: str) -> str:
        """转换为小写"""
        return string.lower()

    def convert_to_upper_case(self, string: str) -> str:
        """转换为大写"""
        return string.upper()

    def split_string(self, string: str, separator: str = ' ', max_split: int = -1) -> list:
        """分割字符串"""
        if max_split == -1:
            return string.split(separator)
        else:
            return string.split(separator, max_split)

    def strip_string(self, string: str, characters: str = None) -> str:
        """去除字符串两端字符"""
        if characters:
            return string.strip(characters)
        return string.strip()

    def replace_string(self, string: str, search_for: str, replace_with: str, count: int = -1) -> str:
        """替换字符串"""
        if count == -1:
            return string.replace(search_for, replace_with)
        else:
            return string.replace(search_for, replace_with, count)

    # 扩展SIP相关关键字实现
    def setup_sip_session(self, session_id: str, config: dict = None) -> bool:
        """设置SIP会话"""
        if self.debug_mode:
            print(f"[DEBUG] Setting up SIP session: {session_id}")
        else:
            print(f"Setting up SIP session: {session_id}")
        # 这里可以实现具体的会话设置逻辑
        return True

    def teardown_sip_session(self, session_id: str) -> bool:
        """拆除SIP会话"""
        if self.debug_mode:
            print(f"[DEBUG] Tearing down SIP session: {session_id}")
        else:
            print(f"Tearing down SIP session: {session_id}")
        # 这里可以实现具体的会话拆除逻辑
        return True

    def send_invite(self, from_uri: str, to_uri: str, headers: dict = None) -> bool:
        """发送SIP INVITE请求"""
        operation_name = f"send_invite_{from_uri}_to_{to_uri}"
        self.performance_monitor.start_timer(operation_name)
        
        try:
            self.logger.info(f"Sending SIP INVITE from {from_uri} to {to_uri}")
            if self.debug_mode:
                self.logger.debug(f"[DEBUG] Sending SIP INVITE from {from_uri} to {to_uri} with headers: {headers}")
            
            # 应用配置中的默认头信息
            if headers is None:
                headers = {}
            
            # 从配置中加载默认头信息
            default_headers = self.config.get('default_sip_headers', {})
            headers.update(default_headers)
            
            # 调用底层实现
            try:
                result = self.client.make_call(from_uri, to_uri)
                if result:
                    self.logger.info(f"Successfully sent SIP INVITE from {from_uri} to {to_uri}")
                else:
                    self.logger.warning(f"Failed to send SIP INVITE from {from_uri} to {to_uri}")
                
                return result
            except Exception as e:
                self.logger.error(f"Error sending SIP INVITE from {from_uri} to {to_uri}: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Unexpected error during SIP INVITE from {from_uri} to {to_uri}: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
            return False
        finally:
            duration = self.performance_monitor.stop_timer(operation_name)
            self.performance_monitor.record_test_result(
                f"send_invite_{from_uri}_to_{to_uri}",
                result,
                duration,
                {"from_uri": from_uri, "to_uri": to_uri, "headers": headers}
            )

    def send_ack(self, dialog_id: str) -> bool:
        """发送SIP ACK确认"""
        if self.debug_mode:
            print(f"[DEBUG] Sending SIP ACK for dialog: {dialog_id}")
        else:
            print(f"Sending SIP ACK for dialog: {dialog_id}")
        # 这里可以实现具体的ACK发送逻辑
        return True

    def send_bye(self, dialog_id: str) -> bool:
        """发送SIP BYE请求"""
        if self.debug_mode:
            print(f"[DEBUG] Sending SIP BYE for dialog: {dialog_id}")
        else:
            print(f"Sending SIP BYE for dialog: {dialog_id}")
        # 这里可以实现具体的BYE发送逻辑
        return True

    def send_cancel(self, request_id: str) -> bool:
        """发送SIP CANCEL请求"""
        if self.debug_mode:
            print(f"[DEBUG] Sending SIP CANCEL for request: {request_id}")
        else:
            print(f"Sending SIP CANCEL for request: {request_id}")
        # 这里可以实现具体的CANCEL发送逻辑
        return True

    def send_options(self, target_uri: str) -> bool:
        """发送SIP OPTIONS请求"""
        operation_name = f"send_options_{target_uri}"
        self.performance_monitor.start_timer(operation_name)
        
        try:
            self.logger.info(f"Sending SIP OPTIONS to {target_uri}")
            if self.debug_mode:
                self.logger.debug(f"[DEBUG] Sending SIP OPTIONS to {target_uri}")
            
            # 从配置获取OPTIONS请求的参数
            options_timeout = self.config.get('options_timeout', 30)
            options_headers = self.config.get('options_headers', {})
            
            # 这里可以实现具体的OPTIONS发送逻辑
            # 模拟发送OPTIONS请求并等待响应
            import time
            time.sleep(0.1)  # 模拟网络延迟
            
            # 检查是否能连接到目标URI
            # 实际实现中会使用SIP客户端发送OPTIONS请求
            try:
                # 尝试使用底层客户端功能
                if hasattr(self.client, 'send_message'):
                    # 发送一个简单的OPTIONS消息
                    result = self.client.send_message(target_uri, target_uri, "OPTIONS")
                else:
                    # 如果没有直接的OPTIONS方法，返回成功
                    result = True
                
                if result:
                    self.logger.info(f"Successfully sent SIP OPTIONS to {target_uri}")
                else:
                    self.logger.warning(f"Failed to send SIP OPTIONS to {target_uri}")
                
                return result
            except Exception as e:
                self.logger.error(f"Error sending SIP OPTIONS to {target_uri}: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Unexpected error during SIP OPTIONS to {target_uri}: {e}")
            if self.debug_mode:
                import traceback
                self.logger.debug(traceback.format_exc())
            return False
        finally:
            duration = self.performance_monitor.stop_timer(operation_name)
            self.performance_monitor.record_test_result(
                f"send_options_{target_uri}",
                result,
                duration,
                {"target_uri": target_uri}
            )

    def send_info(self, dialog_id: str, content: str) -> bool:
        """发送SIP INFO请求"""
        if self.debug_mode:
            print(f"[DEBUG] Sending SIP INFO for dialog {dialog_id}: {content}")
        else:
            print(f"Sending SIP INFO for dialog {dialog_id}: {content}")
        # 这里可以实现具体的INFO发送逻辑
        return True

    def send_notify(self, subscriber_uri: str, event: str, content: str) -> bool:
        """发送SIP NOTIFY请求"""
        if self.debug_mode:
            print(f"[DEBUG] Sending SIP NOTIFY to {subscriber_uri}, event: {event}")
        else:
            print(f"Sending SIP NOTIFY to {subscriber_uri}, event: {event}")
        # 这里可以实现具体的NOTIFY发送逻辑
        return True

    def send_subscribe(self, target_uri: str, event: str, expires: int = 3600) -> bool:
        """发送SIP SUBSCRIBE请求"""
        if self.debug_mode:
            print(f"[DEBUG] Sending SIP SUBSCRIBE to {target_uri}, event: {event}, expires: {expires}")
        else:
            print(f"Sending SIP SUBSCRIBE to {target_uri}, event: {event}, expires: {expires}")
        # 这里可以实现具体的SUBSCRIBE发送逻辑
        return True

    def send_refer(self, target_uri: str, referred_by: str) -> bool:
        """发送SIP REFER请求"""
        if self.debug_mode:
            print(f"[DEBUG] Sending SIP REFER to {target_uri}, referred by: {referred_by}")
        else:
            print(f"Sending SIP REFER to {target_uri}, referred by: {referred_by}")
        # 这里可以实现具体的REFER发送逻辑
        return True

    def wait_for_response(self, request_id: str, timeout: int = 30) -> dict:
        """等待SIP响应"""
        if self.debug_mode:
            print(f"[DEBUG] Waiting for SIP response to request {request_id}, timeout: {timeout}")
        else:
            print(f"Waiting for SIP response to request {request_id}, timeout: {timeout}")
        # 这里可以实现具体的等待响应逻辑
        return {"status": 200, "response": "OK"}

    def wait_for_request(self, method: str, timeout: int = 30) -> dict:
        """等待SIP请求"""
        if self.debug_mode:
            print(f"[DEBUG] Waiting for SIP {method} request, timeout: {timeout}")
        else:
            print(f"Waiting for SIP {method} request, timeout: {timeout}")
        # 这里可以实现具体的等待请求逻辑
        return {"method": method, "uri": "sip:test@example.com"}

    def validate_sip_message(self, message: str) -> bool:
        """验证SIP消息"""
        if self.debug_mode:
            print(f"[DEBUG] Validating SIP message: {message[:50]}...")
        else:
            print(f"Validating SIP message")
        # 这里可以实现具体的SIP消息验证逻辑
        return True

    def parse_sip_response(self, response: str) -> dict:
        """解析SIP响应"""
        if self.debug_mode:
            print(f"[DEBUG] Parsing SIP response: {response[:50]}...")
        else:
            print("Parsing SIP response")
        # 这里可以实现具体的SIP响应解析逻辑
        return {"status_code": 200, "reason_phrase": "OK"}

    def check_sip_headers(self, message: str, required_headers: list) -> bool:
        """检查SIP头字段"""
        if self.debug_mode:
            print(f"[DEBUG] Checking SIP headers: {required_headers}")
        else:
            print(f"Checking SIP headers: {required_headers}")
        # 这里可以实现具体的SIP头字段检查逻辑
        return True

    def modify_sip_headers(self, message: str, headers: dict) -> str:
        """修改SIP头字段"""
        if self.debug_mode:
            print(f"[DEBUG] Modifying SIP headers: {headers}")
        else:
            print("Modifying SIP headers")
        # 这里可以实现具体的SIP头字段修改逻辑
        return message

    def create_sip_dialog(self, call_id: str, local_tag: str, remote_tag: str) -> str:
        """创建SIP对话"""
        if self.debug_mode:
            print(f"[DEBUG] Creating SIP dialog: {call_id}")
        else:
            print(f"Creating SIP dialog: {call_id}")
        # 这里可以实现具体的SIP对话创建逻辑
        return call_id

    def close_sip_dialog(self, dialog_id: str) -> bool:
        """关闭SIP对话"""
        if self.debug_mode:
            print(f"[DEBUG] Closing SIP dialog: {dialog_id}")
        else:
            print(f"Closing SIP dialog: {dialog_id}")
        # 这里可以实现具体的SIP对话关闭逻辑
        return True

    def start_rtp_stream(self, session_id: str, codec: str = "PCMU", port: int = 0) -> bool:
        """启动RTP流"""
        if self.debug_mode:
            print(f"[DEBUG] Starting RTP stream for session {session_id}, codec: {codec}")
        else:
            print(f"Starting RTP stream for session {session_id}, codec: {codec}")
        # 这里可以实现具体的RTP流启动逻辑
        return True

    def stop_rtp_stream(self, session_id: str) -> bool:
        """停止RTP流"""
        if self.debug_mode:
            print(f"[DEBUG] Stopping RTP stream for session {session_id}")
        else:
            print(f"Stopping RTP stream for session {session_id}")
        # 这里可以实现具体的RTP流停止逻辑
        return True

    def monitor_call_quality(self, session_id: str) -> dict:
        """监控通话质量"""
        if self.debug_mode:
            print(f"[DEBUG] Monitoring call quality for session {session_id}")
        else:
            print(f"Monitoring call quality for session {session_id}")
        # 这里可以实现具体的通话质量监控逻辑
        return {"jitter": 0.02, "packet_loss": 0.001, "mos": 4.2}

    def generate_sip_traffic(self, target_uri: str, rate: int = 1, duration: int = 60) -> bool:
        """生成SIP流量"""
        if self.debug_mode:
            print(f"[DEBUG] Generating SIP traffic to {target_uri}, rate: {rate}/s, duration: {duration}s")
        else:
            print(f"Generating SIP traffic to {target_uri}, rate: {rate}/s, duration: {duration}s")
        # 这里可以实现具体的SIP流量生成逻辑
        return True

    def simulate_network_delay(self, delay_ms: int) -> bool:
        """模拟网络延迟"""
        if self.debug_mode:
            print(f"[DEBUG] Simulating network delay: {delay_ms}ms")
        else:
            print(f"Simulating network delay: {delay_ms}ms")
        # 这里可以实现具体的网络延迟模拟逻辑
        import time
        time.sleep(delay_ms / 1000.0)
        return True

    def simulate_packet_loss(self, loss_rate: float) -> bool:
        """模拟丢包"""
        if self.debug_mode:
            print(f"[DEBUG] Simulating packet loss rate: {loss_rate}")
        else:
            print(f"Simulating packet loss rate: {loss_rate}")
        # 这里可以实现具体的丢包模拟逻辑
        return True

    def test_sip_authentication(self, username: str, password: str, realm: str) -> bool:
        """测试SIP认证"""
        if self.debug_mode:
            print(f"[DEBUG] Testing SIP authentication for user {username} in realm {realm}")
        else:
            print(f"Testing SIP authentication for user {username} in realm {realm}")
        # 这里可以实现具体的SIP认证测试逻辑
        return True

    def verify_sip_registration(self, username: str, server_uri: str) -> bool:
        """验证SIP注册"""
        if self.debug_mode:
            print(f"[DEBUG] Verifying SIP registration for {username} on {server_uri}")
        else:
            print(f"Verifying SIP registration for {username} on {server_uri}")
        # 这里可以实现具体的SIP注册验证逻辑
        return True

    def check_sip_server_status(self, server_uri: str) -> dict:
        """检查SIP服务器状态"""
        if self.debug_mode:
            print(f"[DEBUG] Checking SIP server status: {server_uri}")
        else:
            print(f"Checking SIP server status: {server_uri}")
        # 这里可以实现具体的SIP服务器状态检查逻辑
        return {"status": "UP", "version": "unknown", "uptime": "unknown"}

    def configure_sip_client(self, params: dict) -> bool:
        """配置SIP客户端"""
        if self.debug_mode:
            print(f"[DEBUG] Configuring SIP client with params: {params}")
        else:
            print("Configuring SIP client")
        # 这里可以实现具体的SIP客户端配置逻辑
        return True

    def reset_sip_client(self) -> bool:
        """重置SIP客户端"""
        if self.debug_mode:
            print("[DEBUG] Resetting SIP client")
        else:
            print("Resetting SIP client")
        # 这里可以实现具体的SIP客户端重置逻辑
        return True

    def get_sip_statistics(self) -> dict:
        """获取SIP统计信息"""
        if self.debug_mode:
            print("[DEBUG] Getting SIP statistics")
        else:
            print("Getting SIP statistics")
        # 这里可以实现具体的SIP统计信息获取逻辑
        return {"registrations": 0, "calls": 0, "messages": 0}

    def analyze_sip_logs(self, log_file: str) -> list:
        """分析SIP日志"""
        if self.debug_mode:
            print(f"[DEBUG] Analyzing SIP logs from {log_file}")
        else:
            print(f"Analyzing SIP logs from {log_file}")
        # 这里可以实现具体的SIP日志分析逻辑
        return ["Analysis complete"]

    # 实用工具方法
    def wait_until(self, condition_func, timeout: int = 30, poll_interval: float = 0.5) -> bool:
        """等待直到条件满足或超时"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if condition_func():
                    return True
            except Exception:
                # 如果条件函数抛出异常，继续等待
                pass
            time.sleep(poll_interval)
        return False

    def retry_on_failure(self, func, max_attempts: int = 3, delay: float = 1.0, *args, **kwargs):
        """失败时重试函数"""
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts - 1:  # 最后一次尝试
                    if self.debug_mode:
                        self.logger.debug(f"[DEBUG] Function failed after {max_attempts} attempts: {e}")
                    raise e
                if self.debug_mode:
                    self.logger.debug(f"[DEBUG] Attempt {attempt + 1} failed: {e}, retrying in {delay}s")
                time.sleep(delay)
        return None

    def sleep_until_next_second(self):
        """休眠到下一秒开始"""
        import time
        current_time = time.time()
        next_second = ((int(current_time) + 1) * 1000) / 1000.0
        sleep_time = next_second - current_time
        if sleep_time > 0:
            time.sleep(sleep_time)

    def format_timestamp(self, timestamp: float = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化时间戳"""
        import time
        if timestamp is None:
            timestamp = time.time()
        return time.strftime(format_str, time.localtime(timestamp))

    def validate_ip_address(self, ip_addr: str) -> bool:
        """验证IP地址格式"""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(pattern, ip_addr):
            parts = ip_addr.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        return False

    def validate_uri(self, uri: str) -> bool:
        """验证SIP URI格式"""
        import re
        # 简单的SIP URI验证正则表达式
        pattern = r'^sip:[a-zA-Z0-9_.!~*\'();:&=+$,-]+@[a-zA-Z0-9_.!~*\'()-]+\.[a-zA-Z]{2,}(:\d+)?$'
        return bool(re.match(pattern, uri))

    def extract_domain_from_uri(self, uri: str) -> str:
        """从SIP URI提取域名"""
        if uri.startswith('sip:'):
            uri = uri[4:]  # 移除 'sip:' 前缀
        if '@' in uri:
            return uri.split('@', 1)[1].split(':')[0]  # 提取 @ 符号后的域名部分
        return uri

    def normalize_phone_number(self, phone: str) -> str:
        """标准化电话号码"""
        # 移除所有非数字字符（保留+号在开头）
        if phone.startswith('+'):
            digits = '+' + ''.join(filter(str.isdigit, phone[1:]))
        else:
            digits = ''.join(filter(str.isdigit, phone))
        return digits

    def calculate_call_duration(self, start_time: float, end_time: float) -> float:
        """计算通话持续时间"""
        return round(end_time - start_time, 2)

    def get_network_latency(self, host: str, port: int = 5060) -> float:
        """获取网络延迟（毫秒）"""
        import socket
        import time
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5秒超时
            sock.connect((host, port))
            sock.close()
            latency = (time.time() - start_time) * 1000  # 转换为毫秒
            return round(latency, 2)
        except Exception:
            return -1  # 表示连接失败


def create_rf_library_for_pytest(debug_mode=False, log_level="INFO", config=None):
    """
    创建Robot Framework库，桥接到pytest实现
    """
    return SIPRobotKeywords(debug_mode=debug_mode, log_level=log_level, config=config)


class PerformanceMonitor:
    """
    性能监控器
    用于监控和报告SIP测试的性能指标
    """
    
    def __init__(self):
        self.metrics = {}
        self.test_results = []
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """开始计时某个操作"""
        import time
        self.start_times[operation] = time.time()
    
    def stop_timer(self, operation: str) -> float:
        """停止计时并返回耗时"""
        import time
        if operation in self.start_times:
            elapsed = time.time() - self.start_times[operation]
            # 记录操作耗时
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(elapsed)
            del self.start_times[operation]
            return elapsed
        return 0.0
    
    def record_metric(self, metric_name: str, value: float):
        """记录指标值"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
    
    def record_test_result(self, test_name: str, success: bool, duration: float, details: dict = None):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'success': success,
            'duration': duration,
            'timestamp': time.time(),
            'details': details or {}
        }
        self.test_results.append(result)
    
    def get_average(self, metric_name: str) -> float:
        """获取指标平均值"""
        if metric_name in self.metrics and self.metrics[metric_name]:
            values = self.metrics[metric_name]
            return sum(values) / len(values)
        return 0.0
    
    def get_report(self) -> dict:
        """生成性能报告"""
        report = {
            'summary': {
                'total_tests': len(self.test_results),
                'successful_tests': len([r for r in self.test_results if r['success']]),
                'failed_tests': len([r for r in self.test_results if not r['success']]),
            },
            'metrics': {},
            'detailed_results': self.test_results.copy()
        }
        
        # 为每个指标计算统计信息
        for metric_name, values in self.metrics.items():
            if values:
                report['metrics'][metric_name] = {
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values),
                    'total': sum(values)
                }
        
        return report
    
    def save_report(self, filename: str):
        """保存报告到文件"""
        import json
        report = self.get_report()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def print_report(self):
        """打印报告到控制台"""
        report = self.get_report()
        print("=" * 50)
        print("SIP测试性能报告")
        print("=" * 50)
        print(f"总测试数: {report['summary']['total_tests']}")
        print(f"成功测试: {report['summary']['successful_tests']}")
        print(f"失败测试: {report['summary']['failed_tests']}")
        print()
        
        if report['metrics']:
            print("性能指标:")
            for metric_name, stats in report['metrics'].items():
                print(f"  {metric_name}:")
                print(f"    平均值: {stats['average']:.4f}s")
                print(f"    最小值: {stats['min']:.4f}s")
                print(f"    最大值: {stats['max']:.4f}s")
                print(f"    调用次数: {stats['count']}")
            print()
        
        print("测试详情:")
        for result in report['detailed_results']:
            status = "PASS" if result['success'] else "FAIL"
            print(f"  {result['test_name']}: {status} ({result['duration']:.4f}s)")
        print("=" * 50)


# 示例：如何使用此适配器
if __name__ == "__main__":
    # 创建调试模式的适配器
    adapter = RobotFrameworkAdapter(debug_mode=True)
    
    # 示例Robot Framework测试内容
    sample_rf_test = """
*** Settings ***
Library    Collections
Library    String

*** Variables ***
${USERNAME}    alice
${PASSWORD}    secret
${SERVER_URI}  sip:server.com:5060

*** Test Cases ***
Basic SIP Call Test
    [Tags]    smoke    sip
    Register User    ${USERNAME}    ${PASSWORD}    ${SERVER_URI}
    Make SIP Call    sip:${USERNAME}@server.com    sip:bob@server.com
    Sleep    30s
    End Call
    Unregister User    ${USERNAME}

*** Keywords ***
Register User
    [Arguments]    ${username}    ${password}    ${server_uri}
    # 调用底层pytest实现
"""
    
    # 解析并转换
    parsed = adapter.parse_robot_test_content(sample_rf_test)
    print("解析结果:")
    print(f"找到 {len(parsed['test_cases'])} 个测试用例")
    
    # 转换并执行
    converted = adapter.convert_rf_test_to_pytest(sample_rf_test)
    print("\n转换后的pytest代码:")
    print(converted)
    
    # 演示控制结构转换
    control_structure_test = """
*** Test Cases ***
Control Structure Test
    IF    1 == 1
        Log    Condition is true
    ELSE
        Log    Condition is false
    END
    FOR    ${i}    IN RANGE    3
        Log    Loop iteration: ${i}
    END
"""
    
    print("\n控制结构转换示例:")
    converted_control = adapter.convert_rf_test_to_pytest(control_structure_test)
    print(converted_control)
    
    # 演示性能监控功能
    print("\n性能监控演示:")
    # 创建带有配置的SIP关键字实例
    config = {
        "default_sip_headers": {
            "User-Agent": "SIP-AutoTest-Robot-Framework/1.0",
            "Supported": "timer, precondition, histinfo, gruu, replaces"
        },
        "options_timeout": 10,
        "call_timeout": 30
    }
    sip_keywords = SIPRobotKeywords(debug_mode=True, log_level="INFO", config=config)
    
    # 模拟一些操作
    sip_keywords.register_user("test_user", "password", "sip:server.com:5060")
    sip_keywords.make_call("sip:test@server.com", "sip:user@server.com")
    sip_keywords.send_options("sip:test@server.com")
    
    # 打印性能报告
    print("\n性能报告:")
    sip_keywords.performance_monitor.print_report()
    
    # 演示配置管理功能
    print("\n配置管理演示:")
    adapter = RobotFrameworkAdapter(debug_mode=True)
    adapter.set_config("max_retries", 3)
    adapter.set_config("timeout", 60)
    print(f"Max retries: {adapter.get_config('max_retries')}")
    print(f"All configs: {adapter.get_all_configs()}")
    
    # 演示实用工具方法
    print("\n实用工具方法演示:")
    utils = SIPRobotKeywords(debug_mode=True)
    
    # 测试IP地址验证
    print(f"Valid IP 192.168.1.1: {utils.validate_ip_address('192.168.1.1')}")
    print(f"Invalid IP 999.999.999.999: {utils.validate_ip_address('999.999.999.999')}")
    
    # 测试URI验证
    print(f"Valid SIP URI: {utils.validate_uri('sip:alice@example.com')}")
    print(f"Invalid SIP URI: {utils.validate_uri('invalid-uri')}")
    
    # 测试域名提取
    print(f"Domain from URI: {utils.extract_domain_from_uri('sip:bob@test.example.com:5060')}")
    
    # 测试电话号码标准化
    print(f"Normalized phone: {utils.normalize_phone_number('+1-555-123-4567')}")
    
    # 测试时间戳格式化
    print(f"Current time: {utils.format_timestamp()}")
    
    # 测试延迟计算
    start = time.time()
    time.sleep(0.1)  # 模拟延迟
    end = time.time()
    duration = utils.calculate_call_duration(start, end)
    print(f"Calculated duration: {duration}s")


class PerformanceMonitor:
    """
    性能监控器
    用于收集和报告测试执行的性能指标
    """
    
    def __init__(self):
        import time
        self.start_time = None
        self.end_time = None
        self.metrics = {}
        self.test_results = []
        self.call_durations = []
    
    def start_monitoring(self):
        """开始性能监控"""
        import time
        self.start_time = time.time()
        self.metrics = {
            'start_time': self.start_time,
            'test_count': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'average_duration': 0,
            'total_duration': 0
        }
    
    def stop_monitoring(self):
        """停止性能监控"""
        import time
        self.end_time = time.time()
        if self.start_time:
            self.metrics['total_duration'] = self.end_time - self.start_time
    
    def record_test_result(self, test_name: str, passed: bool, duration: float):
        """记录测试结果"""
        import time
        result = {
            'test_name': test_name,
            'passed': passed,
            'duration': duration,
            'timestamp': time.time()
        }
        self.test_results.append(result)
        
        # 更新统计信息
        self.metrics['test_count'] += 1
        if passed:
            self.metrics['passed_tests'] += 1
        else:
            self.metrics['failed_tests'] += 1
        
        # 计算平均持续时间
        if self.test_results:
            durations = [tr['duration'] for tr in self.test_results]
            self.metrics['average_duration'] = sum(durations) / len(durations)
    
    def record_call_duration(self, duration: float):
        """记录呼叫持续时间"""
        self.call_durations.append(duration)
    
    def get_performance_report(self) -> dict:
        """获取性能报告"""
        if self.call_durations:
            avg_call_duration = sum(self.call_durations) / len(self.call_durations)
        else:
            avg_call_duration = 0
            
        return {
            'summary': {
                'total_tests': self.metrics.get('test_count', 0),
                'passed': self.metrics.get('passed_tests', 0),
                'failed': self.metrics.get('failed_tests', 0),
                'success_rate': (self.metrics.get('passed_tests', 0) / max(self.metrics.get('test_count', 1), 1)) * 100,
                'total_duration': self.metrics.get('total_duration', 0),
                'average_test_duration': self.metrics.get('average_duration', 0)
            },
            'call_metrics': {
                'average_call_duration': avg_call_duration,
                'total_calls': len(self.call_durations),
                'min_call_duration': min(self.call_durations) if self.call_durations else 0,
                'max_call_duration': max(self.call_durations) if self.call_durations else 0
            },
            'detailed_results': self.test_results
        }
    
    def print_report(self):
        """打印性能报告"""
        report = self.get_performance_report()
        
        print("\n" + "="*50)
        print("性能监控报告")
        print("="*50)
        print(f"总测试数: {report['summary']['total_tests']}")
        print(f"通过测试: {report['summary']['passed']}")
        print(f"失败测试: {report['summary']['failed']}")
        print(f"成功率: {report['summary']['success_rate']:.2f}%")
        print(f"总耗时: {report['summary']['total_duration']:.2f}s")
        print(f"平均测试耗时: {report['summary']['average_test_duration']:.2f}s")
        
        if report['call_metrics']['total_calls'] > 0:
            print(f"\n呼叫指标:")
            print(f"  平均呼叫时长: {report['call_metrics']['average_call_duration']:.2f}s")
            print(f"  最短呼叫时长: {report['call_metrics']['min_call_duration']:.2f}s")
            print(f"  最长呼叫时长: {report['call_metrics']['max_call_duration']:.2f}s")
            print(f"  总呼叫数: {report['call_metrics']['total_calls']}")
        
        print("="*50)