"""
SIP测试结果报告生成器
整合pytest的结果并生成定制化的SIP测试报告
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import os


class SIPTestReportGenerator:
    """SIP测试报告生成器"""
    
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_pytest_html_report(self, pytest_args: List[str] = None):
        """生成pytest HTML报告"""
        import subprocess
        import sys
        
        cmd = [sys.executable, "-m", "pytest"]
        
        if pytest_args:
            cmd.extend(pytest_args)
        else:
            # 默认运行SIP测试
            cmd.extend([
                "AutoTestForUG/pytest_sip_tests/",
                "-v",
                "--html=report.html",
                "--self-contained-html",
                "-m", "sip_basic"
            ])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            print(f"pytest执行完成，返回码: {result.returncode}")
            if result.stdout:
                print("标准输出:", result.stdout[-500:])  # 只显示最后500个字符
            if result.stderr:
                print("错误输出:", result.stderr[-500:])
        except Exception as e:
            print(f"执行pytest时出错: {e}")
    
    def generate_custom_report(self, test_results: Dict[str, Any], format_type: str = "json"):
        """生成自定义格式的测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type.lower() == "json":
            filename = self.output_dir / f"sip_test_report_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(test_results, f, ensure_ascii=False, indent=2, default=self._json_serializer)
        
        elif format_type.lower() == "txt":
            filename = self.output_dir / f"sip_test_report_{timestamp}.txt"
            self._write_text_report(test_results, filename)
        
        elif format_type.lower() == "html":
            filename = self.output_dir / f"sip_test_report_{timestamp}.html"
            self._write_html_report(test_results, filename)
        
        print(f"报告已生成: {filename}")
        return str(filename)
    
    def _json_serializer(self, obj):
        """JSON序列化器，处理datetime等特殊对象"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _write_text_report(self, results: Dict[str, Any], filename: Path):
        """写入文本格式报告"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("SIP 自动化测试报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 汇总信息
            total = results.get('total', 0)
            passed = results.get('passed', 0)
            failed = results.get('failed', 0)
            error = results.get('error', 0)
            
            f.write(f"总计测试: {total}\n")
            f.write(f"通过: {passed}\n")
            f.write(f"失败: {failed}\n")
            f.write(f"错误: {error}\n")
            f.write(f"成功率: {(passed/total*100):.2f}%\n\n" if total > 0 else "成功率: 0%\n\n")
            
            # 详细结果
            f.write("详细测试结果:\n")
            f.write("-" * 30 + "\n")
            
            test_details = results.get('details', [])
            for detail in test_details:
                f.write(f"测试: {detail.get('name', 'Unknown')}\n")
                f.write(f"  结果: {detail.get('status', 'unknown')}\n")
                f.write(f"  耗时: {detail.get('duration', 0):.2f}s\n")
                if 'error' in detail:
                    f.write(f"  错误: {detail['error']}\n")
                f.write("\n")
    
    def _write_html_report(self, results: Dict[str, Any], filename: Path):
        """写入HTML格式报告"""
        # 安全地获取测试结果值，避免除零错误
        total = results.get('total', 0)
        passed = results.get('passed', 0)
        failed = results.get('failed', 0)
        error = results.get('error', 0)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>SIP 自动化测试报告</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .summary {{ background-color: #e8f4fd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .test-case {{ border: 1px solid #ddd; margin: 10px 0; padding: 10px; border-radius: 5px; }}
        .passed {{ border-left: 5px solid #4CAF50; }}
        .failed {{ border-left: 5px solid #f44336; }}
        .error {{ border-left: 5px solid #ff9800; }}
        .stats {{ display: inline-block; margin-right: 20px; }}
        .stats-box {{ display: inline-flex; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SIP 自动化测试报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>测试汇总</h2>
        <div class="stats-box">
            <div class="stats">
                <strong>总计:</strong> {total}<br>
                <strong>通过:</strong> {passed}
            </div>
            <div class="stats">
                <strong>失败:</strong> {failed}<br>
                <strong>错误:</strong> {error}
            </div>
            <div class="stats">
                <strong>成功率:</strong> {success_rate:.2f}%
            </div>
        </div>
    </div>"""
        
        # 添加测试详情
        test_details = results.get('details', [])
        for detail in test_details:
            status_class = {
                'passed': 'passed',
                'failed': 'failed',
                'error': 'error'
            }.get(detail.get('status', 'unknown'), 'failed')
            
            html_content += f"""
    <div class="test-case {status_class}">
        <h3>{detail.get('name', 'Unknown')}</h3>
        <p><strong>状态:</strong> {detail.get('status', 'unknown')}</p>
        <p><strong>耗时:</strong> {detail.get('duration', 0):.2f}s</p>"""
            if 'error' in detail:
                html_content += f"""
        <p><strong>错误:</strong> {detail['error']}</p>"""
            html_content += """
    </div>"""
        
        html_content += """
</body>
</html>"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def integrate_with_pytest_hook(self):
        """与pytest钩子集成的方法"""
        # 这里可以实现与pytest生命周期的集成
        # 例如，在测试开始、结束时执行特定操作
        pass


def generate_sip_test_report():
    """生成SIP测试报告的便捷函数"""
    generator = SIPTestReportGenerator()
    
    # 示例测试结果
    sample_results = {
        'total': 5,
        'passed': 4,
        'failed': 1,
        'error': 0,
        'details': [
            {
                'name': 'test_basic_sip_call[config0]',
                'status': 'passed',
                'duration': 2.34,
                'description': '基础SIP呼叫测试'
            },
            {
                'name': 'test_basic_sip_call[config1]', 
                'status': 'passed',
                'duration': 1.87,
                'description': '基础SIP呼叫测试'
            },
            {
                'name': 'test_sip_call_flow_with_dsl',
                'status': 'passed', 
                'duration': 3.21,
                'description': 'DSL呼叫流程测试'
            },
            {
                'name': 'test_sip_message_format',
                'status': 'passed',
                'duration': 0.45,
                'description': 'SIP消息格式测试'
            },
            {
                'name': 'test_complex_call_scenario',
                'status': 'failed',
                'duration': 5.67,
                'description': '复杂呼叫场景测试',
                'error': '连接超时'
            }
        ]
    }
    
    # 生成多种格式的报告
    generator.generate_custom_report(sample_results, "json")
    generator.generate_custom_report(sample_results, "txt") 
    generator.generate_custom_report(sample_results, "html")
    
    # 可选：运行pytest并生成HTML报告
    # generator.generate_pytest_html_report()


if __name__ == "__main__":
    generate_sip_test_report()