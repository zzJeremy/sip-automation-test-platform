"""
端口资源管理器
用于管理SIP测试中的端口分配与隔离
"""
import threading
import random
import socket
import logging
from typing import Set, Optional
from contextlib import contextmanager


class PortPool:
    """
    端口池管理器，用于分配和回收端口资源
    """
    
    def __init__(self, min_port: int = 8000, max_port: int = 9000):
        """
        初始化端口池
        
        Args:
            min_port: 最小端口号
            max_port: 最大端口号
        """
        self.min_port = min_port
        self.max_port = max_port
        self._available_ports = set(range(min_port, max_port + 1))
        self._allocated_ports = set()
        self._lock = threading.Lock()
        
        # 预定义一些常用SIP端口，不包含在动态分配中
        sip_ports = {5060, 5061, 5080, 5081}
        self._available_ports -= sip_ports
        
        # 在Linux服务器环境中，检查端口可用性
        self._check_system_ports()
    
    def _check_system_ports(self):
        """
        检查系统中已使用的端口并从可用端口池中移除
        """
        try:
            # 尝试连接到每个端口以检查是否被占用
            ports_to_remove = set()
            for port in list(self._available_ports):
                if self._is_port_in_use(port):
                    ports_to_remove.add(port)
            
            self._available_ports -= ports_to_remove
            logging.info(f"从可用端口池中移除已被占用的端口: {ports_to_remove}")
        except Exception as e:
            logging.warning(f"检查系统端口占用情况时出错: {e}")
    
    def _is_port_in_use(self, port: int) -> bool:
        """
        检查指定端口是否正在被使用
        
        Args:
            port: 要检查的端口号
            
        Returns:
            端口是否被占用
        """
        try:
            # 在Linux服务器上更准确地检查端口占用情况
            import subprocess
            result = subprocess.run(['netstat', '-tuln'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # 检查输出中是否有指定端口
                for line in result.stdout.split('\n'):
                    if f':{port} ' in line or f':{port}\n' in line:
                        return True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            # 如果netstat不可用，回退到socket方法
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)  # 设置超时避免长时间阻塞
                    result = sock.connect_ex(('127.0.0.1', port))
                    return result == 0  # 如果能连接成功，说明端口被占用
            except socket.error:
                pass
        
        return False  # 默认认为端口未被使用
        
    def allocate_port(self) -> Optional[int]:
        """
        分配一个可用端口
        
        Returns:
            分配的端口号，如果没有可用端口则返回None
        """
        with self._lock:
            if not self._available_ports:
                return None
            
            port = self._available_ports.pop()
            self._allocated_ports.add(port)
            return port
    
    def allocate_ports(self, count: int) -> Set[int]:
        """
        分配多个端口
        
        Args:
            count: 需要分配的端口数量
            
        Returns:
            分配的端口集合
        """
        with self._lock:
            if len(self._available_ports) < count:
                return set()
            
            ports = set()
            for _ in range(count):
                if self._available_ports:
                    port = self._available_ports.pop()
                    self._allocated_ports.add(port)
                    ports.add(port)
            
            return ports
    
    def release_port(self, port: int) -> bool:
        """
        释放一个端口
        
        Args:
            port: 要释放的端口号
            
        Returns:
            释放是否成功
        """
        with self._lock:
            if port in self._allocated_ports:
                self._allocated_ports.remove(port)
                self._available_ports.add(port)
                return True
            return False
    
    def release_ports(self, ports: Set[int]) -> int:
        """
        释放多个端口
        
        Args:
            ports: 要释放的端口集合
            
        Returns:
            成功释放的端口数量
        """
        with self._lock:
            released_count = 0
            for port in ports:
                if port in self._allocated_ports:
                    self._allocated_ports.remove(port)
                    self._available_ports.add(port)
                    released_count += 1
            return released_count
    
    @contextmanager
    def get_port(self):
        """
        上下文管理器，自动分配和释放端口
        """
        port = self.allocate_port()
        if port is None:
            raise RuntimeError("No available ports")
        
        try:
            yield port
        finally:
            self.release_port(port)
    
    @property
    def available_count(self) -> int:
        """获取可用端口数量"""
        with self._lock:
            return len(self._available_ports)
    
    @property
    def allocated_count(self) -> int:
        """获取已分配端口数量"""
        with self._lock:
            return len(self._allocated_ports)


class SIPResourceManager:
    """
    SIP资源管理器，管理端口、会话等资源
    """
    
    def __init__(self):
        self.port_pool = PortPool()
        self._sessions = {}
        self._session_lock = threading.Lock()
        
    def allocate_rtp_ports(self, count: int = 2) -> Set[int]:
        """
        为RTP流分配端口（通常需要成对分配用于音频/视频）
        
        Args:
            count: 需要分配的端口数量（通常是2的倍数）
            
        Returns:
            分配的端口集合
        """
        return self.port_pool.allocate_ports(count)
    
    def register_session(self, session_id: str, resources: dict) -> bool:
        """
        注册会话资源
        
        Args:
            session_id: 会话ID
            resources: 会话使用的资源
            
        Returns:
            注册是否成功
        """
        with self._session_lock:
            if session_id in self._sessions:
                return False
            self._sessions[session_id] = {
                'resources': resources,
                'allocated_at': self._get_timestamp()
            }
            return True
    
    def release_session(self, session_id: str) -> bool:
        """
        释放会话资源
        
        Args:
            session_id: 会话ID
            
        Returns:
            释放是否成功
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return False
            
            session = self._sessions[session_id]
            resources = session['resources']
            
            # 释放端口资源
            if 'ports' in resources:
                for port in resources['ports']:
                    self.port_pool.release_port(port)
            
            del self._sessions[session_id]
            return True
    
    def _get_timestamp(self) -> float:
        """获取当前时间戳"""
        import time
        return time.time()
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息，如果会话不存在则返回None
        """
        with self._session_lock:
            return self._sessions.get(session_id)
    
    def cleanup_stale_sessions(self, max_age_seconds: int = 3600) -> int:
        """
        清理过期会话
        
        Args:
            max_age_seconds: 会话最大存活时间（秒）
            
        Returns:
            清理的会话数量
        """
        import time
        
        current_time = time.time()
        stale_sessions = []
        
        with self._session_lock:
            for session_id, session_info in self._sessions.items():
                if current_time - session_info['allocated_at'] > max_age_seconds:
                    stale_sessions.append(session_id)
            
            for session_id in stale_sessions:
                self.release_session(session_id)
        
        return len(stale_sessions)


# 全局资源管理器实例
resource_manager = SIPResourceManager()


def get_global_resource_manager() -> SIPResourceManager:
    """
    获取全局资源管理器实例
    
    Returns:
        全局资源管理器实例
    """
    return resource_manager