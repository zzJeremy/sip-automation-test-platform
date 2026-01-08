"""
SIPp结果解析器模块
解析SIPp的log文件和报告，提取关键测试指标并转换为统一结果格式
"""
import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import json
import csv
from datetime import datetime


class SIPpResultParser:
    """
    SIPp结果解析器，用于解析SIPp的输出文件和报告
    """
    
    def __init__(self):
        self.logger = None  # 可选的日志记录器
    
    def parse_log_file(self, log_file_path: str) -> Dict[str, Any]:
        """
        解析SIPp的log文件
        
        Args:
            log_file_path: SIPp日志文件路径
            
        Returns:
            解析后的日志数据字典
        """
        if not os.path.exists(log_file_path):
            return {'error': f'Log file does not exist: {log_file_path}'}
        
        log_data = {
            'messages': [],
            'errors': [],
            'warnings': [],
            'timestamps': [],
            'call_ids': set()
        }
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 解析SIP消息
        message_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)'
        lines = content.split('\n')
        
        for line in lines:
            match = re.match(message_pattern, line.strip())
            if match:
                timestamp = match.group(1)
                message = match.group(2)
                
                log_data['timestamps'].append(timestamp)
                log_data['messages'].append({
                    'timestamp': timestamp,
                    'message': message
                })
                
                # 检查是否为错误或警告
                if 'ERROR' in message.upper() or 'FAIL' in message.upper():
                    log_data['errors'].append({
                        'timestamp': timestamp,
                        'message': message
                    })
                elif 'WARNING' in message.upper() or 'WARN' in message.upper():
                    log_data['warnings'].append({
                        'timestamp': timestamp,
                        'message': message
                    })
        
        return log_data
    
    def parse_scenario_report(self, report_file_path: str) -> Dict[str, Any]:
        """
        解析SIPp的场景报告文件（通常是CSV格式）
        
        Args:
            report_file_path: 报告文件路径
            
        Returns:
            解析后的报告数据字典
        """
        if not os.path.exists(report_file_path):
            return {'error': f'Report file does not exist: {report_file_path}'}
        
        report_data = {
            'calls': [],
            'statistics': {},
            'summary': {}
        }
        
        try:
            with open(report_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                # 检测CSV格式
                sample = csvfile.read(1024)
                csvfile.seek(0)
                
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                
                for row in reader:
                    report_data['calls'].append(dict(row))
        
        except Exception as e:
            return {'error': f'Error parsing CSV report: {str(e)}'}
        
        # 计算统计信息
        report_data['statistics'] = self._calculate_statistics(report_data['calls'])
        
        return report_data
    
    def parse_statistics_report(self, stats_file_path: str) -> Dict[str, Any]:
        """
        解析SIPp的统计报告文件（通常是XML格式）
        
        Args:
            stats_file_path: 统计报告文件路径
            
        Returns:
            解析后的统计数据字典
        """
        if not os.path.exists(stats_file_path):
            return {'error': f'Stats file does not exist: {stats_file_path}'}
        
        try:
            tree = ET.parse(stats_file_path)
            root = tree.getroot()
            
            stats_data = {
                'global': {},
                'periodic': [],
                'flow_stats': []
            }
            
            # 解析全局统计
            if root.tag == 'statistics':
                for child in root:
                    if child.tag == 'global':
                        stats_data['global'] = self._parse_global_stats(child)
                    elif child.tag == 'periodic':
                        stats_data['periodic'].append(self._parse_periodic_stats(child))
                    elif child.tag == 'flow_stats':
                        stats_data['flow_stats'].append(self._parse_flow_stats(child))
            
            return stats_data
        except ET.ParseError as e:
            return {'error': f'Error parsing XML stats: {str(e)}'}
        except Exception as e:
            return {'error': f'Error reading stats file: {str(e)}'}
    
    def _parse_global_stats(self, element) -> Dict[str, Any]:
        """解析全局统计信息"""
        stats = {}
        for child in element:
            stats[child.tag] = child.text
        return stats
    
    def _parse_periodic_stats(self, element) -> Dict[str, Any]:
        """解析周期性统计信息"""
        stats = {'period': element.get('period')}
        for child in element:
            stats[child.tag] = child.text
        return stats
    
    def _parse_flow_stats(self, element) -> Dict[str, Any]:
        """解析流统计信息"""
        stats = {'flow': element.get('name')}
        for child in element:
            if child.tag == 'call_data':
                stats['call_data'] = self._parse_call_data(child)
            else:
                stats[child.tag] = child.text
        return stats
    
    def _parse_call_data(self, element) -> Dict[str, Any]:
        """解析呼叫数据"""
        data = {}
        for child in element:
            data[child.tag] = child.text
        return data
    
    def _calculate_statistics(self, calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算呼叫统计信息"""
        if not calls:
            return {}
        
        stats = {
            'total_calls': len(calls),
            'success_count': 0,
            'failure_count': 0,
            'average_duration': 0,
            'min_duration': float('inf'),
            'max_duration': 0,
            'success_rate': 0
        }
        
        durations = []
        
        for call in calls:
            # 计算成功/失败统计
            if call.get('Result', '').lower() in ['ok', 'success', '200']:
                stats['success_count'] += 1
            else:
                stats['failure_count'] += 1
            
            # 计算持续时间统计
            duration_str = call.get('Duration', '0')
            try:
                duration = float(duration_str)
                durations.append(duration)
                stats['min_duration'] = min(stats['min_duration'], duration)
                stats['max_duration'] = max(stats['max_duration'], duration)
            except ValueError:
                pass
        
        if durations:
            stats['average_duration'] = sum(durations) / len(durations)
            stats['min_duration'] = stats['min_duration'] if stats['min_duration'] != float('inf') else 0
            stats['success_rate'] = (stats['success_count'] / stats['total_calls']) * 100
        
        return stats
    
    def parse_all_reports(self, output_dir: str) -> Dict[str, Any]:
        """
        解析指定目录下的所有SIPp报告文件
        
        Args:
            output_dir: 包含报告文件的目录
            
        Returns:
            包含所有解析结果的字典
        """
        results = {
            'logs': {},
            'scenarios': {},
            'statistics': {},
            'summary': {}
        }
        
        if not os.path.exists(output_dir):
            return {'error': f'Output directory does not exist: {output_dir}'}
        
        for filename in os.listdir(output_dir):
            filepath = os.path.join(output_dir, filename)
            
            if filename.endswith('.log'):
                log_name = filename[:-4]  # 去掉.log后缀
                results['logs'][log_name] = self.parse_log_file(filepath)
            elif filename.endswith('.csv'):
                csv_name = filename[:-4]  # 去掉.csv后缀
                results['scenarios'][csv_name] = self.parse_scenario_report(filepath)
            elif filename.endswith('.xml'):
                xml_name = filename[:-4]  # 去掉.xml后缀
                results['statistics'][xml_name] = self.parse_statistics_report(filepath)
        
        # 生成汇总报告
        results['summary'] = self._generate_summary(results)
        
        return results
    
    def _generate_summary(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成汇总报告"""
        summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'pass_rate': 0,
            'total_duration': 0,
            'average_response_time': 0,
            'test_results': []
        }
        
        # 从场景报告中提取测试结果
        for scenario_name, scenario_data in all_results.get('scenarios', {}).items():
            if 'statistics' in scenario_data:
                stats = scenario_data['statistics']
                summary['total_tests'] += stats.get('total_calls', 0)
                summary['passed_tests'] += stats.get('success_count', 0)
                summary['failed_tests'] += stats.get('failure_count', 0)
                
                if 'average_duration' in stats:
                    summary['average_response_time'] = stats['average_duration']
        
        if summary['total_tests'] > 0:
            summary['pass_rate'] = (summary['passed_tests'] / summary['total_tests']) * 100
        
        return summary
    
    def export_results(self, results: Dict[str, Any], output_path: str, format: str = 'json'):
        """
        导出解析结果到指定格式的文件
        
        Args:
            results: 解析结果字典
            output_path: 输出文件路径
            format: 输出格式 ('json', 'csv', 'xml')
        """
        if format.lower() == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        elif format.lower() == 'csv':
            # 导出为CSV格式（仅导出调用数据）
            calls_data = []
            for scenario_data in results.get('scenarios', {}).values():
                if 'calls' in scenario_data:
                    calls_data.extend(scenario_data['calls'])
            
            if calls_data:
                fieldnames = set()
                for call in calls_data:
                    fieldnames.update(call.keys())
                
                with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=list(fieldnames))
                    writer.writeheader()
                    writer.writerows(calls_data)
        elif format.lower() == 'xml':
            # 创建一个简单的XML结构
            root = ET.Element('sipp_test_results')
            
            # 添加汇总信息
            summary_elem = ET.SubElement(root, 'summary')
            for key, value in results.get('summary', {}).items():
                elem = ET.SubElement(summary_elem, key)
                elem.text = str(value)
            
            # 添加日志信息
            logs_elem = ET.SubElement(root, 'logs')
            for log_name, log_data in results.get('logs', {}).items():
                log_elem = ET.SubElement(logs_elem, 'log', name=log_name)
                messages_elem = ET.SubElement(log_elem, 'messages')
                for msg in log_data.get('messages', []):
                    msg_elem = ET.SubElement(messages_elem, 'message')
                    msg_elem.text = str(msg)
            
            # 写入XML文件
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)


# 使用示例
if __name__ == "__main__":
    parser = SIPpResultParser()
    
    # 解析单个日志文件
    log_result = parser.parse_log_file("example.log")
    print("Log parsing result:", log_result)
    
    # 解析所有报告
    all_results = parser.parse_all_reports("./sipp_output")
    print("All results:", all_results)
    
    # 导出结果
    parser.export_results(all_results, "parsed_results.json", "json")