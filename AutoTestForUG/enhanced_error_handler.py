"""
增强的错误处理和SIP特定错误处理模块
为SIP基础测试提供更好的错误处理和日志记录功能
扩展原有的error_handler模块，增加了对SIP特定错误的处理
"""

import logging
import functools
import traceback
from typing import Callable, Any
from datetime import datetime
import json
import time
import socket
import re


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


class AuthenticationError(SIPTestError):
    """认证相关错误"""
    pass


class SIPProtocolError(SIPTestError):
    """SIP协议错误"""
    pass


class SIPRequestMergedError(SIPProtocolError):
    """SIP 482 Request Merged错误"""
    pass


def error_handler(func: Callable) -> Callable:
    """
    错误处理装饰器
    捕获函数执行过程中的异常并记录详细日志
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SIPTestError as e:
            logging.error(f"SIP测试错误在 {func.__name__}: {str(e)}")
            logging.debug(f"函数 {func.__name__} 的详细堆栈信息: {traceback.format_exc()}")
            raise
        except Exception as e:
            error_msg = f"未知错误在 {func.__name__}: {str(e)}"
            logging.error(error_msg)
            logging.debug(f"函数 {func.__name__} 的详细堆栈信息: {traceback.format_exc()}")
            raise SIPTestError(f"函数 {func.__name__} 执行失败: {str(e)}")
    return wrapper


def detailed_error_handler(func: Callable) -> Callable:
    """
    详细错误处理装饰器
    捕获函数执行过程中的异常并记录更详细的日志
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SIPTestError as e:
            error_details = {
                'function': func.__name__,
                'exception_type': type(e).__name__,
                'message': str(e),
                'args': str(args)[:500],  # 截断长参数
                'kwargs': str(kwargs)[:500],  # 截断长参数
                'traceback': traceback.format_exc()
            }
            logging.error(f"SIP测试错误详情: {json.dumps(error_details, ensure_ascii=False, indent=2)}")
            raise
        except Exception as e:
            error_details = {
                'function': func.__name__,
                'exception_type': type(e).__name__,
                'message': str(e),
                'args': str(args)[:500],
                'kwargs': str(kwargs)[:500],
                'traceback': traceback.format_exc()
            }
            logging.error(f"未知错误详情: {json.dumps(error_details, ensure_ascii=False, indent=2)}")
            raise SIPTestError(f"函数 {func.__name__} 执行失败: {str(e)}")
    return wrapper


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, exceptions_to_retry: tuple = (NetworkError, CallError, SIPRequestMergedError)):
    """
    失败重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        exceptions_to_retry: 需要重试的异常类型元组
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions_to_retry as e:
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
    
    def __init__(self, name: str = "SIPTest", log_file: str = "sip_test.log", level: int = logging.INFO):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 创建文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            
            # 创建格式化器 - 更详细的格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
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
        self.logger.debug(f"SIP消息 {direction}: {message[:500]}...")  # 增加记录长度
    
    def log_protocol_violation(self, message: str, details: dict = None):
        """记录协议违规"""
        details_str = f" 详情: {details}" if details else ""
        self.logger.warning(f"协议违规: {message}{details_str}")
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """记录性能指标"""
        unit_str = f" {unit}" if unit else ""
        self.logger.info(f"性能指标: {metric_name} = {value}{unit_str}")
    
    def log_state_change(self, old_state: str, new_state: str, context: str = ""):
        """记录状态变更"""
        context_str = f" 上下文: {context}" if context else ""
        self.logger.info(f"状态变更: {old_state} -> {new_state}{context_str}")


def validate_sip_uri(uri: str) -> bool:
    """
    验证SIP URI格式
    
    Args:
        uri: SIP URI
        
    Returns:
        bool: URI格式是否有效
    """
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
    skipped = results.get('skipped', 0)
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    return {
        'total_tests': total,
        'passed_tests': passed,
        'failed_tests': failed,
        'skipped_tests': skipped,
        'success_rate': success_rate,
        'start_time': results.get('start_time'),
        'end_time': results.get('end_time'),
        'total_duration': (results['end_time'] - results['start_time']).total_seconds() if results.get('start_time') and results.get('end_time') else 0
    }


def handle_network_error(error: Exception, operation: str = "network operation"):
    """
    专门处理网络错误
    
    Args:
        error: 异常对象
        operation: 操作描述
    """
    logging.error(f"网络错误在 {operation}: {str(error)}")
    logging.debug(f"网络错误详细信息: {traceback.format_exc()}")
    return NetworkError(f"{operation} 失败: {str(error)}")


def handle_authentication_error(error: Exception, operation: str = "authentication"):
    """
    专门处理认证错误
    
    Args:
        error: 异常对象
        operation: 操作描述
    """
    logging.error(f"认证错误在 {operation}: {str(error)}")
    logging.debug(f"认证错误详细信息: {traceback.format_exc()}")
    return AuthenticationError(f"{operation} 失败: {str(error)}")


def handle_protocol_error(error: Exception, operation: str = "protocol operation"):
    """
    专门处理协议错误
    
    Args:
        error: 异常对象
        operation: 操作描述
    """
    logging.error(f"协议错误在 {operation}: {str(error)}")
    logging.debug(f"协议错误详细信息: {traceback.format_exc()}")
    return SIPProtocolError(f"{operation} 失败: {str(error)}")


def handle_482_error(response: str, operation: str = "SIP request"):
    """
    专门处理482 Request Merged错误
    
    Args:
        response: SIP响应
        operation: 操作描述
    """
    logging.warning(f"检测到482错误在 {operation}: {response[:200]}...")
    return SIPRequestMergedError(f"{operation} 遇到482 Request Merged错误")


def handle_401_error(response: str, operation: str = "SIP request"):
    """
    专门处理401 Unauthorized错误
    
    Args:
        response: SIP响应
        operation: 操作描述
    """
    logging.info(f"检测到401错误在 {operation}: 需要认证")
    return AuthenticationError(f"{operation} 遇到401 Unauthorized错误")


def handle_407_error(response: str, operation: str = "SIP request"):
    """
    专门处理407 Proxy Authentication Required错误
    
    Args:
        response: SIP响应
        operation: 操作描述
    """
    logging.info(f"检测到407错误在 {operation}: 需要代理认证")
    return AuthenticationError(f"{operation} 遇到407 Proxy Authentication Required错误")


def handle_500_error(response: str, operation: str = "SIP request"):
    """
    专门处理500 Server Error错误
    
    Args:
        response: SIP响应
        operation: 操作描述
    """
    logging.error(f"检测到500错误在 {operation}: 服务器内部错误")
    return SIPProtocolError(f"{operation} 遇到500 Server Error错误")


def parse_sip_response_code(response: str) -> int:
    """
    从SIP响应中解析状态码
    
    Args:
        response: SIP响应字符串
        
    Returns:
        int: 状态码，如果解析失败返回0
    """
    try:
        lines = response.split('\r\n')
        if lines:
            first_line = lines[0]
            # SIP/2.0 200 OK 格式
            if first_line.startswith('SIP/2.0 '):
                parts = first_line.split(' ', 2)
                if len(parts) >= 2:
                    return int(parts[1])
    except (ValueError, IndexError):
        pass
    
    return 0


def categorize_sip_error(response: str, operation: str = "SIP request") -> Exception:
    """
    根据SIP响应状态码分类错误类型
    
    Args:
        response: SIP响应
        operation: 操作描述
        
    Returns:
        Exception: 对应的异常对象
    """
    status_code = parse_sip_response_code(response)
    
    if status_code == 401:
        return handle_401_error(response, operation)
    elif status_code == 407:
        return handle_407_error(response, operation)
    elif status_code == 482:
        return handle_482_error(response, operation)
    elif status_code == 500:
        return handle_500_error(response, operation)
    elif 400 <= status_code < 500:
        return SIPTestError(f"{operation} 遇到客户端错误 {status_code}")
    elif 500 <= status_code < 600:
        return SIPProtocolError(f"{operation} 遇到服务器错误 {status_code}")
    else:
        return SIPTestError(f"{operation} 遇到未知错误，状态码: {status_code}")


class SIPErrorHandler:
    """
    SIP特定错误处理类
    提供对各种SIP错误的专业处理方法
    """
    
    def __init__(self):
        self.error_handlers = {
            401: self._handle_401,
            407: self._handle_407,
            482: self._handle_482,
            500: self._handle_500,
            503: self._handle_503
        }
    
    def handle_error_by_code(self, status_code: int, response: str = "", operation: str = "SIP operation"):
        """
        根据状态码处理错误
        
        Args:
            status_code: HTTP/SIP状态码
            response: 完整响应
            operation: 操作描述
        """
        handler = self.error_handlers.get(status_code, self._handle_generic_error)
        return handler(status_code, response, operation)
    
    def _handle_401(self, status_code: int, response: str, operation: str):
        """处理401错误"""
        logging.info(f"处理401错误: {operation}")
        return AuthenticationError(f"{operation} 需要认证 (401 Unauthorized)")
    
    def _handle_407(self, status_code: int, response: str, operation: str):
        """处理407错误"""
        logging.info(f"处理407错误: {operation}")
        return AuthenticationError(f"{operation} 需要代理认证 (407 Proxy Authentication Required)")
    
    def _handle_482(self, status_code: int, response: str, operation: str):
        """处理482错误"""
        logging.warning(f"处理482错误: {operation}")
        return SIPRequestMergedError(f"{operation} 请求合并错误 (482 Request Merged)")
    
    def _handle_500(self, status_code: int, response: str, operation: str):
        """处理500错误"""
        logging.error(f"处理500错误: {operation}")
        return SIPProtocolError(f"{operation} 服务器内部错误 (500 Server Error)")
    
    def _handle_503(self, status_code: int, response: str, operation: str):
        """处理503错误"""
        logging.warning(f"处理503错误: {operation}")
        return SIPProtocolError(f"{operation} 服务不可用 (503 Service Unavailable)")
    
    def _handle_generic_error(self, status_code: int, response: str, operation: str):
        """处理通用错误"""
        logging.warning(f"处理通用错误 {status_code}: {operation}")
        return SIPTestError(f"{operation} 遇到错误 {status_code}")


# 创建全局错误处理器实例
sip_error_handler = SIPErrorHandler()

# 为了与现有代码兼容，导入time模块
import time