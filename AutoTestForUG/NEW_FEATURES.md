# SIP自动化测试框架 - 新增功能说明

## 1. 分布式执行引擎

新增了分布式执行引擎，支持多节点并行测试执行，提高测试效率。

### 使用方法
```python
from core.distributed.execution_engine import DistributedExecutionEngine

# 创建执行引擎
engine = DistributedExecutionEngine({
    "worker_threads": 3,
    "max_concurrent_per_node": 5
})

# 添加执行节点
engine.add_execution_node({
    "node_id": "local_node",
    "host": "localhost",
    "port": 5000,
    "max_concurrent": 3
})

# 提交执行任务
from core.distributed.execution_engine import ExecutionTask

task = ExecutionTask(
    task_type="pytest",
    command="test_basic_call.py",
    parameters={"--verbose": True},
    priority=0
)

task_id = engine.submit_task(task)

# 获取任务状态
task_status = engine.get_task_status(task_id)
```

## 2. Allure报告集成

集成了Allure报告组件，提供详细的测试报告和数据分析。

### 使用方法
```bash
# 运行测试并生成Allure报告
pytest --alluredir=./allure-results

# 生成HTML报告
allure serve ./allure-results
```

## 3. 设备控制器

提供了统一接口控制SIP设备，支持多种设备类型和控制方式。

### 使用方法
```python
from sip_client.device_controller import DeviceControllerFactory

# 创建Web设备控制器
web_controller = DeviceControllerFactory.create_controller(
    'web',
    device_url='http://192.168.1.100'
)

# 连接设备
web_controller.connect_device({
    'username': 'admin',
    'password': 'password'
})

# 发送命令
web_controller.send_command("register_sip_account", 
                          username="test_user", 
                          server="sip.example.com")

# 获取设备状态
status = web_controller.get_device_status()
```

## 4. 测试用例管理平台

提供了可视化测试用例管理平台，可通过Web界面管理测试用例。

### 启动方法
```bash
cd web_interface
python test_case_editor.py
```

然后访问 http://localhost:5001/test-case-editor

## 5. AMQP消息队列集成

Asterisk客户端现已支持AMQP消息队列，实现异步事件处理。

### 使用方法
```python
from sip_client.asterisk_sip_client import AsteriskSIPClient

# 创建启用AMQP的客户端
client = AsteriskSIPClient({
    'amqp_enabled': True,
    'amqp_host': 'localhost',
    'amqp_port': 5672,
    'amqp_username': 'guest',
    'amqp_password': 'guest'
})

# 发布事件到AMQP
client.publish_event('call_started', {
    'call_id': '12345',
    'from': 'sip:alice@example.com',
    'to': 'sip:bob@example.com'
})
```

## 6. 安装依赖

新增功能需要以下依赖：

```bash
pip install selenium>=4.0.0
pip install pika>=1.2.0
pip install allure-pytest>=2.9.45
pip install flask>=2.0.0
pip install flask-cors>=3.0.0
```