#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web界面模块
使用Flask实现的Web界面，用于控制SIP自动化测试
"""

from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS  # 添加CORS支持
from flask_socketio import SocketIO, emit  # 添加WebSocket支持
import threading
import time
import json
from datetime import datetime, timedelta
import os
import sys
import uuid

# 添加项目根目录到Python路径
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 直接使用绝对路径导入
try:
    from test_client.sip_test_client import SIPTestClient
    from utils.email_reporter import EmailReporter
    from utils.utils import setup_logger
    # 为了防止导入错误，暂时不导入SIPCallFlow，稍后在函数内部导入
except ImportError as e:
    print(f"导入模块失败: {e}")
    raise


def discover_test_cases():
    """发现所有可用的测试用例"""
    test_cases = []
    
    # 导入测试用例相关模块
    try:
        from test_cases.sip_test_case import (
            BasicCallTestCase, 
            SIPMessageFormatTestCase, 
            SIPResponseTestCase,
            CallForwardingUnconditionalTestCase,
            CallForwardingBusyTestCase,
            CallForwardingNoAnswerTestCase
        )
        
        # 定义测试用例映射
        case_map = {
            'basic_call': {
                'name': '基础呼叫测试',
                'description': '验证基础SIP呼叫流程: INVITE -> 200 OK -> ACK -> BYE',
                'type': 'functional',
                'category': 'basic'
            },
            'message_format': {
                'name': 'SIP消息格式测试',
                'description': '验证SIP消息格式是否符合RFC规范',
                'type': 'validation',
                'category': 'protocol'
            },
            'response_validation': {
                'name': 'SIP响应验证测试',
                'description': '验证SIP服务器响应是否符合预期',
                'type': 'validation',
                'category': 'protocol'
            },
            'unconditional_forwarding': {
                'name': '无条件呼叫前转测试',
                'description': '验证SIP无条件前转功能: A呼叫B，B无条件前转到C',
                'type': 'business',
                'category': 'advanced'
            },
            'busy_forwarding': {
                'name': '遇忙呼叫前转测试',
                'description': '验证SIP遇忙前转功能: A呼叫B，B遇忙时前转到C',
                'type': 'business',
                'category': 'advanced'
            },
            'noanswer_forwarding': {
                'name': '无应答呼叫前转测试',
                'description': '验证SIP无应答前转功能: A呼叫B，B无应答时前转到C',
                'type': 'business',
                'category': 'advanced'
            }
        }
        
        for case_type, details in case_map.items():
            test_cases.append({
                'id': case_type,
                'name': details['name'],
                'description': details['description'],
                'type': details['type'],
                'category': details['category']
            })
        
    except ImportError as e:
        app.logger.error(f"发现测试用例失败: {e}")
    
    return test_cases

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-for-sip-test'

# 启用CORS
CORS(app)

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量存储测试状态和结果
test_status = {
    'is_running': False,
    'current_test': None,
    'test_progress': 0,
    'test_results': [],
    'last_run_time': None
}

# 存储测试套件、场景和执行记录
test_suites = []
test_scenarios = []
executions = []

# 线程锁，用于保护全局变量的并发访问
executions_lock = threading.Lock()
test_suites_lock = threading.Lock()
test_scenarios_lock = threading.Lock()

# 创建SIP测试客户端实例，使用配置文件路径
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.ini')
sip_client = SIPTestClient(config_path)

@app.route('/')
def index():
    """API主页 - 返回API文档"""
    return jsonify({
        'message': 'SIP自动化测试平台API服务',
        'version': '1.0',
        'endpoints': {
            'GET /api/test_status': '获取测试状态',
            'GET /api/test_results': '获取测试结果',
            'POST /api/start_test': '启动测试',
            'GET/POST /api/config': '管理配置'
        },
        'frontend_url': 'http://localhost:3002'
    })

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


# 测试套件相关API
@app.route('/api/suites', methods=['GET'])
def get_all_suites():
    """获取所有测试套件"""
    return jsonify(test_suites)


@app.route('/api/suites/<int:suite_id>', methods=['GET'])
def get_suite_by_id(suite_id):
    """获取单个测试套件"""
    suite = next((s for s in test_suites if s.get('id') == suite_id), None)
    if suite:
        return jsonify(suite)
    return jsonify({'error': 'Suite not found'}), 404


@app.route('/api/suites', methods=['POST'])
def create_suite():
    """创建测试套件"""
    global test_suites
    try:
        data = request.json
        if not data or 'name' not in data:
            return jsonify({'error': 'Missing required fields: name'}), 400
            
        new_suite = {
            'id': len(test_suites) + 1,
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'scenarios': data.get('scenarios', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        test_suites.append(new_suite)
        return jsonify(new_suite), 201
    except Exception as e:
        app.logger.error(f"创建测试套件出错: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/suites/<int:suite_id>', methods=['PUT'])
def update_suite(suite_id):
    """更新测试套件"""
    global test_suites
    data = request.json
    for i, suite in enumerate(test_suites):
        if suite.get('id') == suite_id:
            test_suites[i].update({
                'name': data.get('name', suite['name']),
                'description': data.get('description', suite['description']),
                'scenarios': data.get('scenarios', suite['scenarios']),
                'updated_at': datetime.now().isoformat()
            })
            return jsonify(test_suites[i])
    return jsonify({'error': 'Suite not found'}), 404


@app.route('/api/suites/<int:suite_id>', methods=['DELETE'])
def delete_suite(suite_id):
    """删除测试套件"""
    global test_suites
    test_suites = [s for s in test_suites if s.get('id') != suite_id]
    return jsonify({'message': 'Suite deleted'})


# 测试场景相关API
@app.route('/api/scenarios', methods=['GET'])
def get_all_scenarios():
    """获取所有测试场景"""
    return jsonify(test_scenarios)


@app.route('/api/scenarios/<int:scenario_id>', methods=['GET'])
def get_scenario_by_id(scenario_id):
    """获取单个测试场景"""
    scenario = next((s for s in test_scenarios if s.get('id') == scenario_id), None)
    if scenario:
        return jsonify(scenario)
    return jsonify({'error': 'Scenario not found'}), 404


@app.route('/api/scenarios', methods=['POST'])
def create_scenario():
    """创建测试场景"""
    global test_scenarios
    try:
        data = request.json
        if not data or 'name' not in data:
            return jsonify({'error': 'Missing required fields: name'}), 400
            
        new_scenario = {
            'id': len(test_scenarios) + 1,
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'clientType': data.get('clientType', 'socket'),
            'priority': data.get('priority', 'medium'),
            'steps': data.get('steps', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        test_scenarios.append(new_scenario)
        return jsonify(new_scenario), 201
    except Exception as e:
        app.logger.error(f"创建测试场景出错: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
def update_scenario(scenario_id):
    """更新测试场景"""
    global test_scenarios
    data = request.json
    for i, scenario in enumerate(test_scenarios):
        if scenario.get('id') == scenario_id:
            test_scenarios[i].update({
                'name': data.get('name', scenario['name']),
                'description': data.get('description', scenario['description']),
                'clientType': data.get('clientType', scenario['clientType']),
                'priority': data.get('priority', scenario['priority']),
                'steps': data.get('steps', scenario['steps']),
                'updated_at': datetime.now().isoformat()
            })
            return jsonify(test_scenarios[i])
    return jsonify({'error': 'Scenario not found'}), 404


@app.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
def delete_scenario(scenario_id):
    """删除测试场景"""
    global test_scenarios
    test_scenarios = [s for s in test_scenarios if s.get('id') != scenario_id]
    return jsonify({'message': 'Scenario deleted'})


# 测试执行相关API
@app.route('/api/executions', methods=['GET'])
def get_all_executions():
    """获取所有执行记录"""
    with executions_lock:
        return jsonify(executions)


@app.route('/api/executions', methods=['POST'])
def start_execution():
    """开始执行测试"""
    global executions
    data = request.json
    
    # 创建执行记录
    execution = {
        'id': str(uuid.uuid4()),
        'suiteIds': data.get('suiteIds', []),
        'concurrentCount': data.get('concurrentCount', 1),
        'environment': data.get('environment', 'test'),
        'status': 'running',
        'progress': 0,
        'startTime': datetime.now().isoformat(),
        'endTime': None,
        'results': []
    }
    
    with executions_lock:
        executions.append(execution)
    
    # 启动执行线程
    execution_thread = threading.Thread(
        target=execute_test_suite,
        args=(execution['id'], data.get('suiteIds', []), data.get('concurrentCount', 1))
    )
    execution_thread.daemon = True
    execution_thread.start()
    
    return jsonify(execution), 201


@app.route('/api/executions/<execution_id>', methods=['DELETE'])
def stop_execution(execution_id):
    """停止执行测试"""
    global executions
    with executions_lock:
        for execution in executions:
            if execution.get('id') == execution_id:
                execution['status'] = 'stopped'
                execution['endTime'] = datetime.now().isoformat()
                return jsonify(execution)
    return jsonify({'error': 'Execution not found'}), 404


@app.route('/api/executions/<execution_id>/status', methods=['GET'])
def get_execution_status(execution_id):
    """获取执行状态"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == execution_id:
                return jsonify({
                    'status': execution.get('status', 'unknown'),
                    'progress': execution.get('progress', 0),
                    'results': execution.get('results', [])
                })
    return jsonify({'error': 'Execution not found'}), 404


# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    app.logger.info('客户端已连接到WebSocket')
    emit('connection_status', {'status': 'connected', 'message': 'WebSocket连接已建立'})


@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    app.logger.info('客户端已断开WebSocket连接')


@socketio.on('request_execution_updates')
def handle_execution_updates(data):
    """处理执行状态更新请求"""
    execution_id = data.get('executionId')
    if execution_id:
        # 发送当前执行状态
        with executions_lock:
            for execution in executions:
                if execution.get('id') == execution_id:
                    emit('execution_update', {
                        'executionId': execution_id,
                        'status': execution.get('status', 'unknown'),
                        'progress': execution.get('progress', 0),
                        'results': execution.get('results', [])
                    })
                    break

def execute_test_suite(execution_id, suite_ids, concurrent_count):
    """执行测试套件的函数"""
    global executions
    try:
        # 查找执行记录
        with executions_lock:
            execution = next((e for e in executions if e.get('id') == execution_id), None)
        if not execution:
            app.logger.warning(f"执行任务不存在: {execution_id}")
            return
            
        # 更新执行状态
        with executions_lock:
            execution['status'] = 'running'
            execution['progress'] = 0
        
        # 通过WebSocket发送状态更新
        try:
            socketio.emit('execution_update', {
                'executionId': execution_id,
                'status': 'running',
                'progress': 0,
                'message': '开始执行测试套件'
            })
        except Exception as ws_error:
            app.logger.error(f"发送WebSocket更新失败: {ws_error}")
        
        # 模拟执行测试套件的过程
        total_suites = len(suite_ids)
        completed_suites = 0
        
        for suite_id in suite_ids:
            # 查找测试套件
            suite = next((s for s in test_suites if s.get('id') == suite_id), None)
            if suite:
                # 模拟执行套件中的场景
                for scenario_id in suite.get('scenarios', []):
                    scenario = next((s for s in test_scenarios if s.get('id') == scenario_id), None)
                    if scenario:
                        # 执行具体的测试场景
                        # 这里可以根据场景的步骤来执行相应的SIP测试
                        success = execute_scenario(scenario)
                        
                        # 通过WebSocket发送场景执行状态
                        try:
                            with executions_lock:
                                progress = execution['progress'] if execution and 'progress' in execution else 0
                            socketio.emit('execution_update', {
                                'executionId': execution_id,
                                'status': 'running',
                                'progress': progress,
                                'message': f'场景 {scenario.get("name", "")} 执行成功' if success else f'场景 {scenario.get("name", "")} 执行失败'
                            })
                        except Exception as ws_error:
                            app.logger.error(f"发送场景WebSocket更新失败: {ws_error}")
                
                completed_suites += 1
                with executions_lock:
                    if execution and total_suites > 0:  # 确保execution仍然存在且total_suites大于0
                        execution['progress'] = int((completed_suites / total_suites) * 100)
                        progress = execution['progress']
                    elif execution:
                        execution['progress'] = 100  # 如果没有套件，直接设为100%
                        progress = 100
                    else:
                        progress = 0
                
                # 通过WebSocket发送进度更新
                try:
                    socketio.emit('execution_update', {
                        'executionId': execution_id,
                        'status': 'running',
                        'progress': progress,
                        'message': f'测试套件 {suite.get("name", "")} 执行完成'
                    })
                except Exception as ws_error:
                    app.logger.error(f"发送进度WebSocket更新失败: {ws_error}")
                
                # 模拟执行时间
                time.sleep(1)
        
        # 更新执行完成状态
        with executions_lock:
            if execution:  # 确保execution仍然存在
                execution['status'] = 'completed'
                execution['progress'] = 100
                execution['endTime'] = datetime.now().isoformat()
        
        # 通过WebSocket发送完成状态
        try:
            socketio.emit('execution_update', {
                'executionId': execution_id,
                'status': 'completed',
                'progress': 100,
                'message': '所有测试套件执行完成'
            })
        except Exception as ws_error:
            app.logger.error(f"发送完成WebSocket更新失败: {ws_error}")
        
    except Exception as e:
        app.logger.error(f"执行测试套件出错: {e}")
        try:
            with executions_lock:
                # 再次获取execution以确保它仍然存在
                current_execution = next((e for e in executions if e.get('id') == execution_id), None)
                if current_execution:
                    current_execution['status'] = 'error'
                    current_execution['error'] = str(e)
            
            # 通过WebSocket发送错误状态
            socketio.emit('execution_update', {
                'executionId': execution_id,
                'status': 'error',
                'progress': 0,  # 默认进度
                'message': f'执行过程中发生错误: {str(e)}'
            })
        except Exception as ws_error:
            app.logger.error(f"发送错误WebSocket更新失败: {ws_error}")


