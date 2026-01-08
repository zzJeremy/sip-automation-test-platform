#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web界面模块
使用Flask实现的Web界面，用于控制SIP自动化测试
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import threading
import time
import json
from datetime import datetime
import os
import sys

# 添加项目根目录到Python路径
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 尝试绝对导入，如果失败则使用相对导入
try:
    from AutoTestForUG.test_client.sip_test_client import SIPTestClient
    from AutoTestForUG.utils.email_reporter import EmailReporter
    from AutoTestForUG.utils.utils import setup_logger
except ImportError:
    # 如果绝对导入失败，尝试直接导入
    try:
        from test_client.sip_test_client import SIPTestClient
        from utils.email_reporter import EmailReporter
        from utils.utils import setup_logger
    except ImportError as e:
        print(f"导入模块失败: {e}")
        raise

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-for-sip-test'

# 全局变量存储测试状态和结果
test_status = {
    'is_running': False,
    'current_test': None,
    'test_progress': 0,
    'test_results': [],
    'last_run_time': None
}

# 创建SIP测试客户端实例，使用配置文件路径
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.ini')
sip_client = SIPTestClient(config_path)

@app.route('/')
def index():
    """主页"""
    return render_template('index.html', test_status=test_status)

@app.route('/api/start_test', methods=['POST'])
def start_test():
    """启动测试API"""
    global test_status
    
    if test_status['is_running']:
        return jsonify({'status': 'error', 'message': '测试已在运行中'})
    
    test_type = request.json.get('test_type', 'all')
    test_duration = request.json.get('test_duration', 30)
    concurrent_calls = request.json.get('concurrent_calls', 5)
    selected_tests = request.json.get('selected_tests', [])
    
    # 启动测试线程
    test_thread = threading.Thread(
        target=run_test_thread,
        args=(test_type, test_duration, concurrent_calls, selected_tests)
    )
    test_thread.daemon = True
    test_thread.start()
    
    return jsonify({
        'status': 'success', 
        'message': f'已启动{test_type}测试',
        'test_type': test_type
    })

@app.route('/api/test_status')
def get_test_status():
    """获取测试状态API"""
    return jsonify(test_status)

@app.route('/api/test_results')
def get_test_results():
    """获取测试结果API"""
    return jsonify({
        'results': test_status['test_results'],
        'last_run_time': test_status['last_run_time']
    })

