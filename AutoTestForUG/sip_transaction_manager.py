"""
SIP事务管理器和定时器机制
实现RFC3261标准的客户端事务管理和定时器功能
"""

import time
import threading
import socket
from enum import Enum
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
import logging

try:
    from .rfc3261_enhancements import get_timer_value
except ImportError:
    from rfc3261_enhancements import get_timer_value


class TransactionState(Enum):
    """事务状态枚举，符合RFC3261标准"""
    CALLING = "calling"
    PROCEEDING = "proceeding"
    COMPLETED = "completed"
    CONFIRMED = "confirmed"
    TERMINATED = "terminated"
    TRYING = "trying"
    RECEIVED = "received"


class TransactionType(Enum):
    """事务类型"""
    INVITE_CLIENT = "invite-client"
    INVITE_SERVER = "invite-server"
    NON_INVITE_CLIENT = "non-invite-client"
    NON_INVITE_SERVER = "non-invite-server"


@dataclass
class SIPTransaction:
    """SIP事务数据类"""
    tid: str  # 事务ID
    method: str
    request: str
    state: TransactionState
    type: TransactionType
    branch: str
    call_id: str
    cseq: int
    created_at: float
    timer_a: float = None  # INVITE事务定时器
    timer_b: float = None  # INVITE事务超时
    timer_d: float = None  # 非INVITE事务定时器
    timer_e: float = None  # 非INVITE重传定时器
    timer_f: float = None  # 非INVITE超时
    timer_k: float = None  # 非INVITE结束
    response_callback: Optional[Callable] = None
    failure_callback: Optional[Callable] = None
    retransmissions: int = 0


