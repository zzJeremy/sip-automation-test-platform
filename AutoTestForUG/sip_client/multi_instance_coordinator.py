"""
多实例协调器模块
协调多个SIP客户端实例的状态，支持跨实例断言和状态共享
"""
import threading
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import queue
from enum import Enum


class InstanceType(Enum):
    """实例类型枚举"""
    SIPp = "sipp"
    PJSIP = "pjsip"
    SOCKET = "socket"
    FUZZ = "fuzz"


@dataclass
class InstanceInfo:
    """实例信息数据类"""
    instance_id: str
    instance_type: InstanceType
    status: str = "idle"  # idle, running, paused, error
    last_activity: datetime = field(default_factory=datetime.now)
    capabilities: List[str] = field(default_factory=list)
    address: str = ""  # 实例地址或标识
    user_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """事件数据类"""
    event_id: str
    source_instance: str
    event_type: str  # call_started, call_ended, message_received, etc.
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    target_instances: List[str] = field(default_factory=list)  # 目标实例列表


@dataclass
class CrossInstanceAssertion:
    """跨实例断言数据类"""
    assertion_id: str
    source_instance: str
    target_instance: str
    condition: str  # 条件表达式
    expected_result: Any
    actual_result: Any = None
    status: str = "pending"  # pending, passed, failed, error
    timestamp: datetime = field(default_factory=datetime.now)
    timeout: int = 30  # 超时时间（秒）


