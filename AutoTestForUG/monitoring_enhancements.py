"""
SIP客户端增强监控和日志模块
提供性能监控、实时日志记录和统计分析功能
"""

import logging
import time
import json
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
import statistics
import psutil
import os


class SIPPerformanceMetrics:
    """
    SIP性能指标收集器
    跟踪和分析SIP操作的性能数据
    """
    
    def __init__(self):
        self.metrics = {
            'registration_times': deque(maxlen=100),  # 最近100次注册时间
            'call_setup_times': deque(maxlen=100),    # 最近100次呼叫建立时间
            'message_send_times': deque(maxlen=100),  # 最近100次消息发送时间
            'response_times': deque(maxlen=100),      # 最近100次响应时间
            'error_counts': defaultdict(int),         # 错误计数
            'success_counts': defaultdict(int),       # 成功计数
            'active_calls': 0,                        # 活跃呼叫数
            'total_registrations': 0,                 # 总注册数
            'total_calls': 0,                         # 总呼叫数
            'total_messages': 0,                      # 总消息数
        }
        self.lock = threading.Lock()
    
    def record_registration_time(self, duration: float):
        """记录注册时间"""
        with self.lock:
            self.metrics['registration_times'].append(duration)
            self.metrics['total_registrations'] += 1
    
    def record_call_setup_time(self, duration: float):
        """记录呼叫建立时间"""
        with self.lock:
            self.metrics['call_setup_times'].append(duration)
            self.metrics['total_calls'] += 1
    
    def record_message_send_time(self, duration: float):
        """记录消息发送时间"""
        with self.lock:
            self.metrics['message_send_times'].append(duration)
            self.metrics['total_messages'] += 1
    
    def record_response_time(self, duration: float):
        """记录响应时间"""
        with self.lock:
            self.metrics['response_times'].append(duration)
    
    def increment_error_count(self, error_type: str):
        """增加错误计数"""
        with self.lock:
            self.metrics['error_counts'][error_type] += 1
    
    def increment_success_count(self, operation: str):
        """增加成功计数"""
        with self.lock:
            self.metrics['success_counts'][operation] += 1
    
    def set_active_calls(self, count: int):
        """设置活跃呼叫数"""
        with self.lock:
            self.metrics['active_calls'] = count
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            stats = {}
            
            # 计算注册时间统计
            if self.metrics['registration_times']:
                times = list(self.metrics['registration_times'])
                stats['registration'] = {
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'median_time': statistics.median(times) if len(times) > 0 else 0,
                    'count': len(times)
                }
            
            # 计算呼叫建立时间统计
            if self.metrics['call_setup_times']:
                times = list(self.metrics['call_setup_times'])
                stats['call_setup'] = {
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'median_time': statistics.median(times) if len(times) > 0 else 0,
                    'count': len(times)
                }
            
            # 计算消息发送时间统计
            if self.metrics['message_send_times']:
                times = list(self.metrics['message_send_times'])
                stats['message_send'] = {
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'median_time': statistics.median(times) if len(times) > 0 else 0,
                    'count': len(times)
                }
            
            # 计算响应时间统计
            if self.metrics['response_times']:
                times = list(self.metrics['response_times'])
                stats['response'] = {
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'median_time': statistics.median(times) if len(times) > 0 else 0,
                    'count': len(times)
                }
            
            # 添加计数统计
            stats['counts'] = {
                'total_registrations': self.metrics['total_registrations'],
                'total_calls': self.metrics['total_calls'],
                'total_messages': self.metrics['total_messages'],
                'active_calls': self.metrics['active_calls'],
                'error_counts': dict(self.metrics['error_counts']),
                'success_counts': dict(self.metrics['success_counts'])
            }
            
            return stats


class SIPEventLogger:
    """
    SIP事件日志记录器
    提供结构化的事件记录和查询功能
    """
    
    def __init__(self, log_file: str = "sip_events.log", max_events: int = 10000):
        self.log_file = log_file
        self.events = deque(maxlen=max_events)
        self.system_stats_enabled = True
        
        # 设置日志记录器
        self.logger = logging.getLogger('SIPEventLogger')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_event(self, event_type: str, operation: str, details: Dict[str, Any], 
                  success: bool = True, duration: Optional[float] = None):
        """记录SIP事件"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'operation': operation,
            'details': details,
            'success': success,
            'duration': duration,
            'system_stats': self._get_system_stats() if self.system_stats_enabled else None
        }
        
        # 添加到内存队列
        self.events.append(event)
        
        # 记录到文件
        log_msg = f"{event_type.upper()} - {operation}: {details} - Success: {success}"
        if duration:
            log_msg += f" - Duration: {duration:.3f}s"
        
        if success:
            self.logger.info(log_msg)
        else:
            self.logger.error(log_msg)
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent,
                'process_memory_mb': psutil.Process().memory_info().rss / 1024 / 1024
            }
        except:
            return {}
    
    def query_events(self, event_type: Optional[str] = None, operation: Optional[str] = None, 
                     success: Optional[bool] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """查询事件"""
        results = []
        
        for event in reversed(self.events):  # 从最新的事件开始
            if (event_type is None or event['event_type'] == event_type) and \
               (operation is None or event['operation'] == operation) and \
               (success is None or event['success'] == success):
                results.append(event)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的错误事件"""
        return self.query_events(success=False, limit=limit)
    
    def export_events(self, filename: str, event_type: Optional[str] = None) -> bool:
        """导出事件到文件"""
        try:
            events_to_export = self.events
            if event_type:
                events_to_export = [e for e in self.events if e['event_type'] == event_type]
            
            with open(filename, 'w', encoding='utf-8') as f:
                for event in events_to_export:
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')
            
            return True
        except Exception as e:
            self.logger.error(f"导出事件失败: {str(e)}")
            return False