def execute_scenario(scenario):
    """执行单个测试场景"""
    try:
        # 在函数内部导入，避免启动时的导入问题
        from core.pytest_integration.sip_dsl import SIPCallFlow
        
        # 根据场景的步骤执行SIP测试
        steps = scenario.get('steps', [])
        for step in steps:
            keyword = step.get('keyword', '')
            parameters = step.get('parameters', [])
            
            # 将参数转换为字典格式
            param_dict = {}
            for param in parameters:
                name = param.get('name', '')
                value = param.get('value', '')
                param_dict[name] = value
            
            # 根据关键字执行相应的SIP操作
            if keyword == 'make_sip_call':
                # 发起SIP呼叫
                callee = param_dict.get('callee', '')
                caller = param_dict.get('caller', '')
                # 使用SIPCallFlow执行呼叫
                call_flow = SIPCallFlow()
                call_flow.invite(callee).wait_for_200_ok().ack().bye()
            elif keyword == 'register_sip':
                # SIP注册
                username = param_dict.get('username', '')
                password = param_dict.get('password', '')
                server = param_dict.get('server', '')
                sip_client.register_user(username, password)
            elif keyword == 'send_dtmf':
                # 发送DTMF
                digits = param_dict.get('digits', '')
                # 实现发送DTMF的逻辑
                pass
            elif keyword == 'hang_up':
                # 挂断通话
                sip_client.hangup_call()
            elif keyword == 'unregister_sip':
                # SIP注销
                sip_client.unregister_user()
            elif keyword == 'send_message':
                # 发送消息
                sip_client.send_message()
            elif keyword == 'wait_for_time':
                # 等待时间
                seconds = int(param_dict.get('seconds', 5))
                time.sleep(seconds)
        
        return True
    except Exception as e:
        app.logger.error(f"执行场景出错: {e}")
        return False


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

