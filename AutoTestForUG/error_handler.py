"""
增强的错误处理和日志记录模块
为SIP基础测试提供更好的错误处理和日志记录功能
"""

import logging
import functools
from typing import Callable, Any
from datetime import datetime


class SIPTestError(Exception):
    """SIP测试相关的自定义异常"""
    pass


class RegistrationError(SIPTestError):
    """注册相关错误"""
    pass


class CallError(SIPTestError):
    """呼叫相关错误"""
    pass


class MessageError(SIPTestError):
    """消息相关错误"""
    pass


class NetworkError(SIPTestError):
    """网络相关错误"""
    pass


def error_handler(func: Callable) -> Callable:
    """
    错误处理装饰器
    捕获函数执行过程中的异常并记录日志
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SIPTestError as e:
            logging.error(f"SIP测试错误在 {func.__name__}: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"未知错误在 {func.__name__}: {str(e)}")
            raise SIPTestError(f"函数 {func.__name__} 执行失败: {str(e)}")
    return wrapper


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    失败重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (NetworkError, CallError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}，{delay}秒后重试...")
                        time.sleep(delay)
                    else:
                        logging.error(f"函数 {func.__name__} 经过 {max_retries} 次重试后仍然失败: {str(e)}")
            
            raise last_exception
        return wrapper
    return decorator


class SIPTestLogger:
    """
    SIP测试专用日志记录器
    提供结构化的日志记录功能
    """
    
    def __init__(self, name: str = "SIPTest", log_file: str = "sip_test.log"):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def log_test_start(self, test_name: str, params: dict = None):
        """记录测试开始"""
        params_str = f" 参数: {params}" if params else ""
        self.logger.info(f"开始测试: {test_name}{params_str}")
    
    def log_test_success(self, test_name: str, duration: float = None):
        """记录测试成功"""
        duration_str = f" 耗时: {duration:.2f}秒" if duration else ""
        self.logger.info(f"测试成功: {test_name}{duration_str}")
    
    def log_test_failure(self, test_name: str, error: Exception = None):
        """记录测试失败"""
        error_str = f" 错误: {str(error)}" if error else ""
        self.logger.error(f"测试失败: {test_name}{error_str}")
    
    def log_sip_message(self, direction: str, message: str):
        """记录SIP消息"""
        self.logger.debug(f"SIP消息 {direction}: {message[:200]}...")  # 只记录前200个字符


def validate_sip_uri(uri: str) -> bool:
    """
    验证SIP URI格式
    
    Args:
        uri: SIP URI
        
    Returns:
        bool: URI格式是否有效
    """
    import re
    sip_uri_pattern = r'^sip:[a-zA-Z0-9_.!~*\'();:&=+$,-]+@([a-zA-Z0-9.-]+|\[[0-9a-fA-F:.]+\])(:[0-9]+)?$'
    return bool(re.match(sip_uri_pattern, uri))


def format_sip_message(message: str) -> str:
    """
    格式化SIP消息以供日志记录
    
    Args:
        message: SIP消息
        
    Returns:
        str: 格式化后的消息
    """
    lines = message.split('\r\n')
    formatted_lines = []
    
    for line in lines:
        # 隐藏敏感信息如密码
        if 'Authorization:' in line or 'Proxy-Authorization:' in line:
            formatted_lines.append(line.split(':')[0] + ': [HIDDEN]')
        else:
            formatted_lines.append(line)
    
    return '\r\n'.join(formatted_lines)


def create_test_summary(results: dict) -> dict:
    """
    创建测试摘要
    
    Args:
        results: 测试结果
        
    Returns:
        dict: 测试摘要
    """
    total = results.get('total', 0)
    passed = results.get('passed', 0)
    failed = results.get('failed', 0)
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    return {
        'total_tests': total,
        'passed_tests': passed,
        'failed_tests': failed,
        'success_rate': success_rate,
        'start_time': results.get('start_time'),
        'end_time': results.get('end_time'),
        'total_duration': (results['end_time'] - results['start_time']).total_seconds() if results.get('start_time') and results.get('end_time') else 0
    }


# 为了与现有代码兼容，导入time模块
import time