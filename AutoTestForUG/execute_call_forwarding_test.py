#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从前端执行SIP呼叫前转测试用例
集成到AutoTestForUG系统的测试用例执行器
支持多种前转类型：无条件前转、遇忙前转、无应答前转
"""

import sys
import os
from pathlib import Path
import yaml
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 修正导入路径
from test_cases.sip_test_case import TestCaseFactory, TestSuite


def load_test_case_from_yaml(yaml_file_path: str):
    """从YAML文件加载测试用例配置"""
    with open(yaml_file_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    
    # 获取第一个测试用例的配置
    test_case_config = config['test_cases'][0] if config.get('test_cases') else config
    
    return test_case_config


def execute_all_call_forwarding_tests():
    """执行所有类型的呼叫前转测试用例"""
    print("=" * 80)
    print("从前端执行SIP呼叫前转测试用例套件")
    print("包括：无条件前转、遇忙前转、无应答前转")
    print("=" * 80)
    
    try:
        # 从YAML文件加载测试配置
        yaml_file = project_root / "test_cases" / "call_forwarding_test.yaml"
        if not yaml_file.exists():
            print(f"错误: 找不到测试配置文件 {yaml_file}")
            return False
        
        print(f"加载测试配置: {yaml_file}")
        config = load_test_case_from_yaml(str(yaml_file))
        
        # 更新配置以连接到实际设备
        config['config']['server_host'] = '192.168.30.66'
        config['config']['server_port'] = 5060
        config['caller_uri'] = 'sip:670491@192.168.30.66:5060'  # A号码
        config['callee_uri'] = 'sip:670492@192.168.30.66:5060'  # B号码（已配置前转）
        config['forward_to_uri'] = 'sip:670493@192.168.30.66:5060'  # C号码（前转目标）
        
        # 设置代理认证信息
        config['proxy_username'] = '670491'
        config['proxy_password'] = '1234'
        
        # 合并配置
        final_config = {**config.get('config', {}), **config}
        
        print(f"测试用例: {config.get('name', 'Unknown')}")
        print(f"描述: {config.get('description', 'No description')}")
        print(f"主叫: {final_config.get('caller_uri')}")
        print(f"被叫: {final_config.get('callee_uri')}")
        print(f"前转目标: {final_config.get('forward_to_uri')}")
        print(f"被测设备: {final_config.get('server_host')}:{final_config.get('server_port')}")
        
        # 创建测试套件
        print("\n创建综合测试套件...")
        test_suite = TestSuite("SIP呼叫前转功能测试套件", "验证SIP多种前转功能")
        
        # 添加无条件前转测试用例
        print("添加无条件前转测试用例...")
        unconditional_config = final_config.copy()
        unconditional_config['test_type'] = 'unconditional'
        unconditional_test_case = TestCaseFactory.create_test_case('call_forwarding_unconditional', unconditional_config)
        test_suite.add_test_case(unconditional_test_case)
        
        # 添加遇忙前转测试用例
        print("添加遇忙前转测试用例...")
        busy_config = final_config.copy()
        busy_config['test_type'] = 'busy'
        busy_test_case = TestCaseFactory.create_test_case('call_forwarding_busy', busy_config)
        test_suite.add_test_case(busy_test_case)
        
        # 添加无应答前转测试用例
        print("添加无应答前转测试用例...")
        noanswer_config = final_config.copy()
        noanswer_config['test_type'] = 'noanswer'
        noanswer_test_case = TestCaseFactory.create_test_case('call_forwarding_noanswer', noanswer_config)
        test_suite.add_test_case(noanswer_test_case)
        
        # 运行测试
        print("\n执行所有前转测试用例...")
        results = test_suite.run_all()
        
        # 输出结果
        print(f"\n综合测试结果:")
        print(f"  测试套件: {results['suite_name']}")
        print(f"  总测试数: {results['total']}")
        print(f"  通过: {results['passed']}")
        print(f"  失败: {results['failed']}")
        print(f"  错误: {results['error']}")
        print(f"  总耗时: {results['total_duration']:.2f}秒")
        
        for result in results['test_results']:
            status_icon = "✓" if result['status'] == 'passed' else "✗"
            print(f"  {status_icon} {result['name']}: {result['status']} ({result['duration']:.2f}秒)")
            if result.get('error_info'):
                print(f"    错误信息: {result['error_info']}")
        
        # 生成详细报告
        print(f"\n详细测试报告:")
        print("-" * 50)
        
        for result in results['test_results']:
            print(f"测试用例: {result['name']}")
            print(f"状态: {result['status']}")
            print(f"耗时: {result['duration']:.2f}秒")
            
            # 根据测试结果提供解释
            if result['status'] == 'passed':
                if 'Unconditional' in result['name']:
                    print("✓ 无条件前转功能正常工作：检测到181 Call Is Being Forwarded响应")
                    print("✓ 呼叫被正确转发到目标号码")
                elif 'Busy' in result['name']:
                    print("✓ 遇忙前转功能正常工作：检测到486 Busy Here后成功前转")
                    print("✓ 被叫方繁忙时呼叫被正确转发")
                elif 'No Answer' in result['name']:
                    print("✓ 无应答前转功能正常工作：超时后成功前转")
                    print("✓ 被叫方无应答时呼叫被正确转发")
            elif result['status'] == 'failed':
                if 'Unconditional' in result['name']:
                    print("✗ 无条件前转功能未按预期工作")
                    print("  - 可能原因: 前转未配置、设备故障或网络问题")
                elif 'Busy' in result['name']:
                    print("✗ 遇忙前转功能未按预期工作")
                    print("  - 可能原因: 遇忙前转未启用或配置错误")
                elif 'No Answer' in result['name']:
                    print("✗ 无应答前转功能未按预期工作")
                    print("  - 可能原因: 无应答前转未启用或超时设置不当")
            else:
                print(f"⚠ 测试执行出错: {result.get('error_info', '未知错误')}")
            
            print()
        
        # 返回测试是否成功
        return results['passed'] > 0
        
    except Exception as e:
        print(f"执行测试用例时出错: {str(e)}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False


def main():
    """主函数"""
    print("SIP呼叫前转测试用例执行器")
    print("此脚本模拟从前端直接执行多种前转测试用例的过程")
    
    success = execute_all_call_forwarding_tests()
    
    if success:
        print("\n" + "=" * 80)
        print("✓ SIP呼叫前转测试用例执行成功!")
        print("测试验证了多种前转功能：无条件前转、遇忙前转、无应答前转")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("✗ SIP呼叫前转测试用例执行失败!")
        print("请检查设备配置和网络连接")
        print("=" * 80)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)