# AutoTestForUG用户使用手册

## 1. 系统要求

- Python 3.7或更高版本
- Windows/Linux/macOS操作系统
- 网络连接（用于测试SIP服务器）

## 2. 安装步骤

### 2.1 克隆或下载项目
将项目文件下载到本地目录。

### 2.2 安装依赖
在项目根目录下执行：
```bash
pip install -r requirements.txt
```

### 2.3 配置系统
根据实际环境修改以下配置文件：
- config/config.ini：系统参数配置
- config/test_cases.ini：测试用例配置

## 3. 快速开始

### 3.1 运行基本测试
```bash
python main.py --test-type call
```

### 3.2 运行特定测试类型
支持的测试类型包括：
- `register`：注册测试
- `call`：呼叫测试
- `message`：SIP消息测试
- `monitor`：性能监控
- `exception`：异常测试
- `all`：全部测试
- `business`：业务测试
- `conference`：会议呼叫测试
- `web` 或 `web_interface`：启动Web界面

### 3.3 启动Web界面
```bash
python main.py --test-type web
```

## 4. 配置说明

### 4.1 config.ini配置文件

#### [SIP]部分
- `server_host`：SIP服务器地址
- `server_port`：SIP服务器端口
- `transport_protocol`：传输协议（UDP/TCP/TLS）

#### [Performance]部分
- `cpu_threshold`：CPU使用率阈值（百分比）
- `memory_threshold`：内存使用率阈值（百分比）
- `disk_threshold`：磁盘使用率阈值（百分比）
- `network_threshold`：网络延迟阈值（毫秒）

#### [Test]部分
- `max_concurrent_users`：最大并发用户数
- `test_duration`：测试持续时间（秒）
- `call_duration`：单次通话持续时间（秒）

#### [LOGGING]部分
- `log_level`：日志级别（DEBUG/INFO/WARNING/ERROR）
- `log_format`：日志格式
- `log_file`：日志文件路径

### 4.2 test_cases.ini配置文件

定义各种测试用例，包括：
- 测试用例ID
- 测试类型（注册、呼叫、消息等）
- 测试参数

## 5. 高级功能

### 5.1 业务测试套件
使用BusinessTestSuite创建复杂的业务测试场景：
```python
from business_layer.business_test_suite import BusinessTestSuite, BusinessTestSuiteFactory

# 创建业务测试套件
suite = BusinessTestSuiteFactory.create_basic_sip_suite("My Test Suite")

# 添加测试场景并执行
result = suite.execute_suite(config)
```

### 5.2 SIP DSL（领域特定语言）
使用SIP DSL定义简单的测试场景：
```python
from core.pytest_integration.sip_dsl import SIPCallFlow

# 定义呼叫流程
call_flow = SIPCallFlow("sip:alice@domain.com", "sip:bob@domain.com")
call_flow.make_call(10).wait_for_ringing().wait_for_answer().wait(5).terminate_call()
```

### 5.3 Pytest集成
项目完全集成pytest框架，支持：
- fixtures管理测试资源
- 并行测试执行
- 详细的测试报告
- 参数化测试

### 5.4 多客户端支持
系统支持多种SIP客户端实现：
- Socket客户端：轻量级实现
- PJSIP客户端：功能完整的SIP栈
- SIPp控制器：外部SIPp工具集成
- Asterisk客户端：高级业务功能

## 6. Web界面使用

启动Web服务后，在浏览器访问 http://localhost:5000 查看测试界面。
Web界面提供：
- 测试配置管理
- 测试执行控制
- 实时测试结果显示
- 历史测试报告查看

## 7. 报告和日志

### 7.1 测试报告
系统生成多种格式的测试报告：
- JSON格式：便于程序处理
- HTML格式：便于查看
- CSV格式：便于数据分析
- TXT格式：便于存档

### 7.2 日志系统
完整的日志记录功能，包括：
- 操作日志
- 错误日志
- 性能指标日志
- 通信消息日志
- 预期结果

## 4. 使用方法

### 4.1 基本测试流程
1. 启动SIP服务器或确保目标服务器可用
2. 配置config.ini中的服务器信息
3. 在test_cases.ini中定义测试用例
4. 运行main.py启动测试

### 4.2 运行测试
```bash
python main.py
```

### 4.3 查看结果
测试完成后，结果将保存在：
- 控制台输出：实时测试状态
- 日志文件：详细操作记录
- 测试报告：汇总测试结果

## 5. 测试类型

### 5.1 SIP注册测试
验证用户注册功能，包括：
- 成功注册
- 认证失败
- 网络超时

### 5.2 SIP呼叫测试
验证呼叫建立功能，包括：
- 呼叫建立
- 呼叫保持/恢复
- 呼叫转移
- 呼叫终止

### 5.3 SIP消息测试
验证SIP消息功能，包括：
- OPTIONS消息
- MESSAGE消息
- INFO消息

### 5.4 性能测试
监控系统性能指标：
- CPU使用率
- 内存使用率
- 网络延迟
- 响应时间

## 6. 结果分析

### 6.1 测试报告
测试完成后生成的报告包含：
- 测试用例执行情况
- 性能指标统计
- 错误和异常记录
- 性能瓶颈分析

### 6.2 性能监控
实时监控系统资源使用情况，当超过设定阈值时发出告警。

## 7. 故障排除

### 7.1 常见问题

#### 问题：无法连接到SIP服务器
- 检查服务器地址和端口配置
- 确认服务器是否正常运行
- 检查防火墙设置

#### 问题：测试用例执行失败
- 检查测试参数配置
- 验证网络连接
- 查看详细日志信息

#### 问题：性能监控异常
- 检查系统权限
- 确认监控模块配置

### 7.2 日志查看
系统日志文件位于logs目录下，包含详细的执行信息和错误记录。

## 8. 高级功能

### 8.1 并发测试
通过配置max_concurrent_users参数设置并发用户数，进行压力测试。

### 8.2 自定义测试
可通过修改test_cases.ini文件添加自定义测试场景。

### 8.3 报告导出
支持将测试结果导出为多种格式（CSV、JSON等）。

## 9. 维护和扩展

### 9.1 添加新测试类型
通过在pytest_sip_tests/test_basic_calls.py中添加新的pytest测试函数来创建新的测试类型，或通过编写YAML/JSON格式的测试用例来定义新的测试场景。

### 9.2 自定义监控指标
通过修改performance_monitor.py添加新的监控指标。

### 9.3 扩展SIP功能
通过扩展sip_test_client.py和sip_test_server.py模块增加新的SIP功能支持。