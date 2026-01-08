"""
对话状态管理器模块
管理复杂的SIP对话状态，跟踪Call-ID、CSeq等状态信息，支持re-INVITE等复杂流程
"""
import threading
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid


class DialogState(Enum):
    """对话状态枚举"""
    NULL = "null"  # 初始状态
    EARLY = "early"  # 早期对话（收到1xx响应）
    CONFIRMED = "confirmed"  # 确认对话（收到2xx响应）
    TERMINATED = "terminated"  # 已终止


class CallState(Enum):
    """呼叫状态枚举"""
    IDLE = "idle"
    CALLING = "calling"
    RINGING = "ringing"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class DialogInfo:
    """对话信息数据类"""
    call_id: str
    local_tag: str
    remote_tag: str
    local_uri: str
    remote_uri: str
    route_set: List[str] = field(default_factory=list)
    state: DialogState = DialogState.NULL
    cseq: int = 1
    local_seq: int = 1  # 本地序列号
    remote_seq: int = 0  # 远程序列号
    last_activity: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    expires: int = 3600  # 有效期（秒）
    media_info: Dict[str, Any] = field(default_factory=dict)  # 媒体信息
    user_data: Dict[str, Any] = field(default_factory=dict)  # 用户自定义数据


@dataclass
class CallInfo:
    """呼叫信息数据类"""
    call_id: str
    caller: str
    callee: str
    state: CallState = CallState.IDLE
    start_time: Optional[datetime] = None
    connect_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    dialog: Optional[DialogInfo] = None
    reinvite_count: int = 0  # re-INVITE计数
    sdp_offers: List[Dict[str, Any]] = field(default_factory=list)  # SDP提供列表
    sdp_answers: List[Dict[str, Any]] = field(default_factory=list)  # SDP应答列表
    user_data: Dict[str, Any] = field(default_factory=dict)  # 用户自定义数据


