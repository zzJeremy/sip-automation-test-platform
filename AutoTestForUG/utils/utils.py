#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工具函数模块
提供AutoTestForUG系统中使用的通用工具函数
"""

import os
import sys
import time
import json
import csv
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import re
import socket
from urllib.parse import urlparse
import uuid


def get_current_timestamp() -> str:
    """
    获取当前时间戳字符串
    
    Returns:
        格式化的当前时间字符串
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_current_timestamp_ms() -> float:
    """
    获取当前时间戳（毫秒）
    
    Returns:
        当前时间戳（浮点数，包含毫秒）
    """
    return time.time()


def format_duration(seconds: float) -> str:
    """
    格式化持续时间
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时间字符串 (HH:MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def validate_ip_address(ip: str) -> bool:
    """
    验证IP地址格式
    
    Args:
        ip: IP地址字符串
        
    Returns:
        是否为有效IP地址
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def validate_uri(uri: str) -> bool:
    """
    验证URI格式
    
    Args:
        uri: URI字符串
        
    Returns:
        是否为有效URI
    """
    try:
        result = urlparse(uri)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def check_port_availability(host: str, port: int) -> bool:
    """
    检查端口是否可用
    
    Args:
        host: 主机地址
        port: 端口号
        
    Returns:
        端口是否可用
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # 如果连接失败，端口可用
    except Exception:
        return False


def create_directory_if_not_exists(path: str) -> bool:
    """
    如果目录不存在则创建目录
    
    Args:
        path: 目录路径
        
    Returns:
        是否成功创建或目录已存在
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"创建目录失败: {e}")
        return False


def write_json_file(data: Any, file_path: str, encoding: str = 'utf-8') -> bool:
    """
    将数据写入JSON文件
    
    Args:
        data: 要写入的数据
        file_path: 文件路径
        encoding: 文件编码
        
    Returns:
        是否写入成功
    """
    try:
        with open(file_path, 'w', encoding=encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"写入JSON文件失败: {e}")
        return False


def read_json_file(file_path: str, encoding: str = 'utf-8') -> Optional[Any]:
    """
    从JSON文件读取数据
    
    Args:
        file_path: 文件路径
        encoding: 文件编码
        
    Returns:
        读取的数据，失败时返回None
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"读取JSON文件失败: {e}")
        return None


def write_csv_file(data: List[Dict[str, Any]], file_path: str, encoding: str = 'utf-8-sig') -> bool:
    """
    将数据写入CSV文件
    
    Args:
        data: 要写入的数据列表，每个元素为字典
        file_path: 文件路径
        encoding: 文件编码
        
    Returns:
        是否写入成功
    """
    try:
        if not data:
            return True
            
        fieldnames = data[0].keys()
        with open(file_path, 'w', newline='', encoding=encoding) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        return True
    except Exception as e:
        logging.error(f"写入CSV文件失败: {e}")
        return False


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """
    计算数值列表的统计信息
    
    Args:
        values: 数值列表
        
    Returns:
        包含统计信息的字典 (平均值, 最小值, 最大值, 标准差)
    """
    if not values:
        return {
            'mean': 0.0,
            'min': 0.0,
            'max': 0.0,
            'std': 0.0,
            'count': 0
        }
    
    import statistics
    return {
        'mean': statistics.mean(values),
        'min': min(values),
        'max': max(values),
        'std': statistics.stdev(values) if len(values) > 1 else 0.0,
        'count': len(values)
    }


def format_bytes(bytes_value: int) -> str:
    """
    格式化字节数为可读格式
    
    Args:
        bytes_value: 字节数
        
    Returns:
        格式化后的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_percentage(value: float, total: float) -> str:
    """
    格式化百分比
    
    Args:
        value: 值
        total: 总数
        
    Returns:
        格式化后的百分比字符串
    """
    if total == 0:
        return "0.00%"
    percentage = (value / total) * 100
    return f"{percentage:.2f}%"


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 移除或替换不安全字符
    unsafe_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(unsafe_chars, '_', filename)
    
    # 限制文件名长度
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
    
    return sanitized


def get_file_size(file_path: str) -> int:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件大小（字节），如果文件不存在则返回0
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def is_file_older_than(file_path: str, seconds: int) -> bool:
    """
    检查文件是否比指定时间更旧
    
    Args:
        file_path: 文件路径
        seconds: 秒数
        
    Returns:
        文件是否比指定时间更旧
    """
    try:
        file_time = os.path.getmtime(file_path)
        current_time = time.time()
        return (current_time - file_time) > seconds
    except OSError:
        return True  # 如果无法获取文件时间，认为文件已过期


