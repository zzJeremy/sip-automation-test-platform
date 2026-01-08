#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
邮件报告模块
用于生成和发送测试报告邮件
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime
import pandas as pd

from utils.utils import setup_logger
def convert_result_to_dict(result):
    """
    将TestResult对象转换为字典格式
    """
    if hasattr(result, '__dict__'):  # 如果是对象
        return result.__dict__
    elif isinstance(result, dict):  # 如果已经是字典
        return result
    else:
        # 尝试使用getattr来获取属性
        result_dict = {}
        for attr in ['test_case_id', 'status', 'execution_time', 'details', 'timestamp']:
            try:
                result_dict[attr] = getattr(result, attr)
            except AttributeError:
                result_dict[attr] = 'N/A'
        return result_dict




class EmailReporter:
    """邮件报告器类"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, sender_email: str):
        """
        初始化邮件报告器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            username: 邮箱用户名
            password: 邮箱密码或授权码
            sender_email: 发送者邮箱地址
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.logger = setup_logger("EmailReporter", "email_report.log")
        
        self.logger.info("邮件报告器初始化完成")
    
    def create_test_report_html(self, test_results: List[Dict[str, Any]], 
                              summary: Dict[str, Any], 
                              title: str = "SIP自动化测试报告") -> str:
        """
        创建HTML格式的测试报告
        
        Args:
            test_results: 测试结果列表
            summary: 测试摘要信息
            title: 报告标题
            
        Returns:
            str: HTML格式的报告内容
        """
        try:
            # 转换TestResult对象为字典格式
            converted_results = [convert_result_to_dict(result) for result in test_results]
            
            # 计算统计信息
            total_tests = len(converted_results)
            passed_tests = len([r for r in converted_results if r.get('status') == 'PASS'])
            failed_tests = len([r for r in converted_results if r.get('status') == 'FAIL'])
            error_tests = len([r for r in converted_results if r.get('status') == 'ERROR'])
            
            # 生成HTML报告
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{title}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
                    .summary {{ background-color: #e8f4fd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                    .results-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                    .results-table th, .results-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    .results-table th {{ background-color: #f2f2f2; }}
                    .pass {{ color: green; }}
                    .fail {{ color: red; }}
                    .error {{ color: orange; }}
                    .details {{ background-color: #fafafa; padding: 10px; margin: 5px 0; border-left: 3px solid #ccc; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{title}</h1>
                    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="summary">
                    <h2>测试摘要</h2>
                    <p><strong>总测试数:</strong> {total_tests}</p>
                    <p><strong>通过:</strong> <span class="pass">{passed_tests}</span></p>
                    <p><strong>失败:</strong> <span class="fail">{failed_tests}</span></p>
                    <p><strong>错误:</strong> <span class="error">{error_tests}</span></p>
                    <p><strong>成功率:</strong> {passed_tests/total_tests*100:.2f}%</p>
                    {f'<p><strong>执行时间:</strong> {summary.get("execution_time", "N/A")}秒</p>' if summary.get("execution_time") else ''}
                </div>
                
                <!-- 如果是性能测试报告，添加性能指标部分 -->
                {self._create_performance_metrics_section(summary) if self._has_performance_data(summary) else ''}
                
                <h2>详细测试结果</h2>
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>测试ID</th>
                            <th>测试名称</th>
                            <th>状态</th>
                            <th>执行时间(秒)</th>
                            <th>详情</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for result in converted_results:
                status_class = ''
                if result.get('status') == 'PASS':
                    status_class = 'pass'
                elif result.get('status') == 'FAIL':
                    status_class = 'fail'
                elif result.get('status') == 'ERROR':
                    status_class = 'error'
                
                html_content += f"""
                        <tr>
                            <td>{result.get('test_case_id', 'N/A')}</td>
                            <td>{result.get('test_name', 'N/A')}</td>
                            <td class="{status_class}">{result.get('status', 'N/A')}</td>
                            <td>{result.get('execution_time', 'N/A'):.2f}</td>
                            <td><div class="details">{result.get('details', 'N/A')}</div></td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"创建HTML报告失败: {e}")
            return f"创建报告失败: {e}"
    
    def _has_performance_data(self, summary: Dict[str, Any]) -> bool:
        """
        检查摘要中是否包含性能测试数据
        
        Args:
            summary: 测试摘要信息
            
        Returns:
            bool: 如果包含性能数据则返回True
        """
        performance_keys = [
            'average_response_time', 'throughput_calls_per_second', 
            'max_concurrent_calls', 'successful_calls', 'total_calls_attempted',
            'successful_registrations', 'num_registrations', 'registration_rate'
        ]
        return any(key in summary for key in performance_keys)
    
    def _create_performance_metrics_section(self, summary: Dict[str, Any]) -> str:
        """
        创建性能指标部分的HTML内容
        
        Args:
            summary: 包含性能数据的摘要信息
            
        Returns:
            str: 性能指标部分的HTML内容
        """
        try:
            html_content = '<div class="performance-metrics"><h2>性能指标</h2><ul>'
            
            # 呼叫性能指标
            if 'average_response_time' in summary:
                html_content += f'<li><strong>平均响应时间:</strong> {summary["average_response_time"]:.3f}秒</li>'
            
            if 'throughput_calls_per_second' in summary:
                html_content += f'<li><strong>呼叫吞吐量:</strong> {summary["throughput_calls_per_second"]:.2f} 呼叫/秒</li>'
            
            if 'max_concurrent_calls' in summary:
                html_content += f'<li><strong>最大并发呼叫数:</strong> {summary["max_concurrent_calls"]}</li>'
            
            # 呼叫成功率
            if 'successful_calls' in summary and 'total_calls_attempted' in summary:
                success_rate = (summary['successful_calls'] / summary['total_calls_attempted']) * 100 if summary['total_calls_attempted'] > 0 else 0
                html_content += f'<li><strong>呼叫成功率:</strong> {summary["successful_calls"]}/{summary["total_calls_attempted"]} ({success_rate:.2f}%)</li>'
            
            # 注册性能指标
            if 'successful_registrations' in summary and 'num_registrations' in summary:
                registration_success_rate = (summary['successful_registrations'] / summary['num_registrations']) * 100 if summary['num_registrations'] > 0 else 0
                html_content += f'<li><strong>注册成功率:</strong> {summary["successful_registrations"]}/{summary["num_registrations"]} ({registration_success_rate:.2f}%)</li>'
            
            if 'registration_rate' in summary:
                html_content += f'<li><strong>注册速率:</strong> {summary["registration_rate"]:.2f} 注册/秒</li>'
            
            # 并发性能指标
            if 'concurrent_test_results' in summary:
                html_content += '<li><strong>并发测试结果:</strong><ul>'
                for i, result in enumerate(summary['concurrent_test_results']):
                    html_content += f'<li>线程 {i+1}: {result}</li>'
                html_content += '</ul></li>'
            
            html_content += '</ul></div>'
            return html_content
            
        except Exception as e:
            self.logger.error(f"创建性能指标部分失败: {e}")
            return ''
    
    def send_report(self, recipients: List[str], subject: str, 
                   test_results: List[Dict[str, Any]], 
                   summary: Dict[str, Any] = None,
                   attachments: List[str] = None) -> bool:
        """
        发送测试报告邮件
        
        Args:
            recipients: 收件人邮箱列表
            subject: 邮件主题
            test_results: 测试结果列表
            summary: 测试摘要信息
            attachments: 附件文件路径列表
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # 创建HTML报告内容
            html_content = self.create_test_report_html(test_results, summary or {})
            
            # 添加HTML内容到邮件
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        msg.attach(part)
                        self.logger.info(f"已添加附件: {file_path}")
                    else:
                        self.logger.warning(f"附件文件不存在: {file_path}")
            
            # 连接SMTP服务器并发送邮件
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # 启用TLS加密
            server.login(self.username, self.password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, recipients, text)
            server.quit()
            
            self.logger.info(f"测试报告邮件已发送给: {recipients}")
            return True
            
        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
            return False
    
    def export_results_to_csv(self, test_results: List[Dict[str, Any]], 
                            file_path: str) -> bool:
        """
        将测试结果导出为CSV文件
        
        Args:
            test_results: 测试结果列表
            file_path: CSV文件保存路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            df = pd.DataFrame(test_results)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.info(f"测试结果已导出到CSV: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"导出CSV失败: {e}")
            return False
    
    def export_results_to_json(self, test_results: List[Dict[str, Any]], 
                             file_path: str) -> bool:
        """
        将测试结果导出为JSON文件
        
        Args:
            test_results: 测试结果列表
            file_path: JSON文件保存路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_results, f, ensure_ascii=False, indent=2)
            self.logger.info(f"测试结果已导出到JSON: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"导出JSON失败: {e}")
            return False


# 使用示例
if __name__ == "__main__":
    # 示例配置
    email_reporter = EmailReporter(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        username="your_email@gmail.com",
        password="your_app_password",  # 使用应用专用密码
        sender_email="your_email@gmail.com"
    )
    
    # 示例测试结果
    test_results = [
        {
            "test_case_id": "CALL_001",
            "test_name": "呼叫建立测试",
            "status": "PASS",
            "execution_time": 2.5,
            "details": "呼叫建立成功"
        },
        {
            "test_case_id": "REG_001", 
            "test_name": "用户注册测试",
            "status": "FAIL",
            "execution_time": 1.2,
            "details": "认证失败"
        },
        {
            "test_case_id": "MSG_001",
            "test_name": "消息发送测试", 
            "status": "PASS",
            "execution_time": 0.8,
            "details": "消息发送成功"
        }
    ]
    
    summary = {
        "execution_time": 10.5,
        "environment": "Test Environment",
        "tester": "AutoTestForUG System"
    }
    
    # 创建HTML报告
    html_report = email_reporter.create_test_report_html(test_results, summary)
    print("HTML报告已生成")
    
    # 导出CSV
    email_reporter.export_results_to_csv(test_results, "test_results.csv")
    
    # 导出JSON
    email_reporter.export_results_to_json(test_results, "test_results.json")
    
    print("邮件报告模块测试完成")