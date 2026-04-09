"""
分布式执行引擎
支持多节点并行测试执行，提高测试效率
"""

import threading
import queue
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import subprocess
import json


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionTask:
    """执行任务数据类"""
    task_id: str
    task_type: str  # 'pytest', 'robot', 'custom'
    command: str
    parameters: Dict[str, Any]
    priority: int = 0  # 数字越小优先级越高
    timeout: int = 300  # 默认5分钟超时
    created_time: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ExecutionNode:
    """执行节点类"""
    
    def __init__(self, node_id: str, host: str, port: int, max_concurrent: int = 5):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.max_concurrent = max_concurrent
        self.current_tasks = 0
        self.status = "online"  # online, offline, busy
        self.last_heartbeat = time.time()
        self.capabilities = []  # 节点支持的能力
        
    def execute_task(self, task: ExecutionTask) -> Dict[str, Any]:
        """在节点上执行任务"""
        try:
            # 根据任务类型执行不同的命令
            if task.task_type == "pytest":
                return self._execute_pytest_task(task)
            elif task.task_type == "robot":
                return self._execute_robot_task(task)
            else:
                return self._execute_custom_task(task)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "exit_code": -1
            }
    
    def _execute_pytest_task(self, task: ExecutionTask) -> Dict[str, Any]:
        """执行pytest任务"""
        cmd_parts = ["pytest"]
        cmd_parts.append(task.command)  # 测试文件路径
        
        # 添加参数
        for param, value in task.parameters.items():
            if isinstance(value, bool):
                if value:
                    cmd_parts.append(f"--{param}")
            else:
                cmd_parts.append(f"--{param}={value}")
        
        # 执行命令
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=task.timeout
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "exit_code": result.returncode
        }
    
    def _execute_robot_task(self, task: ExecutionTask) -> Dict[str, Any]:
        """执行Robot Framework任务"""
        # 检查robot命令是否存在
        import shutil
        robot_cmd = shutil.which("robot") or shutil.which("robot.bat") or "robot"
        
        cmd_parts = [robot_cmd]
        cmd_parts.append(task.command)  # 测试文件路径
        
        # 添加参数
        for param, value in task.parameters.items():
            if isinstance(value, bool):
                if value:
                    cmd_parts.append(f"--{param}")
            else:
                cmd_parts.append(f"--{param}={value}")
        
        # 执行命令
        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=task.timeout
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "exit_code": result.returncode
            }
        except FileNotFoundError:
            # robot命令未找到，尝试备用执行路径
            return self._execute_robot_task_alternative(task)
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"执行Robot Framework任务时发生错误: {str(e)}",
                "exit_code": -1
            }
    
    def _execute_robot_task_alternative(self, task: ExecutionTask) -> Dict[str, Any]:
        """备用的Robot Framework任务执行方法"""
        try:
            # 尝试使用python -m robot执行
            cmd_parts = ["python", "-m", "robot"]
            cmd_parts.append(task.command)  # 测试文件路径
            
            # 添加参数
            for param, value in task.parameters.items():
                if isinstance(value, bool):
                    if value:
                        cmd_parts.append(f"--{param}")
                else:
                    cmd_parts.append(f"--{param}={value}")
            
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=task.timeout
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "exit_code": result.returncode
            }
        except FileNotFoundError:
            # 如果仍然找不到robot命令，返回错误信息
            return {
                "success": False,
                "output": "",
                "error": "Robot Framework未安装，请先安装robotframework库: pip install robotframework",
                "exit_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"执行Robot Framework任务时发生错误: {str(e)}",
                "exit_code": -1
            }
    
    def _execute_custom_task(self, task: ExecutionTask) -> Dict[str, Any]:
        """执行自定义任务"""
        # 执行自定义命令
        result = subprocess.run(
            task.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=task.timeout
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "exit_code": result.returncode
        }