def wait_for_file(file_path: str, timeout: int = 30) -> bool:
    """
    等待文件出现
    
    Args:
        file_path: 文件路径
        timeout: 超时时间（秒）
        
    Returns:
        文件是否在超时前出现
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(file_path):
            return True
        time.sleep(0.1)
    return False


def get_available_disk_space(path: str) -> int:
    """
    获取指定路径的可用磁盘空间
    
    Args:
        path: 路径
        
    Returns:
        可用空间（字节）
    """
    try:
        import shutil
        _, _, free = shutil.disk_usage(path)
        return free
    except Exception:
        return 0


def format_network_traffic(bytes_value: int) -> str:
    """
    格式化网络流量为可读格式
    
    Args:
        bytes_value: 字节数
        
    Returns:
        格式化后的字符串
    """
    return format_bytes(bytes_value)


def parse_sip_message(message: str) -> Optional[Dict[str, Any]]:
    """
    解析SIP消息
    
    Args:
        message: SIP消息字符串
        
    Returns:
        解析后的SIP消息信息
    """
    try:
        lines = message.strip().split('\r\n')
        if not lines:
            return None
        
        # 解析请求行或状态行
        first_line = lines[0].strip()
        parts = first_line.split(' ', 2)
        
        if len(parts) < 2:
            return None
        
        result = {
            'headers': {},
            'body': '',
            'is_request': parts[0].upper() in ['INVITE', 'ACK', 'BYE', 'CANCEL', 'OPTIONS', 'REGISTER', 'MESSAGE']
        }
        
        if result['is_request']:
            result['method'] = parts[0]
            result['uri'] = parts[1]
            result['version'] = parts[2] if len(parts) > 2 else 'SIP/2.0'
        else:
            result['version'] = parts[0]
            result['status_code'] = int(parts[1])
            result['reason'] = parts[2] if len(parts) > 2 else ''
        
        # 解析头部
        body_start = 1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '':
                body_start = i + 1
                break
            if ':' in line:
                key, value = line.split(':', 1)
                result['headers'][key.strip()] = value.strip()
        
        # 解析消息体
        if body_start < len(lines):
            result['body'] = '\r\n'.join(lines[body_start:])
        
        return result
    except Exception as e:
        logging.error(f"解析SIP消息失败: {e}")
        return None


def generate_test_report(results: List[Dict[str, Any]], output_file: str) -> bool:
    """
    生成测试报告
    
    Args:
        results: 测试结果列表
        output_file: 输出文件路径
        
    Returns:
        是否生成成功
    """
    try:
        # 统计信息
        total_tests = len(results)
        passed = sum(1 for r in results if r.get('status') == 'PASS')
        failed = sum(1 for r in results if r.get('status') == 'FAIL')
        errors = sum(1 for r in results if r.get('status') == 'ERROR')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("AutoTestForUG - 测试报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成时间: {get_current_timestamp()}\n")
            f.write(f"测试总数: {total_tests}\n")
            f.write(f"通过: {passed}\n")
            f.write(f"失败: {failed}\n")
            f.write(f"错误: {errors}\n")
            if total_tests > 0:
                f.write(f"通过率: {format_percentage(passed, total_tests)}\n")
            f.write("\n详细结果:\n")
            f.write("-" * 50 + "\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"{i}. 测试用例: {result.get('test_case_id', 'Unknown')}\n")
                f.write(f"   状态: {result.get('status', 'Unknown')}\n")
                f.write(f"   执行时间: {result.get('execution_time', 0):.2f}s\n")
                f.write(f"   详情: {result.get('details', '')}\n")
                f.write("-" * 30 + "\n")
        
        return True
    except Exception as e:
        logging.error(f"生成测试报告失败: {e}")
        return False


def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 记录器名称
        log_file: 日志文件路径
        level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger


def convert_size_to_bytes(size_str: str) -> int:
    """
    将带单位的大小字符串转换为字节数
    
    Args:
        size_str: 大小字符串 (如 '10MB', '5GB')
        
    Returns:
        对应的字节数
    """
    size_str = size_str.strip().upper()
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4
    }
    
    # 提取数字和单位
    import re
    match = re.match(r'(\d+(?:\.\d+)?)\s*([A-Z]+)', size_str)
    if not match:
        raise ValueError(f"无法解析大小字符串: {size_str}")
    
    number, unit = match.groups()
    if unit not in units:
        raise ValueError(f"未知单位: {unit}")
    
    return int(float(number) * units[unit])


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """
    合并两个字典，dict2的值会覆盖dict1的值
    
    Args:
        dict1: 第一个字典
        dict2: 第二个字典
        
    Returns:
        合并后的字典
    """
    result = dict1.copy()
    result.update(dict2)
    return result


def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """
    深度合并两个字典
    
    Args:
        dict1: 第个字典
        dict2: 第二个字典
        
    Returns:
        深度合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """
    将嵌套字典扁平化
    
    Args:
        d: 嵌套字典
        parent_key: 父键
        sep: 分隔符
        
    Returns:
        扁平化后的字典
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def get_network_latency(host: str, port: int, timeout: int = 3) -> Optional[float]:
    """
    获取网络延迟
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间
        
    Returns:
        延迟时间（秒），失败时返回None
    """
    try:
        start_time = time.time()
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return time.time() - start_time
    except Exception:
        return None


def is_port_open(host: str, port: int, timeout: int = 3) -> bool:
    """
    检查端口是否开放
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间
        
    Returns:
        端口是否开放
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def generate_unique_id(prefix: str = "") -> str:
    """
    生成唯一ID
    
    Args:
        prefix: ID前缀
        
    Returns:
        唯一ID字符串
    """
    unique_id = str(uuid.uuid4()).replace('-', '')
    return f"{prefix}{unique_id}" if prefix else unique_id


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    else:
                        raise last_exception
            return None
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试工具函数
    print("当前时间戳:", get_current_timestamp())
    print("格式化持续时间 (3661秒):", format_duration(3661))
    print("验证IP地址 '192.168.1.1':", validate_ip_address("192.168.1.1"))
    print("格式化字节 1048576:", format_bytes(1048576))
    print("10/50 的百分比:", format_percentage(10, 50))
    print("清理文件名 'test<file>.txt':", sanitize_filename("test<file>.txt"))
    print("生成唯一ID:", generate_unique_id("test_"))
    print("检查端口可用性 127.0.0.1:80:", is_port_open("127.0.0.1", 80))