# AutoTestForUG API文档

## 1. 概述

本文档描述了AutoTestForUG系统的内部API接口，包括各模块的类和方法。

## 2. 核心模块API

### 2.1 SIP测试客户端 (test_client/sip_test_client.py)

#### SIPTestClient类

##### 构造函数
```python
def __init__(self, server_host: str, server_port: int, protocol: str = 'UDP', logger=None):
```
- `server_host`: SIP服务器地址
- `server_port`: SIP服务器端口
- `protocol`: 传输协议 ('UDP' 或 'TCP')
- `logger`: 日志记录器

##### register方法
```python
def register(self, username: str, password: str, domain: str) -> bool
```
执行SIP注册操作
- `username`: 用户名
- `password`: 密码
- `domain`: 域名
- 返回值: 注册是否成功

##### make_call方法
```python
def make_call(self, caller: str, callee: str) -> bool
```
发起SIP呼叫
- `caller`: 主叫号码
- `callee`: 被叫号码
- 返回值: 呼叫是否成功建立

##### send_message方法
```python
def send_message(self, sender: str, recipient: str, content: str) -> bool
```
发送SIP消息
- `sender`: 发送方
- `recipient`: 接收方
- `content`: 消息内容
- 返回值: 消息是否发送成功

##### send_request方法
```python
def send_request(self, method: str, uri: str, headers: dict = None, body: str = '') -> Optional[dict]
```
发送SIP请求
- `method`: SIP方法
- `uri`: 请求URI
- `headers`: 请求头
- `body`: 请求体
- 返回值: 响应字典或None

### 2.2 性能监控器 (monitor_client/performance_monitor.py)

#### PerformanceMonitor类

##### 构造函数
```python
def __init__(self, config: dict, logger=None):
```
- `config`: 配置字典
- `logger`: 日志记录器

##### start_monitoring方法
```python
def start_monitoring(self):
```
启动性能监控

##### stop_monitoring方法
```python
def stop_monitoring(self):
```
停止性能监控

##### collect_data方法
```python
def collect_data(self) -> dict:
```
收集当前性能数据
- 返回值: 包含CPU、内存、磁盘、网络信息的字典

##### check_thresholds方法
```python
def check_thresholds(self, data: dict) -> dict:
```
检查性能指标是否超过阈值
- `data`: 性能数据
- 返回值: 告警信息字典

##### export_data方法
```python
def export_data(self, data: list, filename: str):
```
导出监控数据
- `data`: 监控数据列表
- `filename`: 输出文件名

### 2.3 pytest测试套件 (pytest_sip_tests/)

#### pytest_sip_tests包结构

包含以下主要模块：
- `fixtures.py`: pytest fixtures，管理端口池、客户端实例等资源
- `sip_dsl.py`: SIP特定领域语言，提供简洁的API定义SIP测试场景
- `test_case_parser.py`: 解析YAML/JSON格式的测试用例定义
- `report_generator.py`: 生成多格式测试报告（JSON, HTML, Text）
- `test_executor.py`: 测试执行器，集成pytest运行并提供命令行接口

#### 核心功能模块

##### Fixtures
- `port_pool`: 端口池管理，为测试提供可用端口
- `sip_client_factory`: SIP客户端工厂，创建和管理SIP客户端实例
- `test_environment`: 测试环境管理，支持不同测试模式

##### SIP DSL (Domain Specific Language)
- `SIPCallFlow`: 定义SIP呼叫流程的DSL，支持流式调用风格
- `SIPMessageValidator`: SIP消息验证器，提供灵活的消息匹配和验证功能

##### 测试执行器
- `TestExecutor.execute_pytest_suite`: 执行pytest测试套件
- `TestExecutor.run_pytest_with_config`: 使用配置文件运行pytest测试

### 2.4 配置管理器 (config/config.py)

#### load_config函数
```python
def load_config(config_path: str = './config/config.ini') -> dict:
```
加载配置文件
- `config_path`: 配置文件路径
- 返回值: 配置字典

#### save_config函数
```python
def save_config(config: dict, config_path: str = './config/config.ini'):
```
保存配置文件
- `config`: 配置字典
- `config_path`: 配置文件路径

#### get_config_value函数
```python
def get_config_value(section: str, key: str, default=None) -> Any:
```
获取配置值
- `section`: 配置节
- `key`: 配置键
- `default`: 默认值
- 返回值: 配置值

### 2.5 工具函数 (utils/utils.py)

#### 日志相关函数

##### setup_logger函数
```python
def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
```
设置日志记录器
- `name`: 记录器名称
- `log_file`: 日志文件路径
- `level`: 日志级别
- 返回值: 日志记录器对象

#### 文件处理相关函数

##### read_test_cases函数
```python
def read_test_cases(file_path: str) -> List[dict]:
```
读取测试用例文件
- `file_path`: 文件路径
- 返回值: 测试用例列表

##### write_test_results函数
```python
def write_test_results(results: List[dict], file_path: str):
```
写入测试结果
- `results`: 测试结果列表
- `file_path`: 输出文件路径

#### 数据格式化相关函数

##### format_test_result函数
```python
def format_test_result(result: dict) -> str:
```
格式化测试结果
- `result`: 测试结果字典
- 返回值: 格式化后的字符串

##### export_to_csv函数
```python
def export_to_csv(data: List[dict], filename: str):
```
导出数据到CSV文件
- `data`: 数据列表
- `filename`: 输出文件名

#### 网络相关函数

##### get_network_latency函数
```python
def get_network_latency(host: str, port: int, timeout: int = 3) -> Optional[float]:
```
获取网络延迟
- `host`: 目标主机
- `port`: 目标端口
- `timeout`: 超时时间
- 返回值: 延迟时间（秒）或None

##### is_port_open函数
```python
def is_port_open(host: str, port: int, timeout: int = 3) -> bool:
```
检查端口是否开放
- `host`: 目标主机
- `port`: 目标端口
- `timeout`: 超时时间
- 返回值: 端口是否开放

#### ID生成相关函数

##### generate_unique_id函数
```python
def generate_unique_id(prefix: str = "") -> str:
```
生成唯一ID
- `prefix`: 前缀
- 返回值: 唯一ID字符串

#### 重试装饰器

##### retry_on_failure装饰器
```python
def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
```
重试装饰器
- `max_retries`: 最大重试次数
- `delay`: 重试间隔（秒）

## 3. 配置文件格式

### 3.1 config.ini格式

```
[SIP]
server_host = 127.0.0.1
server_port = 5060
transport_protocol = UDP

[Performance]
cpu_threshold = 80
memory_threshold = 85
disk_threshold = 90
network_threshold = 100

[Test]
max_concurrent_users = 100
test_duration = 300
call_duration = 60
```

### 3.2 test_cases.ini格式

```
[test_registration]
type = registration
username = testuser
password = testpass
domain = example.com
expected_result = success

[test_call]
type = call
caller = user1
callee = user2
expected_result = success
```

## 4. 错误处理

系统采用标准的异常处理机制，所有错误信息都会记录到日志文件中。主要异常类型包括：
- ConnectionError: 连接错误
- TimeoutError: 超时错误
- AuthenticationError: 认证错误
- ProtocolError: 协议错误