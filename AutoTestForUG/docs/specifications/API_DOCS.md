# SIP客户端API文档和使用示例

## 1. EnhancedSIPCallTester API

### 1.1 类初始化

```python
from enhanced_sip_call_tester import EnhancedSIPCallTester

# 创建增强型SIP客户端实例
client = EnhancedSIPCallTester(
    server_host="127.0.0.1",    # SIP服务器地址
    server_port=5060,           # SIP服务器端口
    local_host="127.0.0.1",     # 本地地址
    local_port=5080             # 本地端口
)
```

### 1.2 注册功能

```python
# 执行SIP注册
success = client.register(
    server_ip="sip.example.com",    # 服务器IP
    server_port=5060,               # 服务器端口
    username="user123",             # 用户名
    password="password123",         # 密码
    realm="example.com",            # 认证域
    expires=3600                    # 过期时间（秒）
)

if success:
    print("注册成功")
else:
    print("注册失败")
```

### 1.3 呼叫功能

```python
# 发起呼叫
call_result = client.invite(
    destination_uri="sip:callee@example.com",  # 被叫URI
    sdp_offer="v=0\r\n..."                   # SDP协商信息
)

if call_result:
    print("呼叫建立成功")
    
    # 发送确认
    client.ack(
        call_id="call123",
        cseq=1,
        from_uri="sip:caller@example.com",
        to_uri="sip:callee@example.com",
        from_tag="from_tag",
        to_tag="to_tag"
    )
    
    # 结束呼叫
    client.bye(
        call_id="call123",
        cseq=2,
        from_uri="sip:caller@example.com",
        to_uri="sip:callee@example.com",
        from_tag="from_tag",
        to_tag="to_tag"
    )
```

### 1.4 扩展SIP方法

#### PRACK消息
```python
# 发送PRACK消息（可靠临时响应确认）
prack_success = client.prack(
    call_id="call123",
    cseq=1,
    rack_cseq=1,
    rack_method="INVITE", 
    from_uri="sip:caller@example.com",
    to_uri="sip:callee@example.com",
    from_tag="from_tag",
    to_tag="to_tag"
)
```

#### UPDATE消息
```python
# 发送UPDATE消息（更新会话参数）
update_success = client.update(
    call_id="call123",
    cseq=2,
    from_uri="sip:caller@example.com",
    to_uri="sip:callee@example.com",
    from_tag="from_tag",
    to_tag="to_tag",
    sdp_content="v=0\r\n..."  # 新的SDP信息
)
```

#### INFO消息
```python
# 发送INFO消息（传递会话相关信息）
info_success = client.info(
    call_id="call123",
    cseq=3,
    from_uri="sip:caller@example.com",
    to_uri="sip:callee@example.com",
    from_tag="from_tag",
    to_tag="to_tag",
    content="application/dtmf-relay",  # DTMF信号
    content_type="application/dtmf-relay"
)
```

#### REFER消息
```python
# 发送REFER消息（呼叫转移）
refer_success = client.refer(
    call_id="call123",
    cseq=4,
    from_uri="sip:caller@example.com",
    to_uri="sip:callee@example.com",
    from_tag="from_tag",
    to_tag="to_tag",
    refer_to="sip:new_destination@example.com",  # 转移目标
    referred_by="sip:referrer@example.com"       # 转移发起方
)
```

#### SUBSCRIBE消息
```python
# 发送SUBSCRIBE消息（订阅事件）
subscribe_success = client.subscribe(
    call_id="call123",
    cseq=5,
    from_uri="sip:subscriber@example.com",
    to_uri="sip:event_source@example.com",
    from_tag="from_tag",
    to_tag="to_tag",
    event="presence",     # 事件类型
    expires=3600          # 订阅有效期
)
```

## 2. SIPTransactionManager API

### 2.1 事务管理器初始化

```python
from sip_transaction_manager import SIPTransactionManager, TransactionState, TransactionType

# 创建事务管理器
tm = SIPTransactionManager()
```

### 2.2 创建客户端事务

```python
# 创建INVITE客户端事务
invite_transaction = tm.create_client_transaction(
    method="INVITE",
    request="INVITE sip:user@domain.com SIP/2.0...",
    branch="z9hG4bK123456",
    call_id="call123",
    cseq=1,
    response_callback=lambda response: print(f"收到响应: {response}"),
    failure_callback=lambda error: print(f"事务失败: {error}")
)

# 创建REGISTER客户端事务
register_transaction = tm.create_client_transaction(
    method="REGISTER",
    request="REGISTER sip:domain.com SIP/2.0...",
    branch="z9hG4bK789012",
    call_id="reg123",
    cseq=1
)
```

### 2.3 事务状态查询

```python
# 查询事务状态
print(f"事务状态: {invite_transaction.state}")
print(f"事务类型: {invite_transaction.type}")

# 检查是否为INVITE事务
if invite_transaction.type == TransactionType.INVITE_CLIENT:
    print("这是一个INVITE客户端事务")
```

### 2.4 事务清理

```python
# 关闭事务管理器（清理所有资源）
tm.shutdown()
```

## 3. NAT穿越功能

### 3.1 STUN客户端使用

