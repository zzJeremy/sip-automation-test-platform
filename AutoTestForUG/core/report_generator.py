"""
报告生成器 - 核心层
统一的报告生成接口
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
import csv
from xml.etree.ElementTree import Element, SubElement, ElementTree


class ReportGenerator:
    """
    统一的报告生成器
    提供高层级的报告生成接口
    """
    
    def __init__(self, output_dir: str = "test_reports"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        from .pytest_integration.report_generator import SIPTestReportGenerator
        self.sip_report_generator = SIPTestReportGenerator(output_dir)
    
    def generate_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成测试报告（多种格式）
        
        Args:
            test_results: 测试结果
            
        Returns:
            Dict: 报告生成结果
        """
        self.logger.info("开始生成测试报告")
        
        # 生成多种格式报告
        formats = ["json", "html", "txt"]
        report_paths = {}
        
        for fmt in formats:
            try:
                report_path = self.sip_report_generator.generate_custom_report(
                    test_results, fmt
                )
                report_paths[f'{fmt}_report'] = report_path
            except Exception as e:
                self.logger.error(f"生成{fmt}格式报告失败: {str(e)}")
                report_paths[f'{fmt}_report'] = None
        
        # 生成CSV格式报告（新增）
        try:
            csv_report_path = self._generate_csv_report(test_results)
            report_paths['csv_report'] = csv_report_path
        except Exception as e:
            self.logger.error(f"生成CSV格式报告失败: {str(e)}")
            report_paths['csv_report'] = None
        
        # 生成XML格式报告（新增）
        try:
            xml_report_path = self._generate_xml_report(test_results)
            report_paths['xml_report'] = xml_report_path
        except Exception as e:
            self.logger.error(f"生成XML格式报告失败: {str(e)}")
            report_paths['xml_report'] = None
        
        report_result = {
            **report_paths,
            'generated_at': datetime.now().isoformat(),
            'success': all(path is not None for path in report_paths.values())
        }
        
        self.logger.info("测试报告生成完成")
        
        return report_result
    
    def _generate_csv_report(self, test_results: Dict[str, Any]) -> str:
        """生成CSV格式报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(self.output_dir) / f"sip_test_report_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['test_name', 'status', 'duration', 'error']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            # 从测试结果中提取测试详情
            test_details = test_results.get('details', [])
            for detail in test_details:
                writer.writerow({
                    'test_name': detail.get('name', 'Unknown'),
                    'status': detail.get('status', 'unknown'),
                    'duration': detail.get('duration', 0),
                    'error': detail.get('error', '')
                })
        
        self.logger.info(f"CSV报告已生成: {filename}")
        return str(filename)
    
    def _generate_xml_report(self, test_results: Dict[str, Any]) -> str:
        """生成XML格式报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(self.output_dir) / f"sip_test_report_{timestamp}.xml"
        
        # 创建根元素
        root = Element("SIPTestReport")
        root.set("generated_at", datetime.now().isoformat())
        
        # 添加汇总信息
        summary = SubElement(root, "Summary")
        SubElement(summary, "Total").text = str(test_results.get('total', 0))
        SubElement(summary, "Passed").text = str(test_results.get('passed', 0))
        SubElement(summary, "Failed").text = str(test_results.get('failed', 0))
        SubElement(summary, "Error").text = str(test_results.get('error', 0))
        
        # 添加详细测试结果
        details = SubElement(root, "TestDetails")
        test_details = test_results.get('details', [])
        for detail in test_details:
            test_case = SubElement(details, "TestCase")
            SubElement(test_case, "Name").text = detail.get('name', 'Unknown')
            SubElement(test_case, "Status").text = detail.get('status', 'unknown')
            SubElement(test_case, "Duration").text = str(detail.get('duration', 0))
            error_msg = detail.get('error', '')
            if error_msg:
                SubElement(test_case, "Error").text = error_msg
        
        # 写入XML文件
        tree = ElementTree(root)
        tree.write(filename, encoding='utf-8', xml_declaration=True)
        
        self.logger.info(f"XML报告已生成: {filename}")
        return str(filename)
    
    def generate_summary_report(self, test_results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成多套测试结果的汇总报告
        
        Args:
            test_results_list: 测试结果列表
            
        Returns:
            Dict: 汇总报告
        """
        self.logger.info(f"开始生成 {len(test_results_list)} 个测试结果的汇总报告")
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_error = 0
        all_details = []
        
        for result in test_results_list:
            total_tests += result.get('total', 0)
            total_passed += result.get('passed', 0)
            total_failed += result.get('failed', 0)
            total_error += result.get('error', 0)
            
            # 收集所有测试详情
            details = result.get('details', [])
            all_details.extend(details)
        
        summary_result = {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_error': total_error,
            'pass_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'details': all_details,
            'generated_at': datetime.now().isoformat()
        }
        
        # 生成汇总报告
        summary_report_path = self._generate_summary_report_files(summary_result)
        
        self.logger.info("汇总报告生成完成")
        
        return {
            'summary': summary_result,
            'report_path': summary_report_path,
            'success': True
        }
    
    def _generate_summary_report_files(self, summary_result: Dict[str, Any]) -> Dict[str, str]:
        """生成汇总报告的各种格式文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"summary_report_{timestamp}"
        
        report_paths = {}
        
        # JSON格式
        json_path = Path(self.output_dir) / f"{base_filename}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary_result, f, ensure_ascii=False, indent=2)
        report_paths['json'] = str(json_path)
        
        # 文本格式
        txt_path = Path(self.output_dir) / f"{base_filename}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("SIP测试汇总报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成时间: {summary_result['generated_at']}\n\n")
            f.write(f"总测试数: {summary_result['total_tests']}\n")
            f.write(f"通过: {summary_result['total_passed']}\n")
            f.write(f"失败: {summary_result['total_failed']}\n")
            f.write(f"错误: {summary_result['total_error']}\n")
            f.write(f"通过率: {summary_result['pass_rate']:.2f}%\n")
        report_paths['txt'] = str(txt_path)
        
        return report_paths
    
    def generate_pytest_report(self, pytest_args: list = None) -> Dict[str, Any]:
        """
        生成pytest报告
        
        Args:
            pytest_args: pytest参数
            
        Returns:
            Dict: 报告生成结果
        """
        self.logger.info("开始生成pytest报告")
        
        try:
            self.sip_report_generator.generate_pytest_html_report(pytest_args)
            
            return {
                'success': True,
                'message': 'Pytest报告生成完成'
            }
        except Exception as e:
            self.logger.error(f"生成pytest报告失败: {str(e)}")
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_report_data(self, test_results: Dict[str, Any], format_type: str = "json") -> str:
        """
        导出测试报告数据，用于外部系统集成
        
        Args:
            test_results: 测试结果
            format_type: 导出格式
            
        Returns:
            str: 导出的数据内容
        """
        if format_type.lower() == "json":
            return json.dumps(test_results, ensure_ascii=False, indent=2)
        elif format_type.lower() == "csv":
            # 生成CSV格式的数据字符串
            import io
            output = io.StringIO()
            fieldnames = ['test_name', 'status', 'duration', 'error']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            
            writer.writeheader()
            
            test_details = test_results.get('details', [])
            for detail in test_details:
                writer.writerow({
                    'test_name': detail.get('name', 'Unknown'),
                    'status': detail.get('status', 'unknown'),
                    'duration': detail.get('duration', 0),
                    'error': detail.get('error', '')
                })
            
            return output.getvalue()
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")