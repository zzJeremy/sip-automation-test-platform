"""
分布式节点管理器
管理分布式执行引擎中的各个节点
"""

import threading
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import requests
from urllib.parse import urljoin


class NodeStatus(Enum):
    """节点状态枚举"""
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class NodeInfo:
    """节点信息数据类"""
    node_id: str
    host: str
    port: int
    status: NodeStatus
    capabilities: List[str]
    max_concurrent: int
    current_tasks: int
    last_heartbeat: float
    load: float  # 负载百分比


class NodeManager:
    """节点管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化节点管理器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.nodes: Dict[str, NodeInfo] = {}
        self.lock = threading.Lock()
        self.stop_flag = False
        self.heartbeat_thread = None
        self.logger = logging.getLogger(__name__)
        
        # 启动心跳检测线程
        self._start_heartbeat_monitor()
    
    def add_node(self, node_id: str, host: str, port: int, 
                 max_concurrent: int = 5, capabilities: List[str] = None) -> bool:
        """
        添加执行节点
        
        Args:
            node_id: 节点ID
            host: 节点主机
            port: 节点端口
            max_concurrent: 最大并发数
            capabilities: 节点能力列表
            
        Returns:
            bool: 添加是否成功
        """
        if capabilities is None:
            capabilities = ["pytest", "robot", "custom"]
        
        # 检查节点连通性
        if not self._ping_node(host, port):
            self.logger.error(f"无法连接到节点 {node_id} ({host}:{port})")
            return False
        
        with self.lock:
            self.nodes[node_id] = NodeInfo(
                node_id=node_id,
                host=host,
                port=port,
                status=NodeStatus.ONLINE,
                capabilities=capabilities,
                max_concurrent=max_concurrent,
                current_tasks=0,
                last_heartbeat=time.time(),
                load=0.0
            )
        
        self.logger.info(f"成功添加节点: {node_id}")
        return True
    
    def remove_node(self, node_id: str) -> bool:
        """
        移除执行节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            bool: 移除是否成功
        """
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                self.logger.info(f"已移除节点: {node_id}")
                return True
            return False
    
    def _ping_node(self, host: str, port: int) -> bool:
        """检查节点是否可达"""
        try:
            # 尝试连接到节点的健康检查端点
            url = f"http://{host}:{port}/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_available_node(self, required_capabilities: List[str] = None) -> Optional[NodeInfo]:
        """
        获取可用的执行节点
        
        Args:
            required_capabilities: 需要的能力列表
            
        Returns:
            NodeInfo: 可用节点信息，如果没有可用节点返回None
        """
        if required_capabilities is None:
            required_capabilities = []
        
        with self.lock:
            for node in self.nodes.values():
                if (node.status == NodeStatus.ONLINE and 
                    node.current_tasks < node.max_concurrent and
                    all(cap in node.capabilities for cap in required_capabilities)):
                    
                    # 选择负载最低的节点
                    if not hasattr(self, '_best_node') or node.load < self._best_node.load:
                        self._best_node = node
        
        # 返回负载最低的可用节点
        if hasattr(self, '_best_node'):
            return self._best_node
        return None
    
    def update_node_task_count(self, node_id: str, increment: int):
        """
        更新节点任务计数
        
        Args:
            node_id: 节点ID
            increment: 任务数增量（正数为增加，负数为减少）
        """
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.current_tasks = max(0, node.current_tasks + increment)
                node.load = node.current_tasks / node.max_concurrent if node.max_concurrent > 0 else 0
    
    def get_node_stats(self) -> List[Dict[str, Any]]:
        """
        获取所有节点的统计信息
        
        Returns:
            List[Dict]: 节点统计信息列表
        """
        with self.lock:
            stats = []
            for node in self.nodes.values():
                stats.append({
                    'node_id': node.node_id,
                    'host': node.host,
                    'port': node.port,
                    'status': node.status.value,
                    'capabilities': node.capabilities,
                    'max_concurrent': node.max_concurrent,
                    'current_tasks': node.current_tasks,
                    'load': round(node.load * 100, 2),
                    'last_heartbeat': node.last_heartbeat
                })
            return stats
    
    def _start_heartbeat_monitor(self):
        """启动心跳监测线程"""
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """心跳监测主循环"""
        while not self.stop_flag:
            time.sleep(30)  # 每30秒检查一次节点状态
            self._check_node_health()
    
    def _check_node_health(self):
        """检查节点健康状况"""
        with self.lock:
            for node_id, node in list(self.nodes.items()):
                # 检查是否超时
                if time.time() - node.last_heartbeat > 60:  # 60秒超时
                    node.status = NodeStatus.OFFLINE
                    self.logger.warning(f"节点 {node_id} 已离线")
                
                # 重新ping在线节点
                elif node.status != NodeStatus.OFFLINE:
                    if self._ping_node(node.host, node.port):
                        node.status = NodeStatus.ONLINE
                        node.last_heartbeat = time.time()
                    else:
                        node.status = NodeStatus.OFFLINE
                        self.logger.warning(f"节点 {node_id} 无法连接")
    
    def stop(self):
        """停止节点管理器"""
        self.stop_flag = True
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
        
        self.logger.info("节点管理器已停止")