class DialogStateManager:
    """
    对话状态管理器，用于管理SIP对话和呼叫状态
    """
    
    def __init__(self):
        self.dialogs: Dict[str, DialogInfo] = {}  # Call-ID -> DialogInfo
        self.calls: Dict[str, CallInfo] = {}  # Call-ID -> CallInfo
        self.lock = threading.RLock()  # 线程安全锁
        self.cleanup_interval = 300  # 清理间隔（秒）
        self.start_cleanup_thread()
    
    def start_cleanup_thread(self):
        """启动清理线程，定期清理过期对话"""
        def cleanup_loop():
            while True:
                time.sleep(self.cleanup_interval)
                self.cleanup_expired_dialogs()
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def create_dialog(self, call_id: str, local_tag: str, remote_tag: str, 
                     local_uri: str, remote_uri: str, route_set: List[str] = None) -> DialogInfo:
        """
        创建新的对话
        
        Args:
            call_id: 呼叫ID
            local_tag: 本地标签
            remote_tag: 远程标签
            local_uri: 本地URI
            remote_uri: 远程URI
            route_set: 路由集
            
        Returns:
            创建的对话信息对象
        """
        with self.lock:
            if call_id in self.dialogs:
                raise ValueError(f"Dialog with call_id {call_id} already exists")
            
            dialog = DialogInfo(
                call_id=call_id,
                local_tag=local_tag,
                remote_tag=remote_tag,
                local_uri=local_uri,
                remote_uri=remote_uri,
                route_set=route_set or [],
                state=DialogState.NULL
            )
            
            self.dialogs[call_id] = dialog
            return dialog
    
    def get_dialog(self, call_id: str) -> Optional[DialogInfo]:
        """
        获取对话信息
        
        Args:
            call_id: 呼叫ID
            
        Returns:
            对话信息对象，如果不存在则返回None
        """
        with self.lock:
            dialog = self.dialogs.get(call_id)
            if dialog:
                dialog.last_activity = datetime.now()  # 更新最后活动时间
            return dialog
    
    def update_dialog_state(self, call_id: str, state: DialogState) -> bool:
        """
        更新对话状态
        
        Args:
            call_id: 呼叫ID
            state: 新的对话状态
            
        Returns:
            更新是否成功
        """
        with self.lock:
            dialog = self.dialogs.get(call_id)
            if dialog:
                dialog.state = state
                dialog.last_activity = datetime.now()
                return True
            return False
    
    def update_dialog_cseq(self, call_id: str, local_seq: int = None, remote_seq: int = None) -> bool:
        """
        更新对话的CSeq序列号
        
        Args:
            call_id: 呼叫ID
            local_seq: 本地序列号（可选）
            remote_seq: 远程序列号（可选）
            
        Returns:
            更新是否成功
        """
        with self.lock:
            dialog = self.dialogs.get(call_id)
            if dialog:
                if local_seq is not None:
                    dialog.local_seq = local_seq
                if remote_seq is not None:
                    dialog.remote_seq = remote_seq
                dialog.last_activity = datetime.now()
                return True
            return False
    
    def update_dialog_media(self, call_id: str, media_info: Dict[str, Any]) -> bool:
        """
        更新对话的媒体信息
        
        Args:
            call_id: 呼叫ID
            media_info: 媒体信息字典
            
        Returns:
            更新是否成功
        """
        with self.lock:
            dialog = self.dialogs.get(call_id)
            if dialog:
                dialog.media_info.update(media_info)
                dialog.last_activity = datetime.now()
                return True
            return False
    
    def terminate_dialog(self, call_id: str) -> bool:
        """
        终止对话
        
        Args:
            call_id: 呼叫ID
            
        Returns:
            终止是否成功
        """
        with self.lock:
            dialog = self.dialogs.get(call_id)
            if dialog:
                dialog.state = DialogState.TERMINATED
                dialog.last_activity = datetime.now()
                return True
            return False
    
    def delete_dialog(self, call_id: str) -> bool:
        """
        删除对话
        
        Args:
            call_id: 呼叫ID
            
        Returns:
            删除是否成功
        """
        with self.lock:
            if call_id in self.dialogs:
                del self.dialogs[call_id]
                return True
            return False
    
    def create_call(self, call_id: str, caller: str, callee: str) -> CallInfo:
        """
        创建新的呼叫
        
        Args:
            call_id: 呼叫ID
            caller: 主叫方
            callee: 被叫方
            
        Returns:
            创建的呼叫信息对象
        """
        with self.lock:
            if call_id in self.calls:
                raise ValueError(f"Call with call_id {call_id} already exists")
            
            call = CallInfo(
                call_id=call_id,
                caller=caller,
                callee=callee,
                start_time=datetime.now()
            )
            
            self.calls[call_id] = call
            return call
    
    def get_call(self, call_id: str) -> Optional[CallInfo]:
        """
        获取呼叫信息
        
        Args:
            call_id: 呼叫ID
            
        Returns:
            呼叫信息对象，如果不存在则返回None
        """
        with self.lock:
            return self.calls.get(call_id)
    
    def update_call_state(self, call_id: str, state: CallState) -> bool:
        """
        更新呼叫状态
        
        Args:
            call_id: 呼叫ID
            state: 新的呼叫状态
            
        Returns:
            更新是否成功
        """
        with self.lock:
            call = self.calls.get(call_id)
            if call:
                old_state = call.state
                call.state = state
                
                # 根据状态变化更新时间
                if state == CallState.CONNECTED and old_state != CallState.CONNECTED:
                    call.connect_time = datetime.now()
                elif state == CallState.DISCONNECTED:
                    call.end_time = datetime.now()
                
                return True
            return False
    
    def add_sdp_offer(self, call_id: str, sdp: Dict[str, Any]) -> bool:
        """
        添加SDP提供
        
        Args:
            call_id: 呼叫ID
            sdp: SDP信息字典
            
        Returns:
            添加是否成功
        """
        with self.lock:
            call = self.calls.get(call_id)
            if call:
                call.sdp_offers.append(sdp)
                return True
            return False
    
    def add_sdp_answer(self, call_id: str, sdp: Dict[str, Any]) -> bool:
        """
        添加SDP应答
        
        Args:
            call_id: 呼叫ID
            sdp: SDP信息字典
            
        Returns:
            添加是否成功
        """
        with self.lock:
            call = self.calls.get(call_id)
            if call:
                call.sdp_answers.append(sdp)
                return True
            return False
    
    def increment_reinvite_count(self, call_id: str) -> bool:
        """
        增加re-INVITE计数
        
        Args:
            call_id: 呼叫ID
            
        Returns:
            更新是否成功
        """
        with self.lock:
            call = self.calls.get(call_id)
            if call:
                call.reinvite_count += 1
                return True
            return False
    
    def cleanup_expired_dialogs(self):
        """
        清理过期的对话（超过有效期的对话）
        """
        with self.lock:
            now = datetime.now()
            expired_dialogs = []
            
            for call_id, dialog in self.dialogs.items():
                # 检查是否超过最后活动时间加上有效期
                expiry_time = dialog.last_activity + timedelta(seconds=dialog.expires)
                if now > expiry_time:
                    expired_dialogs.append(call_id)
            
            # 删除过期对话
            for call_id in expired_dialogs:
                del self.dialogs[call_id]
            
            if expired_dialogs:
                print(f"Cleaned up {len(expired_dialogs)} expired dialogs")
    
    def get_active_dialogs(self) -> List[DialogInfo]:
        """
        获取所有活跃对话
        
        Returns:
            活跃对话列表
        """
        with self.lock:
            return [dialog for dialog in self.dialogs.values() 
                   if dialog.state != DialogState.TERMINATED]
    
    def get_active_calls(self) -> List[CallInfo]:
        """
        获取所有活跃呼叫
        
        Returns:
            活跃呼叫列表
        """
        with self.lock:
            return [call for call in self.calls.values() 
                   if call.state not in [CallState.DISCONNECTED, CallState.IDLE]]
    
    def get_call_duration(self, call_id: str) -> Optional[timedelta]:
        """
        获取呼叫持续时间
        
        Args:
            call_id: 呼叫ID
            
        Returns:
            呼叫持续时间，如果呼叫不存在则返回None
        """
        with self.lock:
            call = self.calls.get(call_id)
            if call and call.start_time:
                end_time = call.end_time or datetime.now()
                return end_time - call.start_time
            return None
    
    def link_call_to_dialog(self, call_id: str, dialog: DialogInfo) -> bool:
        """
        将呼叫与对话关联
        
        Args:
            call_id: 呼叫ID
            dialog: 对话信息对象
            
        Returns:
            关联是否成功
        """
        with self.lock:
            call = self.calls.get(call_id)
            if call:
                call.dialog = dialog
                return True
            return False


