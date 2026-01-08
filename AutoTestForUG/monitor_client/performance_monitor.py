#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能监控模块
用于监控软交换系统的性能指标，包括CPU、内存、磁盘、网络等
"""

import logging
import time
import threading
import psutil
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import csv
import os
from pathlib import Path

from utils.utils import setup_logger


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, float]  # {'bytes_sent': float, 'bytes_recv': float}
    process_count: int
    thread_count: int
    custom_metrics: Dict[str, Any] = None


class PerformanceMonitor:
    """性能监控器类"""
    
    def __init__(self, config_path: str = None, log_file: str = "performance.log"):
        """
        初始化性能监控器
        
        Args:
            config_path: 配置文件路径
            log_file: 日志文件路径
        """
        self.logger = setup_logger("PerformanceMonitor", log_file)
        self.is_monitoring = False
        self.monitoring_thread = None
        self.metrics_history: List[PerformanceMetrics] = []
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0
        }
        self.alert_callbacks: List[Callable[[str, Any, Any], None]] = []
        
        # 加载配置
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
        
        self.logger.info("性能监控器初始化完成")
    
    def load_config(self, config_path: str):
        """
        从配置文件加载阈值
        
        Args:
            config_path: 配置文件路径
        """
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            
            if 'PERFORMANCE' in config:
                for key in self.thresholds:
                    if config.has_option('PERFORMANCE', key):
                        self.thresholds[key] = config.getfloat('PERFORMANCE', key)
            
            self.logger.info(f"从配置文件 {config_path} 加载阈值设置")
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
    
    def add_alert_callback(self, callback: Callable[[str, Any, Any], None]):
        """
        添加告警回调函数
        
        Args:
            callback: 回调函数，接收(指标名称, 当前值, 阈值)参数
        """
        self.alert_callbacks.append(callback)
    
    def check_thresholds(self, metrics: PerformanceMetrics):
        """
        检查性能指标是否超过阈值
        
        Args:
            metrics: 性能指标
        """
        try:
            # 检查CPU使用率
            if metrics.cpu_percent > self.thresholds['cpu_percent']:
                alert_msg = f"CPU使用率超过阈值: {metrics.cpu_percent}% > {self.thresholds['cpu_percent']}%"
                self.logger.warning(alert_msg)
                
                for callback in self.alert_callbacks:
                    try:
                        callback('cpu_percent', metrics.cpu_percent, self.thresholds['cpu_percent'])
                    except Exception as e:
                        self.logger.error(f"执行告警回调失败: {e}")
            
            # 检查内存使用率
            if metrics.memory_percent > self.thresholds['memory_percent']:
                alert_msg = f"内存使用率超过阈值: {metrics.memory_percent}% > {self.thresholds['memory_percent']}%"
                self.logger.warning(alert_msg)
                
                for callback in self.alert_callbacks:
                    try:
                        callback('memory_percent', metrics.memory_percent, self.thresholds['memory_percent'])
                    except Exception as e:
                        self.logger.error(f"执行告警回调失败: {e}")
            
            # 检查磁盘使用率
            if metrics.disk_percent > self.thresholds['disk_percent']:
                alert_msg = f"磁盘使用率超过阈值: {metrics.disk_percent}% > {self.thresholds['disk_percent']}%"
                self.logger.warning(alert_msg)
                
                for callback in self.alert_callbacks:
                    try:
                        callback('disk_percent', metrics.disk_percent, self.thresholds['disk_percent'])
                    except Exception as e:
                        self.logger.error(f"执行告警回调失败: {e}")
        
        except Exception as e:
            self.logger.error(f"检查阈值时发生错误: {e}")
    
    def collect_metrics(self) -> PerformanceMetrics:
        """
        收集当前系统性能指标
        
        Returns:
            PerformanceMetrics: 性能指标数据
        """
        try:
            # 获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 获取内存使用率
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            
            # 获取磁盘使用率
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            # 获取网络IO统计
            net_io = psutil.net_io_counters()
            network_io = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
            
            # 获取进程和线程数量
            process_count = len(psutil.pids())
            thread_count = threading.active_count()
            
            # 创建性能指标对象
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io,
                process_count=process_count,
                thread_count=thread_count,
                custom_metrics={}
            )
            
            return metrics
        
        except Exception as e:
            self.logger.error(f"收集性能指标时发生错误: {e}")
            # 返回默认值避免程序崩溃
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_io={'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0},
                process_count=0,
                thread_count=0
            )
    
    def monitoring_loop(self):
        """监控循环，持续收集性能指标"""
        self.logger.info("开始性能监控循环")
        
        while self.is_monitoring:
            try:
                # 收集性能指标
                metrics = self.collect_metrics()
                
                # 添加到历史记录
                self.metrics_history.append(metrics)
                
                # 检查阈值
                self.check_thresholds(metrics)
                
                # 限制历史记录大小，避免内存溢出
                if len(self.metrics_history) > 10000:  # 保留最近10000条记录
                    self.metrics_history = self.metrics_history[-5000:]  # 保留后5000条
                
                # 等待指定时间后继续
                time.sleep(5)  # 每5秒收集一次
                
            except Exception as e:
                self.logger.error(f"监控循环中发生错误: {e}")
                time.sleep(5)  # 出错后等待5秒再继续
        
        self.logger.info("性能监控循环结束")
    
    def start_monitoring(self):
        """开始性能监控"""
        if self.is_monitoring:
            self.logger.warning("性能监控已在运行中")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止性能监控"""
        if not self.is_monitoring:
            self.logger.warning("性能监控未运行")
            return
        
        self.is_monitoring = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)  # 最多等待2秒
        
        self.logger.info("性能监控已停止")
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """
        获取当前性能指标
        
        Returns:
            PerformanceMetrics: 当前性能指标
        """
        return self.collect_metrics()
    
    def get_metrics_history(self, last_n: int = None) -> List[PerformanceMetrics]:
        """
        获取性能指标历史记录
        
        Args:
            last_n: 返回最近n条记录，None表示返回所有记录
            
        Returns:
            List[PerformanceMetrics]: 性能指标历史记录
        """
        if last_n is None:
            return self.metrics_history.copy()
        else:
            return self.metrics_history[-last_n:].copy()
    
    def export_metrics_to_csv(self, file_path: str, last_n: int = None):
        """
        导出性能指标到CSV文件
        
        Args:
            file_path: CSV文件路径
            last_n: 导出最近n条记录，None表示导出所有记录
        """
        try:
            metrics_list = self.get_metrics_history(last_n)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'timestamp', 'cpu_percent', 'memory_percent', 'disk_percent',
                    'network_bytes_sent', 'network_bytes_recv', 'network_packets_sent', 'network_packets_recv',
                    'process_count', 'thread_count'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for metrics in metrics_list:
                    row = {
                        'timestamp': datetime.fromtimestamp(metrics.timestamp).isoformat(),
                        'cpu_percent': metrics.cpu_percent,
                        'memory_percent': metrics.memory_percent,
                        'disk_percent': metrics.disk_percent,
                        'network_bytes_sent': metrics.network_io['bytes_sent'],
                        'network_bytes_recv': metrics.network_io['bytes_recv'],
                        'network_packets_sent': metrics.network_io['packets_sent'],
                        'network_packets_recv': metrics.network_io['packets_recv'],
                        'process_count': metrics.process_count,
                        'thread_count': metrics.thread_count
                    }
                    writer.writerow(row)
            
            self.logger.info(f"性能指标已导出到 {file_path}")
        
        except Exception as e:
            self.logger.error(f"导出性能指标到CSV失败: {e}")
    
    def export_metrics_to_json(self, file_path: str, last_n: int = None):
        """
        导出性能指标到JSON文件
        
        Args:
            file_path: JSON文件路径
            last_n: 导出最近n条记录，None表示导出所有记录
        """
        try:
            metrics_list = self.get_metrics_history(last_n)
            
            # 转换为可序列化的格式
            serializable_metrics = []
            for metrics in metrics_list:
                serializable_metrics.append({
                    'timestamp': metrics.timestamp,
                    'datetime': datetime.fromtimestamp(metrics.timestamp).isoformat(),
                    'cpu_percent': metrics.cpu_percent,
                    'memory_percent': metrics.memory_percent,
                    'disk_percent': metrics.disk_percent,
                    'network_io': metrics.network_io,
                    'process_count': metrics.process_count,
                    'thread_count': metrics.thread_count,
                    'custom_metrics': metrics.custom_metrics
                })
            
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(serializable_metrics, jsonfile, ensure_ascii=False, indent=2)
            
            self.logger.info(f"性能指标已导出到 {file_path}")
        
        except Exception as e:
            self.logger.error(f"导出性能指标到JSON失败: {e}")
    
    def get_average_metrics(self, last_n: int = 100) -> Optional[PerformanceMetrics]:
        """
        获取最近n条记录的平均性能指标
        
        Args:
            last_n: 计算最近n条记录的平均值
            
        Returns:
            PerformanceMetrics: 平均性能指标
        """
        try:
            metrics_list = self.get_metrics_history(last_n)
            if not metrics_list:
                return None
            
            avg_metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=sum(m.cpu_percent for m in metrics_list) / len(metrics_list),
                memory_percent=sum(m.memory_percent for m in metrics_list) / len(metrics_list),
                disk_percent=sum(m.disk_percent for m in metrics_list) / len(metrics_list),
                network_io={
                    'bytes_sent': sum(m.network_io['bytes_sent'] for m in metrics_list) / len(metrics_list),
                    'bytes_recv': sum(m.network_io['bytes_recv'] for m in metrics_list) / len(metrics_list),
                    'packets_sent': sum(m.network_io['packets_sent'] for m in metrics_list) / len(metrics_list),
                    'packets_recv': sum(m.network_io['packets_recv'] for m in metrics_list) / len(metrics_list)
                },
                process_count=sum(m.process_count for m in metrics_list) / len(metrics_list),
                thread_count=sum(m.thread_count for m in metrics_list) / len(metrics_list)
            )
            
            return avg_metrics
        
        except Exception as e:
            self.logger.error(f"计算平均性能指标失败: {e}")
            return None
    
    def __del__(self):
        """析构函数，确保监控停止"""
        try:
            if self.is_monitoring:
                self.stop_monitoring()
        except:
            pass  # 忽略析构过程中的错误


if __name__ == "__main__":
    # 测试性能监控器
    monitor = PerformanceMonitor()
    
    # 添加告警回调
    def alert_callback(metric_name: str, current_value: float, threshold: float):
        print(f"告警: {metric_name} 当前值 {current_value} 超过阈值 {threshold}")
    
    monitor.add_alert_callback(alert_callback)
    
    # 开始监控
    monitor.start_monitoring()
    
    print("开始性能监控，持续10秒...")
    time.sleep(10)
    
    # 获取当前指标
    current_metrics = monitor.get_current_metrics()
    print(f"当前CPU使用率: {current_metrics.cpu_percent}%")
    print(f"当前内存使用率: {current_metrics.memory_percent}%")
    
    # 获取平均指标
    avg_metrics = monitor.get_average_metrics(5)
    if avg_metrics:
        print(f"平均CPU使用率: {avg_metrics.cpu_percent}%")
        print(f"平均内存使用率: {avg_metrics.memory_percent}%")
    
    # 停止监控
    monitor.stop_monitoring()
    
    print("性能监控测试完成")