class MultiInstanceCoordinator:
    """
    多实例协调器，用于协调多个SIP客户端实例的状态
    支持跨实例断言和状态共享
    """
    
    def __init__(self):
        self.instances: Dict[str, InstanceInfo] = {}
        self.events: List[Event] = []
        self.assertions: Dict[str, CrossInstanceAssertion] = {}
        self.event_queue = queue.Queue()
        self.lock = threading.RLock()
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.state_store: Dict[str, Any] = {}  # 全局状态存储
        self.start_event_processor()
    
    def start_event_processor(self):
        """启动事件处理器线程"""
        def process_events():
            while True:
                try:
                    event = self.event_queue.get(timeout=1)
                    self._handle_event(event)
                    self.event_queue.task_done()
                except queue.Empty:
                    continue
        
        event_thread = threading.Thread(target=process_events, daemon=True)
        event_thread.start()
    
    def register_instance(self, instance_id: str, instance_type: InstanceType, 
                         capabilities: List[str] = None, address: str = "") -> bool:
        """
        注册新的实例
        
        Args:
            instance_id: 实例ID
            instance_type: 实例类型
            capabilities: 实例能力列表
            address: 实例地址或标识
            
        Returns:
            注册是否成功
        """
        with self.lock:
            if instance_id in self.instances:
                return False
            
            instance = InstanceInfo(
                instance_id=instance_id,
                instance_type=instance_type,
                capabilities=capabilities or [],
                address=address
            )
            
            self.instances[instance_id] = instance
            return True
    
    def unregister_instance(self, instance_id: str) -> bool:
        """
        注销实例
        
        Args:
            instance_id: 实例ID
            
        Returns:
            注销是否成功
        """
        with self.lock:
            if instance_id in self.instances:
                del self.instances[instance_id]
                return True
            return False
    
    def update_instance_status(self, instance_id: str, status: str) -> bool:
        """
        更新实例状态
        
        Args:
            instance_id: 实例ID
            status: 新状态
            
        Returns:
            更新是否成功
        """
        with self.lock:
            instance = self.instances.get(instance_id)
            if instance:
                instance.status = status
                instance.last_activity = datetime.now()
                return True
            return False
    
    def get_instance(self, instance_id: str) -> Optional[InstanceInfo]:
        """
        获取实例信息
        
        Args:
            instance_id: 实例ID
            
        Returns:
            实例信息，如果不存在则返回None
        """
        with self.lock:
            return self.instances.get(instance_id)
    
    def get_instances_by_type(self, instance_type: InstanceType) -> List[InstanceInfo]:
        """
        根据类型获取实例列表
        
        Args:
            instance_type: 实例类型
            
        Returns:
            匹配类型的实例列表
        """
        with self.lock:
            return [instance for instance in self.instances.values() 
                   if instance.instance_type == instance_type]
    
    def get_all_instances(self) -> List[InstanceInfo]:
        """获取所有实例"""
        with self.lock:
            return list(self.instances.values())
    
    def publish_event(self, source_instance: str, event_type: str, 
                     data: Dict[str, Any] = None, target_instances: List[str] = None) -> str:
        """
        发布事件
        
        Args:
            source_instance: 源实例ID
            event_type: 事件类型
            data: 事件数据
            target_instances: 目标实例列表
            
        Returns:
            事件ID
        """
        event_id = str(uuid.uuid4())
        
        event = Event(
            event_id=event_id,
            source_instance=source_instance,
            event_type=event_type,
            data=data or {},
            target_instances=target_instances or []
        )
        
        # 添加到事件队列进行异步处理
        self.event_queue.put(event)
        
        # 同时添加到事件列表
        with self.lock:
            self.events.append(event)
        
        return event_id
    
    def _handle_event(self, event: Event):
        """处理事件"""
        # 更新全局状态存储
        with self.lock:
            self.state_store[f"event_{event.event_id}"] = event
            
            # 如果事件包含状态更新，更新相应状态
            if 'call_id' in event.data and 'state' in event.data:
                call_id = event.data['call_id']
                call_state = event.data['state']
                self.state_store[f"call_{call_id}_state"] = call_state
            
            # 如果事件包含用户信息，更新相应信息
            if 'user' in event.data and 'status' in event.data:
                user = event.data['user']
                status = event.data['status']
                self.state_store[f"user_{user}_status"] = status
        
        # 调用注册的事件处理器
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Error in event handler for {event.event_type}: {e}")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def create_cross_instance_assertion(self, source_instance: str, target_instance: str,
                                      condition: str, expected_result: Any) -> str:
        """
        创建跨实例断言
        
        Args:
            source_instance: 源实例ID
            target_instance: 目标实例ID
            condition: 条件表达式
            expected_result: 期望结果
            
        Returns:
            断言ID
        """
        assertion_id = str(uuid.uuid4())
        
        assertion = CrossInstanceAssertion(
            assertion_id=assertion_id,
            source_instance=source_instance,
            target_instance=target_instance,
            condition=condition,
            expected_result=expected_result
        )
        
        with self.lock:
            self.assertions[assertion_id] = assertion
        
        return assertion_id
    
    def evaluate_assertion(self, assertion_id: str) -> bool:
        """
        评估断言
        
        Args:
            assertion_id: 断言ID
            
        Returns:
            断言是否通过
        """
        with self.lock:
            assertion = self.assertions.get(assertion_id)
            if not assertion:
                return False
            
            # 根据条件评估断言
            try:
                result = self._evaluate_condition(assertion.condition, assertion.source_instance, assertion.target_instance)
                assertion.actual_result = result
                
                if result == assertion.expected_result:
                    assertion.status = "passed"
                    return True
                else:
                    assertion.status = "failed"
                    return False
            except Exception as e:
                assertion.status = "error"
                assertion.actual_result = str(e)
                return False
    
    def _evaluate_condition(self, condition: str, source_instance: str, target_instance: str) -> Any:
        """
        评估条件表达式
        
        Args:
            condition: 条件表达式
            source_instance: 源实例ID
            target_instance: 目标实例ID
            
        Returns:
            评估结果
        """
        # 简化的条件评估，实际实现可能需要更复杂的表达式解析
        if condition.startswith("received_call_from"):
            # 格式: received_call_from(source_user, target_user)
            import re
            match = re.search(r"received_call_from\(([^,]+),\s*([^)]+)\)", condition)
            if match:
                source_user = match.group(1).strip().strip('"\'')
                target_user = match.group(2).strip().strip('"\'')
                
                # 检查目标实例是否收到了来自源实例的呼叫
                # 这里需要查询全局状态存储
                with self.lock:
                    # 检查是否有相应的事件
                    for event in self.events:
                        if (event.event_type == "call_received" and 
                            event.source_instance == source_instance and
                            event.data.get("target_user") == target_user):
                            return True
                return False
        
        elif condition.startswith("message_received"):
            # 格式: message_received(from_user, to_user, message_type)
            import re
            match = re.search(r"message_received\(([^,]+),\s*([^,]+),\s*([^)]+)\)", condition)
            if match:
                from_user = match.group(1).strip().strip('"\'')
                to_user = match.group(2).strip().strip('"\'')
                msg_type = match.group(3).strip().strip('"\'')
                
                with self.lock:
                    # 检查是否有相应的消息接收事件
                    for event in self.events:
                        if (event.event_type == "message_received" and 
                            event.source_instance == source_instance and
                            event.data.get("from_user") == from_user and
                            event.data.get("to_user") == to_user and
                            event.data.get("message_type") == msg_type):
                            return True
                return False
        
        elif condition.startswith("user_status_is"):
            # 格式: user_status_is(user, expected_status)
            import re
            match = re.search(r"user_status_is\(([^,]+),\s*([^)]+)\)", condition)
            if match:
                user = match.group(1).strip().strip('"\'')
                expected_status = match.group(2).strip().strip('"\'')
                
                with self.lock:
                    actual_status = self.state_store.get(f"user_{user}_status")
                    return actual_status == expected_status
        
        # 默认返回False（条件不满足）
        return False
    
    def wait_for_assertion(self, assertion_id: str, timeout: int = 30) -> bool:
        """
        等待断言完成
        
        Args:
            assertion_id: 断言ID
            timeout: 超时时间（秒）
            
        Returns:
            断言是否通过
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self.lock:
                assertion = self.assertions.get(assertion_id)
                if not assertion:
                    return False
                
                if assertion.status in ["passed", "failed", "error"]:
                    return assertion.status == "passed"
            
            time.sleep(0.1)  # 等待0.1秒后重试
        
        # 超时，将断言标记为失败
        with self.lock:
            assertion = self.assertions.get(assertion_id)
            if assertion:
                assertion.status = "failed"
                assertion.actual_result = "Timeout"
        
        return False
    
    def get_shared_state(self, key: str) -> Optional[Any]:
        """
        获取共享状态
        
        Args:
            key: 状态键
            
        Returns:
            状态值，如果不存在则返回None
        """
        with self.lock:
            return self.state_store.get(key)
    
    def set_shared_state(self, key: str, value: Any):
        """
        设置共享状态
        
        Args:
            key: 状态键
            value: 状态值
        """
        with self.lock:
            self.state_store[key] = value
    
    def broadcast_message(self, message_type: str, data: Dict[str, Any], 
                        target_instances: List[str] = None) -> List[str]:
        """
        广播消息给多个实例
        
        Args:
            message_type: 消息类型
            data: 消息数据
            target_instances: 目标实例列表（如果为None，则发送给所有实例）
            
        Returns:
            成功发送的实例ID列表
        """
        if target_instances is None:
            target_instances = list(self.instances.keys())
        
        successful_instances = []
        
        for instance_id in target_instances:
            if instance_id in self.instances:
                event_id = self.publish_event(
                    source_instance="coordinator",
                    event_type=message_type,
                    data=data,
                    target_instances=[instance_id]
                )
                successful_instances.append(instance_id)
        
        return successful_instances
    
    def sync_instances(self, instance_ids: List[str], sync_point: str) -> bool:
        """
        同步多个实例到指定同步点
        
        Args:
            instance_ids: 要同步的实例ID列表
            sync_point: 同步点标识
            
        Returns:
            同步是否成功
        """
        # 发布同步事件
        sync_data = {
            "sync_point": sync_point,
            "timestamp": datetime.now().isoformat()
        }
        
        event_id = self.publish_event(
            source_instance="coordinator",
            event_type="sync_point",
            data=sync_data,
            target_instances=instance_ids
        )
        
        # 等待所有实例确认同步
        start_time = time.time()
        timeout = 10  # 10秒超时
        
        while time.time() - start_time < timeout:
            all_synced = True
            with self.lock:
                # 检查是否所有实例都已确认同步点
                for instance_id in instance_ids:
                    sync_key = f"instance_{instance_id}_sync_{sync_point}"
                    if self.state_store.get(sync_key) != "confirmed":
                        all_synced = False
                        break
            
            if all_synced:
                return True
            
            time.sleep(0.1)
        
        return False
    
    def get_event_history(self, instance_id: str = None, event_type: str = None, 
                         limit: int = 100) -> List[Event]:
        """
        获取事件历史
        
        Args:
            instance_id: 实例ID（可选，如果指定则只返回该实例的事件）
            event_type: 事件类型（可选，如果指定则只返回该类型的事件）
            limit: 限制返回的事件数量
            
        Returns:
            事件列表
        """
        with self.lock:
            events = self.events.copy()
            
            if instance_id:
                events = [e for e in events if e.source_instance == instance_id]
            
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # 按时间倒序排列并限制数量
            events.sort(key=lambda x: x.timestamp, reverse=True)
            return events[:limit]


# 使用示例
if __name__ == "__main__":
    coordinator = MultiInstanceCoordinator()
    
    # 注册实例
    coordinator.register_instance("instance_1", InstanceType.PJSIP, ["call", "register"])
    coordinator.register_instance("instance_2", InstanceType.SIPp, ["call", "load_test"])
    coordinator.register_instance("instance_3", InstanceType.SOCKET, ["fuzz", "security"])
    
    print("Registered instances:")
    for instance in coordinator.get_all_instances():
        print(f"  {instance.instance_id}: {instance.instance_type.value}")
    
    # 发布事件
    event_id = coordinator.publish_event(
        "instance_1",
        "call_started",
        {"call_id": "12345", "from_user": "alice", "to_user": "bob"}
    )
    
    print(f"Published event: {event_id}")
    
    # 创建跨实例断言
    assertion_id = coordinator.create_cross_instance_assertion(
        "instance_1",
        "instance_2",
        'received_call_from("alice", "bob")',
        True
    )
    
    print(f"Created assertion: {assertion_id}")
    
    # 模拟目标实例收到呼叫的事件
    coordinator.publish_event(
        "instance_2",
        "call_received",
        {"call_id": "12345", "from_user": "alice", "target_user": "bob"}
    )
    
    # 等待并评估断言
    result = coordinator.wait_for_assertion(assertion_id, timeout=5)
    print(f"Assertion result: {result}")
    
    # 获取事件历史
    events = coordinator.get_event_history(limit=10)
    print(f"Recent events: {len(events)}")
    
    # 获取共享状态
    coordinator.set_shared_state("test_key", "test_value")
    value = coordinator.get_shared_state("test_key")
    print(f"Shared state value: {value}")