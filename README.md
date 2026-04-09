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
- **core**: 核心层，包含pytest集成、DSL定义和报告生成
- **sip_client**: 客户端层，管理各种SIP客户端实现
- **rf_adapter**: RF适配层，提供Robot Framework到pytest的桥接功能
- **Test Parser**: YAML/JSON测试用例解析器
- **Report Generator**: 多格式测试报告生成器
- **Client Manager**: 客户端管理器，统一管理SIP客户端生命周期

## 功能特性

- 基于pytest的成熟测试执行和管理能力
- SIP协议特定的领域特定语言（DSL）
- 支持YAML/JSON格式的可读性测试用例定义
- 灵活的资源管理和测试执行策略
- 多格式的测试报告（JSON, HTML, Text）
- 并行测试执行支持
- 丰富的测试标记和参数化支持
- 统一的客户端管理和状态追踪
- 异步报告生成，提高性能
- RFC 3261合规性验证
- 客户端重连机制，提高稳定性

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

## 快速开始

1. **安装Python依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **运行基础SIP测试**：
   ```bash
   python -m pytest AutoTestForUG/tests/ -v
   ```

3. **运行主程序**：
   ```bash
   python AutoTestForUG/main.py
   ```

4. **从YAML配置运行测试**：
   ```bash
   python AutoTestForUG/execute_call_forwarding_test.py
   ```

## 使用示例

### 1. 基础SIP呼叫测试
```python
import pytest
from AutoTestForUG.sip_client.client_manager import SIPClientManager
from AutoTestForUG.sip_client.client_selection_strategy import SIPClientType

def test_basic_sip_call():
    # 创建客户端管理器
    manager = SIPClientManager()
    
    # 创建统一SIP客户端
    client = manager.create_client(SIPClientType.UNIFIED)
    
    # 执行注册
    register_result = client.register('alice', 'password123')
    assert register_result.success, f"注册失败: {register_result.error_message}"
    
    # 执行呼叫
    call_result = client.make_call('sip:alice@127.0.0.1:5060', 'sip:bob@127.0.0.1:5060')
    assert call_result.success, f"呼叫失败: {call_result.error_message}"
    
    # 取消注册
    unregister_result = client.unregister()
    assert unregister_result.success, f"取消注册失败: {unregister_result.error_message}"
```

### 2. DSL方式定义呼叫流程
```python
from AutoTestForUG.core.pytest_integration.sip_dsl import SIPCallFlow

def test_sip_call_flow():
    # 使用DSL定义呼叫流程
    call_flow = SIPCallFlow()
    call_flow.invite("sip:alice@domain.com")\
             .expect_response(200)\
             .ack()\
             .bye()\
             .expect_response(200)
    
    # 执行呼叫流程
    # 这里可以结合具体客户端实现
    print("呼叫流程定义完成:", call_flow)
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

## 项目结构

```
AutoTestForUG/
├── business_layer/         # 业务层 - 测试场景编排和管理
│   ├── __init__.py
│   ├── business_test_suite.py
│   └── enhanced_test_scenario.py
├── config/                 # 配置文件
│   ├── config.ini
│   └── config.py
├── core/                   # 核心层 - 框架核心功能
│   ├── distributed/        # 分布式执行相关
│   ├── pytest_integration/ # pytest集成
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── fixtures.py
│   │   ├── report_generator.py
│   │   └── sip_dsl.py
│   ├── __init__.py
│   └── report_generator.py
├── docs/                   # 文档
├── sip_client/             # 客户端层 - SIP客户端实现
│   ├── __init__.py
│   ├── client_manager.py
│   ├── enhanced_socket_client.py
│   ├── pj_sip_client.py
│   ├── socket_client_adapter.py
│   └── unified_sip_client.py
├── test_cases/             # 测试用例定义
├── tests/                  # 单元测试
├── utils/                  # 工具类
├── web_interface/          # Web界面
├── main.py                 # 主入口文件
├── requirements.txt        # Python依赖
└── setup_linux_env.sh      # Linux环境设置脚本
```

## 部署指南

### Linux环境部署

1. **安装系统依赖**：
   ```bash
   # Ubuntu/Debian
   sudo apt-get update -y
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
   python3 AutoTestForUG/main.py --test-type all
   ```

#### 作为系统服务运行

1. **复制服务文件到系统目录**：
   ```bash
   sudo cp AutoTestForUG/sip-auto-test.service /etc/systemd/system/
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

## Windows环境下的PJSIP支持

为了在Windows环境下使用PJSIP协议栈进行SIP测试，项目提供了专门的支持。

### 安装PJSIP库

1. **使用安装脚本**（推荐）：
   ```bash
   python AutoTestForUG/install_pjsip_windows.py
   ```

2. **手动安装**：
   - 访问 [PJSIP官方发布页面](https://github.com/pjsip/pjproject/releases)
   - 下载适合您Python版本的pjsua2 wheel文件
   - 安装wheel文件：
     ```bash
     pip install path/to/downloaded/pjsua2-x.x.x-cpxx-cpxxm-win_amd64.whl
     ```
   - 注意：cpXX表示Python版本（如cp39表示Python 3.9），amd64表示64位系统

3. **验证安装**：
   ```bash
   python -c "import pjsua2; print('PJSIP库安装成功')"
   ```

## 开发计划

项目持续发展中，主要开发方向包括：

1. **增强测试覆盖**：扩展更多SIP协议场景的测试覆盖
2. **性能优化**：进一步提高测试执行效率和并发能力
3. **Web界面**：完善Web界面，提供更直观的测试管理和监控
4. **CI/CD集成**：提供更完善的CI/CD集成方案
5. **多协议支持**：扩展支持更多通信协议

## 许可证

[MIT License](https://opensource.org/licenses/MIT)

## 贡献

欢迎贡献代码、报告问题或提出建议！请通过GitHub Issues或Pull Requests参与项目。

## 联系方式

- 项目地址：https://github.com/zzJeremy/sip-automation-test-platform
- 维护者：zzJeremy
