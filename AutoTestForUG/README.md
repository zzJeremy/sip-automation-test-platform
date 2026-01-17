# SIP自动化测试平台

## 项目概述

SIP自动化测试平台是一个基于pytest框架的SIP协议测试框架，采用"开源测试框架 + 轻量领域层（DSL/adapter）"的混合方案。项目充分利用pytest的生态系统，同时在pytest之上实现SIP特定的领域层，提供简洁的API来定义SIP测试场景。

## 架构设计

### 三层架构 + 混合方案
本项目采用清晰的三层架构设计，结合pytest生态系统：

```
┌─────────────────────────────────────────┐
│              业务层                      │
│    BusinessTestSuite, TestScenarioManager│
└─────────────────────────────────────────┘
                │
┌─────────────────────────────────────────┐
│        领域特定语言层（DSL）             │
│      SIPCallFlow, SIPMessageValidator   │
└─────────────────────────────────────────┘
                │
┌─────────────────────────────────────────┐
│          测试定义层                      │
│        YAML/JSON 测试用例               │
└─────────────────────────────────────────┘
                │
┌─────────────────────────────────────────┐
│          资源管理层                      │
│      pytest fixtures (端口池、客户端等)    │
└─────────────────────────────────────────┘
                │
┌─────────────────────────────────────────┐
│          执行引擎层                      │
│           pytest 框架                   │
└─────────────────────────────────────────┘
```

### 核心组件

- **business_layer**: 业务层，包含业务测试套件和场景管理
- **pytest_sip_tests**: 核心层，基于pytest的测试执行
- **rf_adapter**: RF适配层，提供Robot Framework到pytest的桥接功能
- **SIP DSL**: 领域特定语言，提供简洁的API定义SIP测试场景
- **Fixtures**: pytest fixtures管理端口池、客户端实例、测试环境等共享资源
- **Test Parser**: YAML/JSON测试用例解析器
- **Report Generator**: 多格式测试报告生成器
- **Test Executor**: 统一测试执行器，支持pytest和Robot Framework格式的测试
- **Client Manager**: 客户端管理器，统一管理SIP客户端生命周期

### 核心组件

- **pytest_sip_tests**: pytest测试套件
- **SIP DSL**: 领域特定语言，提供简洁的API定义SIP测试场景
- **Fixtures**: pytest fixtures管理端口池、客户端实例、测试环境等共享资源
- **Test Parser**: YAML/JSON测试用例解析器
- **Report Generator**: 多格式测试报告生成器
- **Test Executor**: 测试执行器，集成pytest运行

## 功能特性

- 基于pytest的成熟测试执行和管理能力
- SIP协议特定的领域特定语言（DSL）
- 支持YAML/JSON格式的可读性测试用例定义
- 灵活的资源管理和测试执行策略
- 多格式的测试报告（JSON, HTML, Text）
- 并行测试执行支持
- 丰富的测试标记和参数化支持

## 环境依赖

### Python依赖
```bash
# 使用pip安装Python依赖
pip install -r requirements.txt

# 或使用poetry安装（推荐）
poetry install
```

### 系统级依赖
以下工具需要单独安装：

- **SIPp**: SIP协议性能测试工具（可选）
  ```bash
  # Ubuntu/Debian
  sudo apt-get install sipp

  # CentOS/RHEL
  sudo yum install sipp

  # macOS
  brew install sipp
  ```

- **SIP服务器**: 用于测试的SIP服务器（如Asterisk, Kamailio等）

### 快速开始

1. **安装Python依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **运行基础SIP测试**：
   ```bash
   python -m pytest AutoTestForUG/pytest_sip_tests/ -v -m sip_basic
   ```

3. **运行所有测试**：
   ```bash
   python -m pytest AutoTestForUG/pytest_sip_tests/ -v
   ```

4. **使用测试执行器**：
   ```bash
   python AutoTestForUG/pytest_sip_tests/test_executor.py
   ```

5. **从YAML配置运行测试**：
   ```bash
   python AutoTestForUG/pytest_sip_tests/test_executor.py --config test_cases_yaml_example.yaml
   ```

## 使用示例

### 1. 基础SIP呼叫测试
```python
import pytest
from AutoTestForUG.core.pytest_integration.sip_dsl import define_call_scenario

@pytest.mark.sip_basic
def test_basic_sip_call(sip_client_factory):
    caller_client = sip_client_factory(client_id="caller")
    
    # 执行呼叫
    result = caller_client.make_basic_call(
        caller_uri="sip:alice@127.0.0.1:5060",
        callee_uri="sip:bob@127.0.0.1:5060",
        call_duration=5
    )
    
    assert result is True, "基础呼叫失败"
```