class DistributedExecutionEngine:
    """分布式执行引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化分布式执行引擎
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.nodes: List[ExecutionNode] = []
        self.task_queue = queue.PriorityQueue()  # 优先级队列
        self.running_tasks: Dict[str, ExecutionTask] = {}
        self.completed_tasks: List[ExecutionTask] = []
        self.failed_tasks: List[ExecutionTask] = []
        self.lock = threading.Lock()
        self.stop_flag = False
        self.worker_threads = []
        self.logger = logging.getLogger(__name__)
        
        # 启动工作线程
        self._start_worker_threads()
    
    def add_execution_node(self, node_config: Dict[str, Any]) -> bool:
        """
        添加执行节点
        
        Args:
            node_config: 节点配置
            
        Returns:
            bool: 添加是否成功
        """
        try:
            node = ExecutionNode(
                node_id=node_config.get('node_id', f"node_{len(self.nodes)}"),
                host=node_config.get('host', 'localhost'),
                port=node_config.get('port', 5000),
                max_concurrent=node_config.get('max_concurrent', 5)
            )
            
            # 检查节点连接性
            if self._ping_node(node):
                self.nodes.append(node)
                self.logger.info(f"成功添加执行节点: {node.node_id}")
                return True
            else:
                self.logger.error(f"无法连接到节点: {node.node_id}")
                return False
        except Exception as e:
            self.logger.error(f"添加执行节点失败: {str(e)}")
            return False
    
    def _ping_node(self, node: ExecutionNode) -> bool:
        """检查节点是否可达"""
        # 简单的ping实现，实际环境中可能需要更复杂的健康检查
        try:
            # 这里可以实现实际的节点连通性检查
            return True
        except Exception:
            return False
    
    def submit_task(self, task: ExecutionTask) -> str:
        """
        提交执行任务
        
        Args:
            task: 执行任务
            
        Returns:
            str: 任务ID
        """
        task.created_time = time.time()
        task.task_id = f"task_{int(time.time())}_{hash(task.command) % 10000}"
        
        # 添加到任务队列
        with self.lock:
            # 优先级队列：(优先级, 任务创建时间, 任务对象)
            self.task_queue.put((task.priority, task.created_time, task))
        
        self.logger.info(f"提交任务: {task.task_id}, 类型: {task.task_type}")
        return task.task_id
    
    def _start_worker_threads(self):
        """启动工作线程"""
        num_workers = self.config.get('worker_threads', 3)
        
        for i in range(num_workers):
            thread = threading.Thread(target=self._worker_loop, args=(i,))
            thread.daemon = True
            thread.start()
            self.worker_threads.append(thread)
    
    def _worker_loop(self, worker_id: int):
        """工作线程主循环"""
        self.logger.info(f"启动工作线程: {worker_id}")
        
        while not self.stop_flag:
            try:
                # 从队列获取任务
                priority, created_time, task = self.task_queue.get(timeout=1)
                
                # 找到可用的执行节点
                node = self._get_available_node()
                if node is None:
                    # 没有可用节点，将任务放回队列
                    time.sleep(1)
                    self.task_queue.put((priority, created_time, task))
                    continue
                
                # 执行任务
                self._execute_task_on_node(task, node)
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"工作线程 {worker_id} 出错: {str(e)}")
    
    def _get_available_node(self) -> Optional[ExecutionNode]:
        """获取可用的执行节点"""
        with self.lock:
            for node in self.nodes:
                if node.status == "online" and node.current_tasks < node.max_concurrent:
                    return node
        return None
    
    def _execute_task_on_node(self, task: ExecutionTask, node: ExecutionNode):
        """在指定节点上执行任务"""
        with self.lock:
            task.status = TaskStatus.RUNNING
            task.start_time = time.time()
            self.running_tasks[task.task_id] = task
            node.current_tasks += 1
        
        self.logger.info(f"在节点 {node.node_id} 上执行任务: {task.task_id}")
        
        try:
            # 执行任务
            result = node.execute_task(task)
            
            # 更新任务状态
            with self.lock:
                task.status = TaskStatus.COMPLETED if result["success"] else TaskStatus.FAILED
                task.result = result
                task.end_time = time.time()
                
                if not result["success"]:
                    task.error = result.get("error", "Unknown error")
                
                del self.running_tasks[task.task_id]
                
                if result["success"]:
                    self.completed_tasks.append(task)
                else:
                    self.failed_tasks.append(task)
                
                node.current_tasks -= 1
                
        except Exception as e:
            # 任务执行出错
            with self.lock:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.end_time = time.time()
                del self.running_tasks[task.task_id]
                self.failed_tasks.append(task)
                node.current_tasks -= 1
    
    def get_task_status(self, task_id: str) -> Optional[ExecutionTask]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            ExecutionTask: 任务对象，如果不存在返回None
        """
        with self.lock:
            if task_id in self.running_tasks:
                return self.running_tasks[task_id]
            
            # 检查已完成的任务
            for task in self.completed_tasks:
                if task.task_id == task_id:
                    return task
            
            # 检查失败的任务
            for task in self.failed_tasks:
                if task.task_id == task_id:
                    return task
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self.lock:
            total_completed = len(self.completed_tasks)
            total_failed = len(self.failed_tasks)
            total_running = len(self.running_tasks)
            total_pending = self.task_queue.qsize()
            
            return {
                "nodes_count": len(self.nodes),
                "active_nodes": sum(1 for n in self.nodes if n.status == "online"),
                "total_completed_tasks": total_completed,
                "total_failed_tasks": total_failed,
                "total_running_tasks": total_running,
                "total_pending_tasks": total_pending,
                "tasks_in_queue": total_pending
            }
    
    def stop(self):
        """停止执行引擎"""
        self.stop_flag = True
        for thread in self.worker_threads:
            thread.join(timeout=2)
        
        self.logger.info("分布式执行引擎已停止")