class SIPTransactionManager:
    """
    SIP事务管理器
    实现RFC3261标准的客户端事务管理
    """
    
    def __init__(self):
        self.transactions: Dict[str, SIPTransaction] = {}
        self.lock = threading.Lock()
        self.running = True
        self.timer_thread = threading.Thread(target=self._run_timers, daemon=True)
        self.timer_thread.start()
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def create_client_transaction(self, method: str, request: str, branch: str, 
                                call_id: str, cseq: int, response_callback: Callable = None,
                                failure_callback: Callable = None) -> SIPTransaction:
        """
        创建客户端事务
        
        Args:
            method: SIP方法
            request: 请求消息
            branch: Via头中的branch参数
            call_id: Call-ID
            cseq: CSeq值
            response_callback: 响应回调函数
            failure_callback: 失败回调函数
            
        Returns:
            SIPTransaction: 创建的事务对象
        """
        tid = f"{call_id}_{cseq}_{branch}"
        
        # 确定事务类型
        trans_type = TransactionType.INVITE_CLIENT if method == "INVITE" else TransactionType.NON_INVITE_CLIENT
        
        # 确定初始状态
        initial_state = TransactionState.CALLING if method == "INVITE" else TransactionState.TRYING
        
        transaction = SIPTransaction(
            tid=tid,
            method=method,
            request=request,
            state=initial_state,
            type=trans_type,
            branch=branch,
            call_id=call_id,
            cseq=cseq,
            created_at=time.time(),
            response_callback=response_callback,
            failure_callback=failure_callback
        )
        
        # 设置定时器
        self._setup_timers(transaction)
        
        # 添加到事务列表
        with self.lock:
            self.transactions[tid] = transaction
        
        self.logger.info(f"创建客户端事务: {tid}, 方法: {method}")
        return transaction
    
    def _setup_timers(self, transaction: SIPTransaction):
        """设置事务相关的定时器"""
        current_time = time.time()
        
        if transaction.type == TransactionType.INVITE_CLIENT:
            # INVITE客户端事务定时器
            transaction.timer_a = current_time + get_timer_value('T1') / 1000.0  # 初始重传定时器
            transaction.timer_b = current_time + get_timer_value('TIMER_B') / 1000.0  # 事务超时
        else:
            # 非INVITE客户端事务定时器
            transaction.timer_e = current_time + get_timer_value('T1') / 1000.0  # 重传定时器
            transaction.timer_f = current_time + get_timer_value('TIMER_F') / 1000.0  # 事务超时
            transaction.timer_k = current_time + get_timer_value('TIMER_K') / 1000.0  # 结束定时器
    
    def send_request(self, transaction: SIPTransaction, sock: socket.socket, 
                     server_addr: tuple) -> bool:
        """
        发送请求并处理事务状态转换
        
        Args:
            transaction: 事务对象
            sock: UDP套接字
            server_addr: 服务器地址
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 发送请求
            sock.sendto(transaction.request.encode('utf-8'), server_addr)
            
            # 更新事务状态
            if transaction.type == TransactionType.INVITE_CLIENT:
                if transaction.state == TransactionState.CALLING:
                    transaction.state = TransactionState.CALLING
            else:
                if transaction.state == TransactionState.TRYING:
                    transaction.state = TransactionState.TRYING
            
            self.logger.debug(f"发送请求，事务ID: {transaction.tid}, 状态: {transaction.state.value}")
            return True
        except Exception as e:
            self.logger.error(f"发送请求失败，事务ID: {transaction.tid}, 错误: {str(e)}")
            self._handle_transaction_failure(transaction, str(e))
            return False
    
    def receive_response(self, response: str, via_branch: str) -> bool:
        """
        接收响应并处理事务状态转换
        
        Args:
            response: 响应消息
            via_branch: Via头中的branch参数，用于匹配事务
            
        Returns:
            bool: 是否找到匹配的事务
        """
        # 查找匹配的事务
        matched_tid = None
        with self.lock:
            for tid, transaction in self.transactions.items():
                if transaction.branch == via_branch:
                    matched_tid = tid
                    break
        
        if matched_tid is None:
            self.logger.warning(f"未找到匹配的事务，branch: {via_branch}")
            return False
        
        transaction = self.transactions[matched_tid]
        
        # 解析响应状态码
        lines = response.split('\r\n')
        if lines and ' ' in lines[0]:
            status_parts = lines[0].split(' ', 2)
            if len(status_parts) >= 2:
                try:
                    status_code = int(status_parts[1])
                    
                    # 根据状态码更新事务状态
                    if transaction.type == TransactionType.INVITE_CLIENT:
                        if 100 <= status_code <= 199:
                            transaction.state = TransactionState.PROCEEDING
                        elif 200 <= status_code <= 299:
                            transaction.state = TransactionState.TERMINATED
                            # 调用成功回调
                            if transaction.response_callback:
                                transaction.response_callback(response)
                        elif 300 <= status_code <= 699:
                            transaction.state = TransactionState.COMPLETED
                            # 调用失败回调
                            if transaction.failure_callback:
                                transaction.failure_callback(response)
                    else:  # 非INVITE事务
                        if 100 <= status_code <= 199:
                            transaction.state = TransactionState.PROCEEDING
                        elif status_code >= 200:
                            transaction.state = TransactionState.TERMINATED
                            # 调用响应回调
                            if transaction.response_callback:
                                transaction.response_callback(response)
                    
                    self.logger.info(f"事务 {transaction.tid} 状态更新为: {transaction.state.value}, 响应码: {status_code}")
                    return True
                except ValueError:
                    self.logger.error(f"无法解析响应状态码: {status_parts[1]}")
                    return False
        
        return False
    
    def _handle_transaction_failure(self, transaction: SIPTransaction, error: str):
        """处理事务失败"""
        transaction.state = TransactionState.TERMINATED
        
        # 调用失败回调
        if transaction.failure_callback:
            transaction.failure_callback(error)
        
        self.logger.error(f"事务失败，ID: {transaction.tid}, 错误: {error}")
    
    def _run_timers(self):
        """定时器运行线程"""
        while self.running:
            current_time = time.time()
            
            with self.lock:
                # 检查所有事务的定时器
                for tid, transaction in list(self.transactions.items()):
                    try:
                        self._check_transaction_timers(transaction, current_time)
                    except Exception as e:
                        self.logger.error(f"检查事务定时器时出错: {str(e)}")
            
            # 每100ms检查一次定时器
            time.sleep(0.1)
    
    def _check_transaction_timers(self, transaction: SIPTransaction, current_time: float):
        """检查单个事务的定时器"""
        if transaction.state == TransactionState.TERMINATED:
            # 清理已终止的事务
            if current_time - transaction.created_at > 5:  # 5秒后清理
                del self.transactions[transaction.tid]
                self.logger.debug(f"清理已终止的事务: {transaction.tid}")
            return
        
        if transaction.type == TransactionType.INVITE_CLIENT:
            # INVITE客户端事务定时器检查
            if transaction.state == TransactionState.CALLING:
                if current_time >= transaction.timer_a:
                    # Timer A expired - 重传请求
                    self._resend_request(transaction)
                    # 指数退避
                    transaction.retransmissions += 1
                    transaction.timer_a = current_time + (get_timer_value('T1') * (2 ** transaction.retransmissions)) / 1000.0
                    self.logger.debug(f"INVITE事务重传，事务ID: {transaction.tid}")
                
                if current_time >= transaction.timer_b:
                    # Timer B expired - 事务超时
                    self._handle_transaction_failure(transaction, "Timer B expired")
        
        else:
            # 非INVITE客户端事务定时器检查
            if transaction.state in [TransactionState.TRYING, TransactionState.PROCEEDING]:
                if transaction.timer_e and current_time >= transaction.timer_e:
                    # Timer E expired - 重传请求
                    self._resend_request(transaction)
                    # 指数退避，但不超过T2
                    transaction.retransmissions += 1
                    next_timeout = min(get_timer_value('T2'), get_timer_value('T1') * (2 ** transaction.retransmissions))
                    transaction.timer_e = current_time + next_timeout / 1000.0
                    self.logger.debug(f"非INVITE事务重传，事务ID: {transaction.tid}")
                
                if current_time >= transaction.timer_f:
                    # Timer F expired - 事务超时
                    self._handle_transaction_failure(transaction, "Timer F expired")
    
    def _resend_request(self, transaction: SIPTransaction):
        """重传请求"""
        # 这里只是标记需要重传，实际重传应在外部完成
        self.logger.debug(f"准备重传请求，事务ID: {transaction.tid}")
    
    def cancel_transaction(self, tid: str):
        """取消指定事务"""
        with self.lock:
            if tid in self.transactions:
                transaction = self.transactions[tid]
                transaction.state = TransactionState.TERMINATED
                self.logger.info(f"取消事务: {tid}")
    
    def shutdown(self):
        """关闭事务管理器"""
        self.running = False
        with self.lock:
            self.transactions.clear()


# 定义RFC3261定时器类
class SIPRFC3261Timers:
    """RFC3261定时器管理类"""
    
    # RFC3261标准定时器值（毫秒）
    DEFAULT_VALUES = {
        'T1': 500,      # 默认往返时间
        'T2': 4000,     # 最大重传间隔
        'T4': 5000,     # 最大传输时间
        'TIMER_B': 64 * 500,  # INVITE事务超时
        'TIMER_F': 64 * 500,  # 非INVITE事务超时
        'TIMER_H': 64 * 500,  # ACK等待INVITE响应
        'TIMER_I': 64 * 500,  # 非INVITE响应确认
        'TIMER_J': 64 * 500,  # 非INVITE请求重传
        'TIMER_K': 5000,      # UDP非INVITE事务结束
    }
    
    def __init__(self):
        self.timers = self.DEFAULT_VALUES.copy()
    
    def get_timer_value(self, timer_name: str) -> int:
        """获取定时器值"""
        return self.timers.get(timer_name.upper(), self.DEFAULT_VALUES[timer_name.upper()])
    
    def set_timer_value(self, timer_name: str, value: int):
        """设置定时器值"""
        self.timers[timer_name.upper()] = value
    
    def get_all_timers(self) -> Dict[str, int]:
        """获取所有定时器值"""
        return self.timers.copy()


# 事务管理器的全局实例
transaction_manager = SIPTransactionManager()