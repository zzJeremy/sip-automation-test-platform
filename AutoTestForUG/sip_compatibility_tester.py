"""
SIP服务器兼容性测试
测试基础SIP客户端与不同SIP服务器的兼容性
"""

import socket
import time
from typing import Dict, List, Tuple
import logging




class SIPCompatibilityTester:
    """
    SIP服务器兼容性测试器
    测试基础SIP客户端与不同SIP服务器的兼容性
    """
    
    def __init__(self):
        """初始化兼容性测试器"""
        self.logger = logging.getLogger(__name__)
        self.results = []
    
    def test_server_connectivity(self, host: str, port: int) -> bool:
        """
        测试与SIP服务器的连接性
        
        Args:
            host: 服务器主机地址
            port: 服务器端口
            
        Returns:
            bool: 连接是否成功
        """
        self.logger.info(f"测试与服务器 {host}:{port} 的连接性...")
        
        try:
            # 尝试创建UDP套接字并连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)  # 5秒超时
            
            # 发送一个简单的OPTIONS请求来测试连接
            options_msg = (
                f"OPTIONS sip:ping@{host}:{port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP 127.0.0.1:5080;branch=z9hG4bK{int(time.time())}\r\n"
                f"From: <sip:test@127.0.0.1:5080>;tag={int(time.time())}\r\n"
                f"To: <sip:ping@{host}:{port}>\r\n"
                f"Call-ID: {int(time.time())}.test@127.0.0.1\r\n"
                f"CSeq: 1 OPTIONS\r\n"
                f"Max-Forwards: 70\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            
            sock.sendto(options_msg.encode('utf-8'), (host, port))
            
            # 尝试接收响应
            try:
                response, addr = sock.recvfrom(4096)
                response_str = response.decode('utf-8')
                self.logger.info(f"收到服务器响应: {response_str.split()[1] if response_str.split() else 'Unknown'}")
                sock.close()
                return True
            except socket.timeout:
                self.logger.warning("服务器响应超时")
                sock.close()
                return False
                
        except Exception as e:
            self.logger.error(f"连接服务器时发生错误: {str(e)}")
            return False
    
    def test_basic_call_with_server(self, server_config: Dict[str, any], 
                                  caller_uri: str, callee_uri: str) -> Dict[str, any]:
        """
        使用特定服务器配置测试基础通话
        
        Args:
            server_config: 服务器配置
            caller_uri: 主叫URI
            callee_uri: 被叫URI
            
        Returns:
            Dict: 测试结果
        """
        self.logger.info(f"使用服务器配置测试基础通话: {server_config}")
        
        # 使用pytest架构执行基础通话测试
        from AutoTestForUG.core.pytest_integration.sip_dsl import SIPCallFlow
        from AutoTestForUG.core.pytest_integration.fixtures import sip_client_factory
        
        start_time = time.time()
        try:
            # 使用SIP DSL执行呼叫流程
            call_flow = SIPCallFlow(sip_client_factory)
            success = call_flow.make_call(caller_uri, callee_uri, duration=3)
        except Exception as e:
            self.logger.error(f"执行基础通话测试时发生错误: {str(e)}")
            success = False
        elapsed_time = time.time() - start_time
        
        result = {
            'server_config': server_config,
            'caller_uri': caller_uri,
            'callee_uri': callee_uri,
            'success': success,
            'elapsed_time': elapsed_time,
            'timestamp': time.time()
        }
        
        self.results.append(result)
        return result
    
    def run_comprehensive_compatibility_test(self, server_configs: List[Dict], 
                                           test_cases: List[Tuple[str, str]]) -> List[Dict]:
        """
        运行综合兼容性测试
        
        Args:
            server_configs: 服务器配置列表
            test_cases: 测试用例列表
            
        Returns:
            List: 所有测试结果
        """
        self.logger.info(f"开始综合兼容性测试，{len(server_configs)} 个服务器配置，{len(test_cases)} 个测试用例")
        
        all_results = []
        
        for i, config in enumerate(server_configs):
            self.logger.info(f"测试服务器配置 {i+1}/{len(server_configs)}: {config}")
            
            # 首先测试连接性
            connectivity = self.test_server_connectivity(
                config['sip_server_host'], 
                config['sip_server_port']
            )
            
            if not connectivity:
                self.logger.error(f"无法连接到服务器 {config['sip_server_host']}:{config['sip_server_port']}，跳过该配置")
                continue
            
            # 对每个测试用例执行通话测试
            for j, (caller, callee) in enumerate(test_cases):
                self.logger.info(f"执行测试用例 {j+1}/{len(test_cases)}: {caller} -> {callee}")
                
                result = self.test_basic_call_with_server(config, caller, callee)
                all_results.append(result)
                
                # 测试之间稍作延迟
                time.sleep(1)
        
        return all_results
    
    def generate_compatibility_report(self) -> str:
        """
        生成兼容性测试报告
        
        Returns:
            str: 测试报告
        """
        if not self.results:
            return "没有测试结果可生成报告"
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - successful_tests
        
        report = []
        report.append("=" * 60)
        report.append("SIP服务器兼容性测试报告")
        report.append("=" * 60)
        report.append(f"总测试数: {total_tests}")
        report.append(f"成功数: {successful_tests}")
        report.append(f"失败数: {failed_tests}")
        report.append(f"成功率: {(successful_tests/total_tests*100):.2f}%" if total_tests > 0 else "成功率: 0%")
        report.append("")
        
        # 按服务器分组统计
        server_stats = {}
        for result in self.results:
            server_key = f"{result['server_config']['sip_server_host']}:{result['server_config']['sip_server_port']}"
            if server_key not in server_stats:
                server_stats[server_key] = {'total': 0, 'success': 0, 'failed': 0}
            
            server_stats[server_key]['total'] += 1
            if result['success']:
                server_stats[server_key]['success'] += 1
            else:
                server_stats[server_key]['failed'] += 1
        
        report.append("按服务器统计:")
        for server, stats in server_stats.items():
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report.append(f"  {server}: 总计{stats['total']}, 成功{stats['success']}, 失败{stats['failed']}, 成功率{success_rate:.2f}%")
        
        report.append("")
        report.append("详细测试结果:")
        report.append("-" * 60)
        
        for i, result in enumerate(self.results, 1):
            status = "成功" if result['success'] else "失败"
            report.append(f"{i}. {result['caller_uri']} -> {result['callee_uri']}")
            report.append(f"   服务器: {result['server_config']['sip_server_host']}:{result['server_config']['sip_server_port']}")
            report.append(f"   状态: {status}, 耗时: {result['elapsed_time']:.2f}秒")
            report.append("")
        
        return "\n".join(report)


def main():
    """兼容性测试主函数"""
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建兼容性测试器
    tester = SIPCompatibilityTester()
    
    # 定义不同的服务器配置进行测试
    server_configs = [
        {
            'sip_server_host': '127.0.0.1',
            'sip_server_port': 5060,
            'local_host': '127.0.0.1',
            'local_port': 5080
        },
        {
            'sip_server_host': '127.0.0.1',
            'sip_server_port': 5070,  # 不同端口测试
            'local_host': '127.0.0.1',
            'local_port': 5081
        }
        # 可以添加更多服务器配置
    ]
    
    # 定义测试用例
    test_cases = [
        ("sip:alice@127.0.0.1:5060", "sip:bob@127.0.0.1:5060"),
        ("sip:user1@127.0.0.1:5060", "sip:user2@127.0.0.1:5060"),
        ("sip:test@127.0.0.1:5060", "sip:echo@127.0.0.1:5060")
    ]
    
    print("开始SIP服务器兼容性测试...")
    
    # 运行兼容性测试
    results = tester.run_comprehensive_compatibility_test(server_configs, test_cases)
    
    # 生成并打印报告
    report = tester.generate_compatibility_report()
    print(report)
    
    # 保存报告到文件
    with open("sip_compatibility_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("兼容性测试完成，报告已保存到 sip_compatibility_report.txt")


if __name__ == "__main__":
    main()