### 2. DSL方式定义呼叫流程
```python
@pytest.mark.sip_call_flow
def test_sip_call_flow_with_dsl(basic_call_scenario):
    scenario = basic_call_scenario
    
    # 使用DSL定义呼叫流程
    call_flow = define_call_scenario(
        caller_uri=scenario['caller_uri'],
        callee_uri=scenario['callee_uri'], 
        duration=scenario['call_duration']
    )
    
    # 执行呼叫流程
    result = scenario['caller_client'].make_basic_call(
        caller_uri=call_flow.caller_uri,
        callee_uri=call_flow.callee_uri,
        call_duration=call_flow.steps[-1]['duration'] if call_flow.steps else 5
    )
    
    assert result is True, "DSL呼叫流程执行失败"
```

### 3. YAML格式测试用例
```yaml
test_cases:
  - name: "基础呼叫建立测试"
    description: "测试基本的SIP呼叫建立流程"
    type: "basic_call"
    config:
      server_host: "127.0.0.1"
      server_port: 5060
      caller_uri: "sip:alice@127.0.0.1:5060"
      callee_uri: "sip:bob@127.0.0.1:5060"
      call_duration: 5
    steps:
      - action: "send_invite"
        description: "发送INVITE请求"
      - action: "wait_for_200ok"
        description: "等待200 OK响应"
      - action: "send_ack"
        description: "发送ACK确认"
      - action: "send_bye"
        description: "发送BYE请求终止呼叫"
```

## 架构优势

### 1. 利用成熟框架
- 充分利用pytest的生态系统
- 支持并行执行、重试、报告等功能
- 丰富的第三方插件支持

### 2. 领域特定语言
- 提供简洁的API定义SIP测试场景
- 支持流式调用风格
- 易于理解和维护

### 3. 灵活的测试定义
- 支持编程方式和声明方式（YAML/JSON）
- 便于非开发人员参与测试用例编写
- 支持参数化和数据驱动测试

### 4. 资源管理
- 自动化的资源分配和清理
- 会话级和函数级作用域管理
- 异常安全的资源释放

## 扩展性

- 可轻松扩展新的SIP DSL方法
- 支持新的测试用例格式
- 可集成更多pytest插件
- 支持与CI/CD系统集成
   sudo apt-get install -y sipp libpjsua2-dev python3 python3-pip python3-dev build-essential net-tools
   
   # CentOS/RHEL
   sudo yum update -y
   sudo yum install -y epel-release
   sudo yum install -y sipp libpjsua2-dev python3 python3-pip python3-devel gcc gcc-c++ net-tools
   ```

2. **安装Python依赖**：
   ```bash
   pip3 install -r requirements.txt
   # 或使用poetry
   poetry install
   ```

3. **初始化服务器环境**：
   ```bash
   chmod +x setup_linux_env.sh
   sudo ./setup_linux_env.sh
   ```

4. **配置系统参数**（可选但推荐）：
   系统会在部署过程中自动配置以下参数：
   - 文件描述符限制
   - 网络参数以支持大量并发连接

5. **运行测试**：
   ```bash
   python3 -m AutoTestForUG.main --test-type all
   ```

#### 作为系统服务运行

1. **复制服务文件到系统目录**：
   ```bash
   sudo cp sip-auto-test.service /etc/systemd/system/
   ```

2. **启用并启动服务**：
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sip-auto-test.service
   sudo systemctl start sip-auto-test.service
   ```

3. **检查服务状态**：
   ```bash
   sudo systemctl status sip-auto-test.service
   ```

4. **查看服务日志**：
   ```bash
   sudo journalctl -u sip-auto-test.service -f
   ```

## 使用示例

```python
from AutoTestForUG.sip_client.client_manager import SIPClientManager
from AutoTestForUG.core.pytest_integration.fixtures import sip_client_factory
from AutoTestForUG.core.pytest_integration.sip_dsl import SIPCallFlow

# 使用客户端管理器
manager = SIPClientManager()
client = manager.create_client('PJSIP')
client.register('username', 'password')

# 使用pytest SIP DSL
call_flow = SIPCallFlow()
call_flow.invite("sip:alice@domain.com").expect_response(200).ack().bye().expect_response(200)
```

## 项目结构

```
AutoTestForUG/
├── business_layer/         # 业务层 - 测试场景编排和管理
│   ├── __init__.py
│   ├── business_test_suite.py
│   └── test_scenario.py
├── config/                 # 配置文件
├── docs/                   # 文档
├── pytest_sip_tests/       # 核心层 - 基于pytest的测试执行
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures.py
│   ├── report_generator.py
│   └── sip_dsl.py
├── rf_adapter/             # RF适配层 - Robot Framework适配器
│   ├── __init__.py
│   └── robot_adapter.py
├── sip_client/             # 客户端层 - SIP客户端管理
├── test_cases/             # 测试用例定义
├── utils/                  # 工具类
└── main.py                 # 主入口文件
```

## 开发计划

请参考 `plan2026-01-08.md` 文件了解详细的开发计划和路线图。

## 许可证

[请根据实际情况填写许可证信息]