class SIPMonitor:
    """
    SIP监控器
    综合性能指标收集和事件记录
    """
    
    def __init__(self, enable_realtime_monitoring: bool = True):
        self.performance_metrics = SIPPerformanceMetrics()
        self.event_logger = SIPEventLogger()
        self.enable_realtime_monitoring = enable_realtime_monitoring
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        
        if self.enable_realtime_monitoring:
            self._start_monitoring_thread()
    
    def _start_monitoring_thread(self):
        """启动监控线程"""
        def monitoring_loop():
            while not self.stop_monitoring.wait(30):  # 每30秒记录一次系统指标
                try:
                    system_stats = self.event_logger._get_system_stats()
                    self.event_logger.log_event(
                        event_type='system_monitoring',
                        operation='health_check',
                        details={'stats': system_stats},
                        success=True
                    )
                except Exception as e:
                    self.event_logger.logger.warning(f"监控循环出错: {str(e)}")
        
        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def log_registration_event(self, username: str, domain: str, success: bool, duration: float = None):
        """记录注册事件"""
        details = {
            'username': username,
            'domain': domain
        }
        self.event_logger.log_event(
            event_type='registration',
            operation='register',
            details=details,
            success=success,
            duration=duration
        )
        
        if success and duration:
            self.performance_metrics.record_registration_time(duration)
        
        if not success:
            self.performance_metrics.increment_error_count('registration_failed')
        else:
            self.performance_metrics.increment_success_count('registration')
    
    def log_call_event(self, caller: str, callee: str, success: bool, duration: float = None):
        """记录呼叫事件"""
        details = {
            'caller': caller,
            'callee': callee
        }
        self.event_logger.log_event(
            event_type='call',
            operation='make_call',
            details=details,
            success=success,
            duration=duration
        )
        
        if success and duration:
            self.performance_metrics.record_call_setup_time(duration)
        
        if not success:
            self.performance_metrics.increment_error_count('call_failed')
        else:
            self.performance_metrics.increment_success_count('call')
    
    def log_message_event(self, sender: str, receiver: str, success: bool, duration: float = None):
        """记录消息事件"""
        details = {
            'sender': sender,
            'receiver': receiver
        }
        self.event_logger.log_event(
            event_type='message',
            operation='send_message',
            details=details,
            success=success,
            duration=duration
        )
        
        if success and duration:
            self.performance_metrics.record_message_send_time(duration)
        
        if not success:
            self.performance_metrics.increment_error_count('message_failed')
        else:
            self.performance_metrics.increment_success_count('message')
    
    def log_response_event(self, method: str, status_code: int, duration: float):
        """记录响应事件"""
        details = {
            'method': method,
            'status_code': status_code
        }
        success = 200 <= status_code < 300
        self.event_logger.log_event(
            event_type='response',
            operation='receive_response',
            details=details,
            success=success,
            duration=duration
        )
        
        self.performance_metrics.record_response_time(duration)
        
        if not success:
            self.performance_metrics.increment_error_count(f'status_{status_code}')
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取综合统计信息"""
        stats = self.performance_metrics.get_statistics()
        stats['events_count'] = len(self.event_logger.events)
        return stats
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的错误"""
        return self.event_logger.get_recent_errors(limit)
    
    def export_report(self, filename: str) -> bool:
        """导出监控报告"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'statistics': self.get_statistics(),
                'recent_errors': self.get_recent_errors(20)
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            self.event_logger.logger.error(f"导出报告失败: {str(e)}")
            return False
    
    def stop(self):
        """停止监控"""
        self.stop_monitoring.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)


class SIPMonitoringDecorator:
    """
    SIP监控装饰器
    用于自动监控方法调用
    """
    
    def __init__(self, monitor: SIPMonitor):
        self.monitor = monitor
    
    def monitor_registration(self, username: str, domain: str):
        """监控注册方法的装饰器工厂"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.monitor.log_registration_event(username, domain, result, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.monitor.log_registration_event(username, domain, False, duration)
                    raise
            return wrapper
        return decorator
    
    def monitor_call(self, caller: str, callee: str):
        """监控呼叫方法的装饰器工厂"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.monitor.log_call_event(caller, callee, result, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.monitor.log_call_event(caller, callee, False, duration)
                    raise
            return wrapper
        return decorator
    
    def monitor_message(self, sender: str, receiver: str):
        """监控消息方法的装饰器工厂"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.monitor.log_message_event(sender, receiver, result, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.monitor.log_message_event(sender, receiver, False, duration)
                    raise
            return wrapper
        return decorator


# 全局监控实例
sip_monitor = SIPMonitor(enable_realtime_monitoring=True)