```python
from nat_traversal import STUNClient

# 创建STUN客户端
stun_client = STUNClient(
    stun_server="stun.l.google.com",  # STUN服务器
    stun_port=19302                   # STUN端口
)

# 获取公网映射地址
mapped_address = stun_client.get_mapped_address()
if mapped_address:
    public_ip, public_port = mapped_address
    print(f"公网地址: {public_ip}:{public_port}")
else:
    print("无法获取公网地址")
```

### 3.2 NAT兼容消息创建

```python
from nat_traversal import create_nat_compatible_sip_message

# 创建NAT兼容的SIP消息
original_message = "INVITE sip:user@domain.com SIP/2.0..."
nat_compatible_message = create_nat_compatible_sip_message(
    original_message=original_message,
    public_ip="192.168.1.100",    # 公网IP
    public_port=5080              # 公网端口
)
```

## 4. RFC3261增强功能

### 4.1 RFC3261增强器使用

```python
from rfc3261_enhancements import RFC3261Enhancements

enhancer = RFC3261Enhancements()

# 生成安全随机字符串
random_string = enhancer.generate_secure_random_string(16)
print(f"随机字符串: {random_string}")

# 计算摘要认证
auth_response = enhancer.calculate_hmac_auth(
    username="test_user",
    password="test_password",
    realm="test_realm",
    nonce="test_nonce",
    method="REGISTER",
    uri="sip:test@example.com"
)
print(f"认证响应: {auth_response}")

# 验证对话标识符
is_valid = enhancer.validate_dialog_identifier(
    from_tag="from123",
    to_tag="to456", 
    call_id="call789"
)
print(f"对话有效: {is_valid}")
```

## 5. 完整使用示例

### 5.1 基本呼叫流程示例

```python
from enhanced_sip_call_tester import EnhancedSIPCallTester

def make_basic_call():
    # 创建SIP客户端
    client = EnhancedSIPCallTester(
        server_host="127.0.0.1",
        server_port=5060,
        local_host="127.0.0.1", 
        local_port=5080
    )
    
    try:
        # 发起呼叫
        print("发起呼叫...")
        call_success = client.invite(
            destination_uri="sip:callee@127.0.0.1",
            sdp_offer="v=0\r\no=- 123456 1 IN IP4 127.0.0.1\r\n..."
        )
        
        if call_success:
            print("呼叫成功建立")
            
            # 发送确认
            client.ack(
                call_id="test_call_123",
                cseq=1,
                from_uri="sip:caller@127.0.0.1",
                to_uri="sip:callee@127.0.0.1",
                from_tag="caller_tag",
                to_tag="callee_tag"
            )
            
            print("发送ACK确认")
            
            # 等待一段时间后结束呼叫
            import time
            time.sleep(2)
            
            # 结束呼叫
            bye_success = client.bye(
                call_id="test_call_123",
                cseq=2,
                from_uri="sip:caller@127.0.0.1",
                to_uri="sip:callee@127.0.0.1",
                from_tag="caller_tag",
                to_tag="callee_tag"
            )
            
            if bye_success:
                print("呼叫已结束")
            else:
                print("结束呼叫失败")
        else:
            print("呼叫建立失败")
            
    except Exception as e:
        print(f"呼叫过程出现错误: {e}")
    finally:
        print("呼叫流程完成")

# 执行基本呼叫
make_basic_call()
```

### 5.2 扩展功能使用示例

```python
def use_extended_features():
    client = EnhancedSIPCallTester(
        server_host="127.0.0.1",
        server_port=5060,
        local_host="127.0.0.1",
        local_port=5080
    )
    
    # 使用PRACK确认临时响应
    prack_result = client.prack(
        call_id="extended_call_123",
        cseq=1,
        rack_cseq=1,
        rack_method="INVITE",
        from_uri="sip:caller@127.0.0.1",
        to_uri="sip:callee@127.0.0.1",
        from_tag="from123",
        to_tag="to456"
    )
    
    if prack_result:
        print("PRACK发送成功")
    
    # 使用UPDATE更新会话
    update_result = client.update(
        call_id="extended_call_123",
        cseq=2,
        from_uri="sip:caller@127.0.0.1",
        to_uri="sip:callee@127.0.0.1",
        from_tag="from123",
        to_tag="to456",
        sdp_content="v=0\r\no=- 123457 1 IN IP4 127.0.0.1\r\n..."  # 更新后的SDP
    )
    
    if update_result:
        print("UPDATE发送成功")
    
    # 使用INFO传递DTMF
    info_result = client.info(
        call_id="extended_call_123",
        cseq=3,
        from_uri="sip:caller@127.0.0.1",
        to_uri="sip:callee@127.0.0.1",
        from_tag="from123",
        to_tag="to456",
        content="Signal=1",
        content_type="application/dtmf-relay"
    )
    
    if info_result:
        print("INFO(DTMF)发送成功")

# 使用扩展功能
use_extended_features()
```

## 6. 错误处理最佳实践

```python
def robust_sip_operation():
    client = EnhancedSIPCallTester(
        server_host="127.0.0.1",
        server_port=5060,
        local_host="127.0.0.1",
        local_port=5080
    )
    
    try:
        # 执行SIP操作
        result = client.invite(
            destination_uri="sip:destination@127.0.0.1",
            sdp_offer="v=0\r\n..."
        )
        
        if not result:
            print("SIP操作失败")
            return False
            
        return True
        
    except ConnectionError as e:
        print(f"连接错误: {e}")
        return False
    except TimeoutError as e:
        print(f"超时错误: {e}")
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        return False
```