# 仪表板相关API
@app.route('/api/dashboard/stats')
def get_dashboard_stats():
    """获取仪表板统计信息"""
    # 计算统计信息
    with executions_lock:
        total_executions = len(executions)
        successful_executions = len([e for e in executions if e.get('status') == 'completed'])
        failed_executions = len([e for e in executions if e.get('status') == 'error'])
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        
        # 计算平均执行时间
        completed_executions = [e for e in executions if 'endTime' in e and 'startTime' in e]
    if completed_executions:
        durations = []
        for exec_info in completed_executions:
            try:
                # 处理ISO格式的时间字符串，兼容不同Python版本
                start_str = exec_info['startTime']
                end_str = exec_info['endTime']
                
                # 尝试使用fromisoformat，如果不支持则使用strptime
                try:
                    # 移除时区标识符，以便fromisoformat能正确解析
                    clean_start_str = start_str.replace('Z', '').split('.')[0]
                    clean_end_str = end_str.replace('Z', '').split('.')[0]
                    start_time = datetime.fromisoformat(clean_start_str)
                    end_time = datetime.fromisoformat(clean_end_str)
                except AttributeError:
                    # 如果fromisoformat不可用（Python < 3.7），使用strptime
                    # 处理各种可能的时间格式
                    clean_start_str = start_str.replace('Z', '').replace('+00:00', '').split('.')[0]
                    clean_end_str = end_str.replace('Z', '').replace('+00:00', '').split('.')[0]
                    start_time = datetime.strptime(clean_start_str, '%Y-%m-%dT%H:%M:%S')
                    end_time = datetime.strptime(clean_end_str, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    # 如果fromisoformat解析失败，尝试手动清理字符串
                    clean_start_str = start_str.replace('Z', '').split('.')[0]
                    clean_end_str = end_str.replace('Z', '').split('.')[0]
                    start_time = datetime.fromisoformat(clean_start_str)
                    end_time = datetime.fromisoformat(clean_end_str)
                
                duration = (end_time - start_time).total_seconds()
                durations.append(duration)
            except ValueError as ve:
                app.logger.error(f"时间格式错误: {ve}")
                # 如果解析时间失败，跳过该条目
                continue
            except Exception as e:
                app.logger.error(f"计算执行时间时出错: {e}")
                # 如果出现其他错误，跳过该条目
                continue
        avg_duration = sum(durations) / len(durations) if durations else 0
    else:
        avg_duration = 0
    
    return jsonify({
        'totalExecutions': total_executions,
        'successRate': round(success_rate, 2),
        'failureRate': round(100 - success_rate, 2),
        'avgDuration': round(avg_duration, 2)
    })


@app.route('/api/dashboard/recent-tests')
def get_recent_tests():
    """获取最近的测试记录"""
    with executions_lock:
        # 返回最近的执行记录
        recent = executions[-10:] if len(executions) > 10 else executions  # 获取最近10条记录
    result = []
    for exec_info in recent:
        status_map = {
            'completed': '成功',
            'running': '进行中',
            'error': '失败',
            'stopped': '已停止'
        }
        status = status_map.get(exec_info.get('status', 'unknown'), '未知')
        
        result.append({
            'suiteName': f"执行 #{exec_info.get('id', '')[:8]}",
            'status': status,
            'startTime': exec_info.get('startTime', ''),
            'endTime': exec_info.get('endTime', '')
        })
    
    return jsonify(result)


@app.route('/api/dashboard/trends')
def get_trend_data():
    """获取趋势数据"""
    # 模拟趋势数据
    today = datetime.now()
    labels = [(today - timedelta(days=i)).strftime('%m-%d') for i in range(6, -1, -1)]
    
    # 模拟成功和失败的数据
    import random
    success_data = [random.randint(5, 15) for _ in range(7)]
    failure_data = [random.randint(0, 3) for _ in range(7)]
    
    return jsonify({
        'labels': labels,
        'successData': success_data,
        'failureData': failure_data
    })


@app.route('/api/dashboard/quick-test', methods=['POST'])
def run_quick_test():
    """运行快速测试"""
    test_data = request.json or {}
    
    # 启动一个快速测试
    test_type = test_data.get('test_type', 'register')
    test_duration = test_data.get('test_duration', 5)
    
    # 启动测试线程
    test_thread = threading.Thread(
        target=run_test_thread,
        args=(test_type, test_duration, 1, [])
    )
    test_thread.daemon = True
    test_thread.start()
    
    return jsonify({
        'status': 'success',
        'message': f'快速测试已启动: {test_type}',
        'test_type': test_type
    })


@app.route('/api/suites/stats')
def get_suite_stats():
    """获取测试套件统计信息"""
    total_suites = len(test_suites)
    active_suites = total_suites  # 暂时认为所有套件都是活跃的
    inactive_suites = 0
    
    return jsonify({
        'total': total_suites,
        'active': active_suites,
        'inactive': inactive_suites
    })


@app.route('/api/suites/<int:suite_id>/scenarios')
def get_suite_with_scenarios(suite_id):
    """获取测试套件详情（包含关联的测试场景）"""
    suite = next((s for s in test_suites if s.get('id') == suite_id), None)
    if not suite:
        return jsonify({'error': 'Suite not found'}), 404
    
    # 获取套件关联的场景详情
    scenario_details = []
    for scenario_id in suite.get('scenarios', []):
        scenario = next((s for s in test_scenarios if s.get('id') == scenario_id), None)
        if scenario:
            scenario_details.append(scenario)
    
    return jsonify({
        'suite': suite,
        'scenarios': scenario_details
    })


@app.route('/api/scenarios/<int:scenario_id>/details')
def get_scenario_with_details(scenario_id):
    """获取测试场景详情（包含步骤和配置）"""
    scenario = next((s for s in test_scenarios if s.get('id') == scenario_id), None)
    if not scenario:
        return jsonify({'error': 'Scenario not found'}), 404
    
    # 返回场景的详细信息
    return jsonify({
        'id': scenario.get('id'),
        'name': scenario.get('name'),
        'description': scenario.get('description'),
        'clientType': scenario.get('clientType'),
        'priority': scenario.get('priority'),
        'steps': scenario.get('steps'),
        'created_at': scenario.get('created_at'),
        'updated_at': scenario.get('updated_at')
    })


@app.route('/api/scenarios/templates')
def get_scenario_templates():
    """获取测试场景模板"""
    templates = [
        {
            'id': 1,
            'name': 'SIP注册测试模板',
            'description': '标准SIP用户注册测试场景',
            'steps': [
                {'keyword': 'register_sip', 'parameters': [{'name': 'username', 'value': ''}, {'name': 'password', 'value': ''}]},
                {'keyword': 'wait_for_time', 'parameters': [{'name': 'seconds', 'value': '5'}]}
            ]
        },
        {
            'id': 2,
            'name': 'SIP呼叫测试模板',
            'description': '标准SIP呼叫建立测试场景',
            'steps': [
                {'keyword': 'make_sip_call', 'parameters': [{'name': 'caller', 'value': ''}, {'name': 'callee', 'value': ''}]},
                {'keyword': 'wait_for_time', 'parameters': [{'name': 'seconds', 'value': '10'}]},
                {'keyword': 'hang_up', 'parameters': []}
            ]
        },
        {
            'id': 3,
            'name': 'SIP消息测试模板',
            'description': 'SIP消息发送和接收测试场景',
            'steps': [
                {'keyword': 'send_message', 'parameters': [{'name': 'message', 'value': 'Test message'}]},
                {'keyword': 'wait_for_time', 'parameters': [{'name': 'seconds', 'value': '5'}]}
            ]
        }
    ]
    return jsonify(templates)


@app.route('/api/scenarios/sip-steps')
def get_sip_steps():
    """获取SIP协议相关的预定义步骤"""
    sip_steps = [
        {'keyword': 'make_sip_call', 'description': '发起SIP呼叫'},
        {'keyword': 'register_sip', 'description': 'SIP用户注册'},
        {'keyword': 'send_message', 'description': '发送SIP消息'},
        {'keyword': 'send_dtmf', 'description': '发送DTMF信号'},
        {'keyword': 'hang_up', 'description': '挂断通话'},
        {'keyword': 'unregister_sip', 'description': 'SIP用户注销'},
        {'keyword': 'wait_for_time', 'description': '等待指定时间'}
    ]
    return jsonify(sip_steps)


@app.route('/api/scenarios/validate', methods=['POST'])
def validate_scenario():
    """验证测试场景配置"""
    scenario_data = request.json
    
    # 简单验证逻辑
    errors = []
    warnings = []
    
    if not scenario_data.get('name'):
        errors.append('场景名称不能为空')
    
    if not scenario_data.get('steps'):
        warnings.append('未定义测试步骤')
    
    # 更多验证逻辑可以在这里添加
    
    return jsonify({
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    })


@app.route('/api/executions/bulk', methods=['POST'])
def start_bulk_execution():
    """批量执行测试"""
    data = request.json
    execution_ids = []
    
    # 批量创建执行记录
    for execution_data in data.get('executions', []):
        execution = {
            'id': str(uuid.uuid4()),
            'suiteIds': execution_data.get('suiteIds', []),
            'concurrentCount': execution_data.get('concurrentCount', 1),
            'environment': execution_data.get('environment', 'test'),
            'status': 'running',
            'progress': 0,
            'startTime': datetime.now().isoformat(),
            'endTime': None,
            'results': []
        }
        with executions_lock:
            executions.append(execution)
        execution_ids.append(execution['id'])
        
        # 启动执行线程
        execution_thread = threading.Thread(
            target=execute_test_suite,
            args=(execution['id'], execution.get('suiteIds', []), execution.get('concurrentCount', 1))
        )
        execution_thread.daemon = True
        execution_thread.start()
    
    return jsonify({
        'status': 'success',
        'execution_ids': execution_ids,
        'message': f'批量执行已启动，共{len(execution_ids)}个任务'
    })


@app.route('/api/executions/<execution_id>/pause', methods=['PUT'])
def pause_execution(execution_id):
    """暂停执行测试"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == execution_id:
                if execution.get('status') == 'running':
                    execution['status'] = 'paused'
                    return jsonify({'status': 'success', 'message': '执行已暂停'})
                else:
                    return jsonify({'status': 'error', 'message': '执行不在运行状态'}), 400
    return jsonify({'status': 'error', 'message': '执行不存在'}), 404


@app.route('/api/executions/<execution_id>/resume', methods=['PUT'])
def resume_execution(execution_id):
    """恢复执行测试"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == execution_id:
                if execution.get('status') == 'paused':
                    execution['status'] = 'running'
                    return jsonify({'status': 'success', 'message': '执行已恢复'})
                else:
                    return jsonify({'status': 'error', 'message': '执行不在暂停状态'}), 400
    return jsonify({'status': 'error', 'message': '执行不存在'}), 404


# 测试报告相关API
@app.route('/api/reports', methods=['GET'])
def get_all_reports():
    """获取所有报告"""
    with executions_lock:
        # 将执行记录转换为报告格式
        reports = []
        for execution in executions:
            # 计算持续时间
            duration = 0
            if execution.get('startTime') and execution.get('endTime'):
                try:
                    start_time = datetime.fromisoformat(execution['startTime'].replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(execution['endTime'].replace('Z', '+00:00'))
                    duration = (end_time - start_time).total_seconds()
                except:
                    duration = 0
            
            # 计算通过/失败数量
            total = len(execution.get('results', []))
            passed = len([r for r in execution.get('results', []) if r.get('status') == 'pass'])
            failed = total - passed
            
            report = {
                'id': execution.get('id', ''),
                'suiteName': f"执行 #{execution.get('id', '')[:8]}" if execution.get('id') else '未知执行',
                'startTime': execution.get('startTime', ''),
                'endTime': execution.get('endTime', ''),
                'duration': round(duration, 2),
                'total': total,
                'passed': passed,
                'failed': failed,
                'status': execution.get('status', 'unknown'),
                'environment': execution.get('environment', 'default'),
                'concurrentCount': execution.get('concurrentCount', 1)
            }
            reports.append(report)
    
    # 支持分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 分页处理
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_reports = reports[start_idx:end_idx]
    
    return jsonify({
        'reports': paginated_reports,
        'total': len(reports),
        'page': page,
        'per_page': per_page,
        'pages': max(1, (len(reports) + per_page - 1) // per_page)
    })


@app.route('/api/reports/<report_id>', methods=['GET'])
def get_report_by_id(report_id):
    """获取单个报告"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == report_id:
                # 计算持续时间
                duration = 0
                if execution.get('startTime') and execution.get('endTime'):
                    try:
                        start_time = datetime.fromisoformat(execution['startTime'].replace('Z', '+00:00'))
                        end_time = datetime.fromisoformat(execution['endTime'].replace('Z', '+00:00'))
                        duration = (end_time - start_time).total_seconds()
                    except:
                        duration = 0
                
                # 计算通过/失败数量
                total = len(execution.get('results', []))
                passed = len([r for r in execution.get('results', []) if r.get('status') == 'pass'])
                failed = total - passed
                
                report = {
                    'id': execution.get('id', ''),
                    'suiteName': f"执行 #{execution.get('id', '')[:8]}" if execution.get('id') else '未知执行',
                    'startTime': execution.get('startTime', ''),
                    'endTime': execution.get('endTime', ''),
                    'duration': round(duration, 2),
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'status': execution.get('status', 'unknown'),
                    'environment': execution.get('environment', 'default'),
                    'concurrentCount': execution.get('concurrentCount', 1),
                    'results': execution.get('results', []),
                    'suiteIds': execution.get('suiteIds', [])
                }
                return jsonify(report)
    
    return jsonify({'error': '报告不存在'}), 404


@app.route('/api/reports/<report_id>/detail', methods=['GET'])
def get_report_detail(report_id):
    """获取报告详情"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == report_id:
                # 构建详细的报告信息
                detail = {
                    'id': execution.get('id'),
                    'suiteName': f"执行 #{execution.get('id', '')[:8]}",
                    'startTime': execution.get('startTime'),
                    'endTime': execution.get('endTime'),
                    'status': execution.get('status'),
                    'environment': execution.get('environment'),
                    'concurrentCount': execution.get('concurrentCount'),
                    'suiteIds': execution.get('suiteIds'),
                    'results': execution.get('results', []),
                    'logs': execution.get('logs', []),
                    'metrics': execution.get('metrics', {}),
                    'summary': {
                        'total': len(execution.get('results', [])),
                        'passed': len([r for r in execution.get('results', []) if r.get('status') == 'pass']),
                        'failed': len([r for r in execution.get('results', []) if r.get('status') == 'fail']),
                        'blocked': len([r for r in execution.get('results', []) if r.get('status') == 'block'])
                    }
                }
                return jsonify(detail)
    
    return jsonify({'error': '报告不存在'}), 404


@app.route('/api/reports/stats', methods=['GET'])
def get_report_stats():
    """获取报告统计数据"""
    with executions_lock:
        total_reports = len(executions)
        successful_reports = len([e for e in executions if e.get('status') == 'completed'])
        failed_reports = len([e for e in executions if e.get('status') == 'error'])
        running_reports = len([e for e in executions if e.get('status') == 'running'])
        
        # 计算成功率
        success_rate = (successful_reports / total_reports * 100) if total_reports > 0 else 0
        failure_rate = (failed_reports / total_reports * 100) if total_reports > 0 else 0
        
        # 计算平均执行时间
        completed_executions = [e for e in executions if 'endTime' in e and 'startTime' in e]
        avg_duration = 0
        if completed_executions:
            durations = []
            for exec_info in completed_executions:
                try:
                    # 处理ISO格式的时间字符串，兼容不同Python版本
                    start_str = exec_info['startTime']
                    end_str = exec_info['endTime']
                    
                    # 尝试使用fromisoformat，如果不支持则使用strptime
                    try:
                        # 移除时区标识符，以便fromisoformat能正确解析
                        clean_start_str = start_str.replace('Z', '').split('.')[0]
                        clean_end_str = end_str.replace('Z', '').split('.')[0]
                        start_time = datetime.fromisoformat(clean_start_str)
                        end_time = datetime.fromisoformat(clean_end_str)
                    except AttributeError:
                        # 如果fromisoformat不可用（Python < 3.7），使用strptime
                        # 处理各种可能的时间格式
                        clean_start_str = start_str.replace('Z', '').replace('+00:00', '').split('.')[0]
                        clean_end_str = end_str.replace('Z', '').replace('+00:00', '').split('.')[0]
                        start_time = datetime.strptime(clean_start_str, '%Y-%m-%dT%H:%M:%S')
                        end_time = datetime.strptime(clean_end_str, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        # 如果fromisoformat解析失败，尝试手动清理字符串
                        clean_start_str = start_str.replace('Z', '').split('.')[0]
                        clean_end_str = end_str.replace('Z', '').split('.')[0]
                        start_time = datetime.fromisoformat(clean_start_str)
                        end_time = datetime.fromisoformat(clean_end_str)
                    
                    duration = (end_time - start_time).total_seconds()
                    durations.append(duration)
                except ValueError as ve:
                    app.logger.error(f"时间格式错误: {ve}")
                    # 如果解析时间失败，跳过该条目
                    continue
                except Exception as e:
                    app.logger.error(f"计算执行时间时出错: {e}")
                    # 如果出现其他错误，跳过该条目
                    continue
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        return jsonify({
            'total': total_reports,
            'successful': successful_reports,
            'failed': failed_reports,
            'running': running_reports,
            'successRate': round(success_rate, 2),
            'failureRate': round(failure_rate, 2),
            'avgDuration': round(avg_duration, 2)
        })


@app.route('/api/reports/<report_id>/export/<format>', methods=['GET'])
def export_report_format(report_id, format):
    """导出指定格式的报告"""
    # 获取报告数据
    with executions_lock:
        execution = next((e for e in executions if e.get('id') == report_id), None)
        if not execution:
            return jsonify({'error': '报告不存在'}), 404
    
    # 根据格式生成报告内容
    if format.lower() == 'json':
        # 返回JSON格式的报告
        return jsonify({
            'id': execution.get('id'),
            'suiteName': f"执行 #{execution.get('id', '')[:8]}",
            'startTime': execution.get('startTime'),
            'endTime': execution.get('endTime'),
            'status': execution.get('status'),
            'results': execution.get('results', []),
            'environment': execution.get('environment'),
            'suiteIds': execution.get('suiteIds')
        })
    elif format.lower() == 'html':
        # 返回HTML格式的报告
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试报告 - {execution.get('id', 'Unknown')}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .results {{ margin-top: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>测试报告</h1>
                <p><strong>ID:</strong> {execution.get('id', 'Unknown')}</p>
                <p><strong>开始时间:</strong> {execution.get('startTime', 'N/A')}</p>
                <p><strong>结束时间:</strong> {execution.get('endTime', 'N/A')}</p>
                <p><strong>状态:</strong> {execution.get('status', 'Unknown')}</p>
            </div>
            <div class="results">
                <h2>测试结果</h2>
                <table>
                    <tr><th>测试项</th><th>状态</th><th>耗时</th></tr>
                    {"".join([
                        f'<tr><td>{r.get("name", "Unknown")}</td><td>{r.get("status", "Unknown")}</td><td>{r.get("duration", 0)}</td></tr>'
                        for r in execution.get('results', [])
                    ])}
                </table>
            </div>
        </body>
        </html>
        """
        from flask import Response
        return Response(html_content, mimetype='text/html')
    elif format.lower() == 'pdf':
        # 简单返回一个PDF格式的占位符
        pdf_placeholder = b'%PDF-1.4\n% This is a placeholder PDF\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        from flask import Response
        return Response(pdf_placeholder, mimetype='application/pdf')
    
    return jsonify({'error': '不支持的格式'}), 400


@app.route('/api/reports/<report_id>/rerun', methods=['POST'])
def rerun_test(report_id):
    """重跑测试"""
    with executions_lock:
        execution = next((e for e in executions if e.get('id') == report_id), None)
        if not execution:
            return jsonify({'error': '报告不存在'}), 404
    
    # 获取原始执行参数
    suite_ids = execution.get('suiteIds', [])
    environment = execution.get('environment', 'test')
    concurrent_count = execution.get('concurrentCount', 1)
    
    # 创建新的执行任务
    new_execution_id = str(uuid.uuid4())
    new_execution = {
        'id': new_execution_id,
        'suiteIds': suite_ids,
        'environment': environment,
        'concurrentCount': concurrent_count,
        'status': 'pending',
        'progress': 0,
        'startTime': datetime.now().isoformat(),
        'endTime': None,
        'results': []
    }
    
    executions.append(new_execution)
    
    # 启动执行线程
    execution_thread = threading.Thread(
        target=execute_test_suite,
        args=(new_execution_id, suite_ids, environment, concurrent_count)
    )
    execution_thread.daemon = True
    execution_thread.start()
    
    return jsonify({
        'id': new_execution_id,
        'message': '重跑任务已启动',
        'originalReportId': report_id
    })


@app.route('/api/executions/<execution_id>/detail')
def get_execution_detail(execution_id):
    """获取执行详情"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == execution_id:
                return jsonify(execution)
    return jsonify({'error': 'Execution not found'}), 404


@app.route('/api/executions/<execution_id>/logs')
def get_execution_logs(execution_id):
    """获取执行日志"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == execution_id:
                # 模拟返回一些日志
                logs = [
                    {'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': '执行开始'},
                    {'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': '正在执行测试套件'},
                    {'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': '执行完成'},
                ]
                return jsonify(logs)
    return jsonify({'error': 'Execution not found'}), 404


@app.route('/api/executions/<execution_id>/results')
def get_execution_results(execution_id):
    """获取执行结果"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == execution_id:
                # 模拟返回执行结果
                results = {
                    'execution_id': execution_id,
                    'summary': {
                        'total_tests': 10,
                        'passed': 8,
                        'failed': 2,
                        'skipped': 0
                    },
                    'details': [
                        {'test_name': 'SIP注册测试', 'status': 'passed', 'duration': 2.5},
                        {'test_name': 'SIP呼叫测试', 'status': 'passed', 'duration': 5.2},
                        {'test_name': 'SIP消息测试', 'status': 'failed', 'duration': 1.3},
                    ]
                }
                return jsonify(results)
    return jsonify({'error': 'Execution not found'}), 404


@app.route('/api/executions/stats')
def get_execution_stats():
    """获取执行统计信息"""
    with executions_lock:
        total_executions = len(executions)
        completed_executions = len([e for e in executions if e.get('status') == 'completed'])
        running_executions = len([e for e in executions if e.get('status') == 'running'])
        failed_executions = len([e for e in executions if e.get('status') == 'error'])
    
    return jsonify({
        'total': total_executions,
        'completed': completed_executions,
        'running': running_executions,
        'failed': failed_executions
    })


@app.route('/api/executions/<execution_id>/metrics')
def get_realtime_metrics(execution_id):
    """获取实时执行指标"""
    with executions_lock:
        for execution in executions:
            if execution.get('id') == execution_id:
                # 模拟返回实时指标
                metrics = {
                    'cpu_usage': 45,
                    'memory_usage': 60,
                    'active_threads': 3,
                    'requests_per_second': 12.5,
                    'response_time_avg': 0.25,
                    'error_rate': 0.02
                }
                return jsonify(metrics)
    return jsonify({'error': 'Execution not found'}), 404


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

# 测试用例相关API
@app.route('/api/test_cases', methods=['GET'])
def get_all_test_cases():
    """获取所有可用的测试用例"""
    test_cases = discover_test_cases()
    return jsonify(test_cases)


@app.route('/api/test_browser', methods=['GET'])
def get_test_browser():
    """获取测试浏览器数据，包括所有测试用例分类"""
    test_cases = discover_test_cases()
    
    # 按类别分组
    categorized_tests = {}
    for test_case in test_cases:
        category = test_case['category']
        if category not in categorized_tests:
            categorized_tests[category] = []
        categorized_tests[category].append(test_case)
    
    return jsonify({
        'categories': categorized_tests,
        'total_count': len(test_cases)
    })


@app.route('/api/test_cases/<test_case_id>/execute', methods=['POST'])
def execute_test_case(test_case_id):
    """执行特定的测试用例"""
    try:
        # 获取测试配置
        config = request.json or {}
        
        # 根据测试用例ID创建并执行相应的测试用例
        from test_cases.sip_test_case import TestCaseFactory
        
        # 执行测试
        test_case = TestCaseFactory.create_test_case(test_case_id, config)
        result = test_case.run()
        
        return jsonify({
            'status': 'success',
            'result': {
                'name': test_case.name,
                'description': test_case.description,
                'status': result.value,
                'duration': test_case.duration,
                'error_info': test_case.error_info
            }
        })
    except Exception as e:
        app.logger.error(f"执行测试用例失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    # 启动Web服务器
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)