# 使用示例
if __name__ == "__main__":
    # 创建对话状态管理器
    state_manager = DialogStateManager()
    
    # 创建一个对话
    call_id = str(uuid.uuid4())
    dialog = state_manager.create_dialog(
        call_id=call_id,
        local_tag="12345",
        remote_tag="67890",
        local_uri="sip:alice@domain.com",
        remote_uri="sip:bob@domain.com"
    )
    
    print(f"Created dialog: {dialog}")
    
    # 更新对话状态
    state_manager.update_dialog_state(call_id, DialogState.CONFIRMED)
    
    # 创建一个呼叫
    call = state_manager.create_call(call_id, "alice", "bob")
    state_manager.update_call_state(call_id, CallState.CONNECTED)
    
    # 添加SDP信息
    state_manager.add_sdp_offer(call_id, {
        'session_id': '1234567890',
        'media_type': 'audio',
        'port': 8000,
        'codec': 'PCMU'
    })
    
    # 获取活跃对话和呼叫
    active_dialogs = state_manager.get_active_dialogs()
    active_calls = state_manager.get_active_calls()
    
    print(f"Active dialogs: {len(active_dialogs)}")
    print(f"Active calls: {len(active_calls)}")
    
    # 获取呼叫持续时间
    duration = state_manager.get_call_duration(call_id)
    print(f"Call duration: {duration}")