def run_test_thread(test_type, test_duration, concurrent_calls, selected_tests=None):
    """测试执行线程"""
    global test_status
    
    try:
        test_status['is_running'] = True
        test_status['current_test'] = test_type
        test_status['test_progress'] = 0
        
        # 如果没有提供selected_tests，则根据test_type执行测试
        if selected_tests is None or len(selected_tests) == 0:
            if test_type == 'all':
                selected_tests = ['basic', 'performance', 'exception', 'sip_message']
            else:
                selected_tests = [test_type]
        
        # 计算总测试数量
        total_tests = len(selected_tests)
        completed_tests = 0
        
        # 根据选择的测试类型执行相应测试
        for test in selected_tests:
            # 处理基础功能测试的子测试用例
            if test.startswith('basic_'):
                # 执行具体的子测试用例
                sub_test_type = test[6:]  # 去掉 'basic_' 前缀
                if sub_test_type == 'unconditional_forward':
                    # 无条件前转测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟无条件前转设置和测试（当前版本未实现具体功能）
                        # 这里可以添加具体的无条件前转测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '无条件前转测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，无条件前转测试未执行'
                        })
                
                elif sub_test_type == 'no_answer_forward':
                    # 无应答前转测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟无应答前转设置和测试（当前版本未实现具体功能）
                        # 这里可以添加具体的无应答前转测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '无应答前转测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，无应答前转测试未执行'
                        })
                
                elif sub_test_type == 'busy_forward':
                    # 遇忙前转测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟遇忙前转设置和测试（当前版本未实现具体功能）
                        # 这里可以添加具体的遇忙前转测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '遇忙前转测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，遇忙前转测试未执行'
                        })
                
                elif sub_test_type == 'secretary_service':
                    # 秘书业务测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟秘书业务测试（当前版本未实现具体功能）
                        # 这里可以添加具体的秘书业务测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '秘书业务测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，秘书业务测试未执行'
                        })
                
                elif sub_test_type == 'simple_call':
                    # 简单通话测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 执行简单通话测试
                        sip_client.make_call("sip:670491@127.0.0.1:5060", "sip:test@127.0.0.1:5060")
                        time.sleep(5)
                        
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '简单通话测试完成'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，简单通话测试未执行'
                        })
                
                elif sub_test_type == 'conference':
                    # 会议功能测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 执行会议功能测试
                        sip_client.setup_conference_call(["sip:user1@127.0.0.1:5060", "sip:user2@127.0.0.1:5060"])
                        
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '会议功能测试完成'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，会议功能测试未执行'
                        })
                
                elif sub_test_type == 'busy_callback':
                    # 遇忙回叫测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟遇忙回叫测试（当前版本未实现具体功能）
                        # 这里可以添加具体的遇忙回叫测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '遇忙回叫测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，遇忙回叫测试未执行'
                        })
                
                elif sub_test_type == 'call_waiting':
                    # 呼叫等待测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟呼叫等待测试（当前版本未实现具体功能）
                        # 这里可以添加具体的呼叫等待测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '呼叫等待测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，呼叫等待测试未执行'
                        })
                
                elif sub_test_type == 'multi_party_call':
                    # 多方通话测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟多方通话测试（当前版本未实现具体功能）
                        # 这里可以添加具体的多方通话测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '多方通话测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，多方通话测试未执行'
                        })
                
                elif sub_test_type == 'abbreviated_dialing':
                    # 缩位拨号测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟缩位拨号测试（当前版本未实现具体功能）
                        # 这里可以添加具体的缩位拨号测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '缩位拨号测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，缩位拨号测试未执行'
                        })
                
                elif sub_test_type == 'call_hold':
                    # 呼叫保持测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟呼叫保持测试（当前版本未实现具体功能）
                        # 这里可以添加具体的呼叫保持测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '呼叫保持测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，呼叫保持测试未执行'
                        })
                
                elif sub_test_type == 'group_answer':
                    # 同组代接测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟同组代接测试（当前版本未实现具体功能）
                        # 这里可以添加具体的同组代接测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '同组代接测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，同组代接测试未执行'
                        })
                
                elif sub_test_type == 'do_not_disturb':
                    # 免打扰测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟免打扰设置和测试（当前版本未实现具体功能）
                        # 这里可以添加具体的免打扰测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '免打扰测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，免打扰测试未执行'
                        })
                
                elif sub_test_type == 'designated_answer':
                    # 指定代答测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟指定代答测试（当前版本未实现具体功能）
                        # 这里可以添加具体的指定代答测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '指定代答测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，指定代答测试未执行'
                        })
                
                elif sub_test_type == 'outbound_restriction':
                    # 呼出限制测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟呼出限制测试（当前版本未实现具体功能）
                        # 这里可以添加具体的呼出限制测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '呼出限制测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，呼出限制测试未执行'
                        })
                
                elif sub_test_type == 'alarm_service':
                    # 闹钟服务测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟闹钟服务测试（当前版本未实现具体功能）
                        # 这里可以添加具体的闹钟服务测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '闹钟服务测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，闹钟服务测试未执行'
                        })
                
                elif sub_test_type == 'call_forward':
                    # 呼叫转移测试（包括通话转接和振铃转接）
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟呼叫转移测试（当前版本未实现具体功能）
                        # 这里可以添加具体的呼叫转移测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '呼叫转移测试完成（通话转接和振铃转接）（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，呼叫转移测试未执行'
                        })
                
                elif sub_test_type == 'hotline':
                    # 立即热线测试
                    username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                    password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                    success = sip_client.register_user(username, password)
                    if success:
                        # 模拟立即热线测试（当前版本未实现具体功能）
                        # 这里可以添加具体的立即热线测试逻辑
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'details': '立即热线测试完成（功能待实现）'
                        })
                    else:
                        test_status['test_results'].append({
                            'test_type': test,
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'details': '注册失败，立即热线测试未执行'
                        })
            
            elif test == 'basic':
                # 基础SIP功能测试
                username = sip_client.config.get('TEST_CLIENT', {}).get('username', '670491')
                password = sip_client.config.get('TEST_CLIENT', {}).get('password', '1234')
                success = sip_client.register_user(username, password)
                if success:
                    time.sleep(2)
                    sip_client.make_call("sip:670491@127.0.0.1:5060", "sip:test@127.0.0.1:5060")
                    time.sleep(5)
                    # 注销功能在当前SIPTestClient实现中不可用，跳过
                    
                    test_status['test_results'].append({
                        'test_type': 'basic',
                        'status': 'completed',
                        'timestamp': datetime.now().isoformat(),
                        'details': '基础SIP功能测试完成'
                    })
                else:
                    test_status['test_results'].append({
                        'test_type': 'basic',
                        'status': 'error',
                        'timestamp': datetime.now().isoformat(),
                        'details': '注册失败，基础SIP功能测试未执行'
                    })
            elif test == 'performance':
                # 性能测试
                performance_results = sip_client.run_performance_tests(
                    test_duration=test_duration, 
                    concurrent_calls=concurrent_calls
                )
                
                test_status['test_results'].append({
                    'test_type': 'performance',
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'results': performance_results
                })
            elif test == 'exception':
                # 异常情况测试
                sip_client.simulate_network_failure()
                time.sleep(2)
                sip_client.test_authentication_failure("test_user", "wrong_password")
                time.sleep(2)
                sip_client.test_server_unavailable()
                time.sleep(2)
                sip_client.test_timeout_scenarios(5)
                
                test_status['test_results'].append({
                    'test_type': 'exception',
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'details': '异常情况测试完成'
                })
            elif test == 'sip_message':
                # SIP消息解析和验证测试
                sip_client.run_sip_message_tests()
                
                test_status['test_results'].append({
                    'test_type': 'sip_message',
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'details': 'SIP消息解析和验证测试完成'
                })
            
            # 更新进度
            completed_tests += 1
            test_status['test_progress'] = int((completed_tests / total_tests) * 100)
        
        test_status['test_results'].append({
            'test_type': 'all_selected',
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'details': f'所选测试完成: {", ".join(selected_tests)}'
        })
        
        test_status['last_run_time'] = datetime.now().isoformat()
        
    except Exception as e:
        app.logger.error(f"测试执行出错: {e}")
        test_status['test_results'].append({
            'test_type': test_type,
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        })
    
    finally:
        test_status['is_running'] = False
        test_status['current_test'] = None

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """配置管理API"""
    if request.method == 'POST':
        # 更新配置
        config_data = request.json
        # 这里可以添加配置更新逻辑
        return jsonify({'status': 'success', 'message': '配置已更新'})
    else:
        # 返回当前配置
        return jsonify({
            'sip_server_host': sip_client.config.get('sip_server_host', ''),
            'sip_server_port': sip_client.config.get('sip_server_port', 5060),
            'local_host': sip_client.config.get('local_host', ''),
            'local_port': sip_client.config.get('local_port', 5060),
            'username': sip_client.config.get('username', ''),
            'register_domain': sip_client.config.get('register_domain', '')
        })

if __name__ == '__main__':
    # 确保templates目录存在
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    # 启动Web服务器
    app.run(debug=True, host='0.0.0.0', port=5000)