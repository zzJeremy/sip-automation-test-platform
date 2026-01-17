"""
核心层包 - SIP自动化测试系统
提供核心测试执行引擎、DSL、报告生成等功能
"""
from .pytest_integration import *

# 导入核心功能
from .test_engine import TestEngine
from .report_generator import ReportGenerator
from .pytest_integration.sip_dsl import SIPDSL

__all__ = [
    'TestEngine',
    'ReportGenerator',
    'SIPDSL'
]