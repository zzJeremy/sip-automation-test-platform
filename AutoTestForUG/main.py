#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AutoTestForUG - SIP自动化测试系统主入口文件
实现软交换系统自动化测试的核心功能
"""

import logging
import sys
import argparse
import os
from pathlib import Path
import pathlib

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from test_client.sip_test_client import SIPTestClient
from monitor_client.performance_monitor import PerformanceMonitor
from config.config import load_config


def setup_logging(config_path: str = './AutoTestForUG/config/config.ini'):
    """设置日志系统"""
    try:
        # 检查当前工作目录以确定正确的配置文件路径
        cwd = pathlib.Path.cwd()
        
        if cwd.name == 'AutoTestForUG':
            # 当前在AutoTestForUG目录中
            possible_paths = [
                './config/config.ini',  # 从AutoTestForUG目录运行
                config_path,  # 默认路径
            ]
        else:
            # 当前在项目根目录或其他位置
            possible_paths = [
                config_path,  # 默认路径（从项目根目录运行）
                './config/config.ini',  # 从AutoTestForUG目录运行（如果路径错误）
                './AutoTestForUG/config/config.ini'  # 从项目根目录运行
            ]
        
        actual_config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                actual_config_path = path
                break
        
        if actual_config_path is None:
            # 如果都没找到，尝试从当前工作目录推断
            if cwd.name == 'AutoTestForUG':
                # 当前在AutoTestForUG目录中
                actual_config_path = './config/config.ini'
            else:
                # 当前在项目根目录或其他位置
                actual_config_path = './AutoTestForUG/config/config.ini'
        
        config = load_config(actual_config_path)
        logging_config = config.get('LOGGING', {})
        log_level_str = logging_config.get('log_level', 'INFO')
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        log_format = logging_config.get('log_format', 
                                   '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = logging_config.get('log_file', './logs/autotestforug.log')
        
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    except Exception as e:
        # 如果配置文件加载失败，使用默认配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('autotestforug.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logging.error(f"使用默认日志配置: {str(e)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SIP自动化测试系统')
    parser.add_argument('--config', type=str, default=None, help='配置文件路径')
    parser.add_argument('--test-type', type=str, choices=['register', 'call', 'message', 'monitor', 'exception', 'all', 'web', 'web_interface', 'connectivity', 'sip_message', 'performance', 'business', 'conference'],
                       default='all', help='测试类型: register(注册测试), call(呼叫测试), message(SIP消息测试), '
                                          'monitor(性能监控), exception(异常测试), all(全部测试), '
                                          'web/web_interface(启动Web界面), connectivity(设备连接性测试), '
                                          'sip_message(SIP消息解析测试), performance(性能测试), '
                                          'business(业务测试), conference(会议呼叫测试)')
    parser.add_argument('--duration', type=int, default=60, help='测试持续时间（秒）')
    
    args = parser.parse_args()
    
    # 如果没有指定配置文件路径，则使用默认路径
    if args.config is None:
        # 检查当前工作目录以确定默认配置文件路径
        import pathlib
        cwd = pathlib.Path.cwd()
        
        # 检查可能的配置文件位置
        if (cwd / 'AutoTestForUG' / 'config' / 'config.ini').exists():
            args.config = './AutoTestForUG/config/config.ini'  # 从项目根目录运行
        elif (cwd / 'config' / 'config.ini').exists():
            args.config = './config/config.ini'  # 从AutoTestForUG目录运行
        else:
            # 如果都不存在，尝试使用相对路径
            args.config = './config/config.ini'
    
    # 设置日志系统
    setup_logging(args.config)
    logger = logging.getLogger(__name__)
    
    logger.info("启动AutoTestForUG SIP自动化测试系统")
    
    try:
        # 加载配置
        config = load_config(args.config)
        logger.info(f"配置文件加载成功: {args.config}")
        
        # 根据测试类型执行相应功能
        if args.test_type in ['web', 'web_interface']:
            # 启动Web界面
            logger.info("启动Web界面")
            try:
                # 确保项目路径正确
                import sys
                import os
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                
                from web_interface.web_app import app
                logger.info("Web界面启动成功，访问地址: http://localhost:5000")
                app.run(debug=True, host='0.0.0.0', port=5000)
                # app.run()是阻塞的，只有在服务器停止时才会执行下面的代码
            except ImportError as ie:
                logger.error(f"无法启动Web界面，导入错误: {ie}")
                logger.info("请安装Flask: pip install flask")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                sys.exit(1)  # 如果导入失败，退出程序
            except Exception as e:
                logger.error(f"启动Web界面时出错: {e}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                sys.exit(1)  # 发生错误时退出程序
        else:
            # 执行其他测试类型
            if args.test_type in ['register', 'call', 'message', 'exception', 'sip_message', 'performance', 'all']:
                logger.info(f"启动SIP测试客户端，测试类型: {args.test_type}")
                sip_client = SIPTestClient(args.config)
                
                if args.test_type == 'register' or args.test_type == 'all':
                    # 执行设备连接性测试
                    logger.info("执行目标设备连接性测试")
                    sip_client.test_device_connectivity()
                    
                    # 执行注册测试
                    logger.info("执行SIP用户注册测试")
                    sip_client.register_user(sip_client.username, sip_client.password)
                
                if args.test_type == 'call' or args.test_type == 'all':
                    # 执行呼叫测试
                    logger.info("执行SIP呼叫测试")
                    sip_client.make_call("sip:caller@127.0.0.1:5060", "sip:callee@127.0.0.1:5060", args.duration)
                
                if args.test_type == 'message' or args.test_type == 'all':
                    # 执行消息测试
                    logger.info("执行SIP消息测试")
                    sip_client.send_message("sip:sender@127.0.0.1:5060", "sip:receiver@127.0.0.1:5060", "测试消息内容")
                
                if args.test_type == 'exception' or args.test_type == 'all':
                    # 执行异常情况测试
                    logger.info("执行异常情况测试")
                    
                    # 网络故障模拟测试
                    logger.info("执行网络故障模拟测试")
                    sip_client.simulate_network_failure()
                    
                    # 认证失败测试
                    logger.info("执行认证失败测试")
                    sip_client.test_authentication_failure("test_user", "wrong_password")
                    
                    # 服务器不可用测试
                    logger.info("执行服务器不可用测试")
                    sip_client.test_server_unavailable()
                    
                    # 超时场景测试
                    logger.info("执行超时场景测试")
                    sip_client.test_timeout_scenarios(5)  # 5秒超时
                
                if args.test_type == 'sip_message' or args.test_type == 'all':
                    # 执行SIP消息解析和验证测试
                    logger.info("执行SIP消息解析和验证测试")
                    sip_client.run_sip_message_tests()
                
                if args.test_type == 'performance' or args.test_type == 'all':
                    # 执行性能测试
                    logger.info("执行性能测试")
                    
                    # 基础性能测试
                    logger.info("执行基础性能测试")
                    performance_results = sip_client.run_performance_tests(test_duration=30, concurrent_calls=5)
                    
                    # 并发注册测试
                    logger.info("执行并发注册测试")
                    registration_results = sip_client.run_concurrent_registration_tests(num_registrations=50, max_concurrent=10)
                    
                    # 输出性能测试摘要
                    logger.info(f"性能测试摘要:")
                    logger.info(f"  - 呼叫成功率: {performance_results.get('successful_calls', 0)}/{performance_results.get('total_calls_attempted', 0)}")
                    logger.info(f"  - 平均响应时间: {performance_results.get('average_response_time', 0):.3f}秒")
                    logger.info(f"  - 吞吐量: {performance_results.get('throughput_calls_per_second', 0):.2f} 呼叫/秒")
                    logger.info(f"  - 注册成功率: {registration_results.get('successful_registrations', 0)}/{registration_results.get('num_registrations', 0)}")
                
                if args.test_type == 'conference' or args.test_type == 'all':
                    # 执行会议呼叫测试
                    logger.info("执行会议呼叫测试")
                    
                    # 设置会议呼叫
                    logger.info("设置包含3个参与者的会议呼叫")
                    participants = [
                        "sip:alice@127.0.0.1:5060",
                        "sip:bob@127.0.0.1:5060", 
                        "sip:charlie@127.0.0.1:5060"
                    ]
                    conference_id = sip_client.setup_conference_call(participants)
                    
                    if conference_id:
                        # 添加额外参与者到会议
                        logger.info("向会议添加额外参与者")
                        sip_client.add_participant_to_conference(conference_id, "sip:diana@127.0.0.1:5060")
                        
                        # 从会议中移除一个参与者
                        logger.info("从会议中移除一个参与者")
                        sip_client.remove_participant_from_conference(conference_id, "sip:bob@127.0.0.1:5060")
                        
                        # 结束会议
                        logger.info("结束会议呼叫")
                        sip_client.end_conference_call(conference_id)
            
            if args.test_type == 'monitor' or args.test_type == 'all':
                logger.info("启动性能监控模块")
                monitor = PerformanceMonitor(args.config)
                
                # 启动监控
                monitor.start_monitoring()
                
                # 运行指定时间后停止监控
                import time
                time.sleep(args.duration)
                monitor.stop_monitoring()
                
                # 导出监控数据
                export_file = monitor.export_monitor_data()
                logger.info(f"监控数据已导出到: {export_file}")
        
        logger.info("AutoTestForUG测试完成")
        
    except Exception as e:
        logger.error(f"AutoTestForUG运行出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()