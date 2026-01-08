# SIP自动化测试平台

## 项目概述

SIP自动化测试平台是一个三层架构的SIP协议测试框架，旨在提供一个灵活、可扩展的SIP协议自动化测试解决方案。项目结合了多种SIP实现方式，包括原生socket实现、PJSIP专业库、SIPp工具以及安全测试客户端。

## 架构设计

### 三层架构
```
┌─────────────────────────────────────────┐
│           统一接口层                     │
│        SIPClientBase                    │
└─────────────────────────────────────────┘
                │
┌─────────────────────────────────────────┐
│          协议实现层                      │
│  SocketSIPClientAdapter  │ PJSIPSIPClient │
│  SIPpDriverClient        │ SocketFuzzClient │
└─────────────────────────────────────────┘
                │
┌─────────────────────────────────────────┐
│          智能调度层                      │
│        TestOrchestrator                 │
└─────────────────────────────────────────┘
```

### 核心组件

- **SIPClientBase**: 定义SIP客户端统一接口
- **PJSIPSIPClient**: 基于PJSIP库的专业SIP实现
- **SocketSIPClientAdapter**: 基于socket的适配器实现
- **SIPpDriverClient**: 基于SIPp工具的性能测试实现
- **SocketFuzzClient**: 基于socket的安全测试实现
- **TestOrchestrator**: 智能调度器，根据测试类型自动选择客户端

## 功能特性

- 统一的SIP客户端接口
- 多种SIP实现方式支持
- 智能测试调度
- 注册、呼叫、消息等SIP功能
- 性能测试支持
- 安全测试支持

## 安装依赖

```bash
pip install pjsua2  # 可选，用于PJSIP客户端
```

## 使用示例

```python
from AutoTestForUG.sip_client.client_manager import SIPClientManager
from AutoTestForUG.sip_client.test_orchestrator import TestOrchestrator, TestCase, TestType

# 使用客户端管理器
manager = SIPClientManager()
client = manager.create_client('PJSIP')
client.register('username', 'password')

# 使用测试调度器
test_case = TestCase(
    name="Functional Test",
    test_type=TestType.FUNCTIONAL,
    target="sip:test@server.com",
    parameters={}
)
orchestrator = TestOrchestrator()
result = orchestrator.execute_test(test_case)
```

## 项目结构

```
AutoTestForUG/
├── sip_client/           # SIP客户端实现
│   ├── sip_client_base.py    # 抽象基类
│   ├── pj_sip_client.py      # PJSIP实现
│   ├── socket_client_adapter.py # Socket适配器
│   ├── sipp_driver_client.py # SIPp驱动
│   ├── socket_fuzz_client.py # Fuzz测试客户端
│   ├── client_manager.py     # 客户端管理器
│   ├── hybrid_client.py      # 混合客户端
│   └── test_orchestrator.py  # 测试调度器
├── plan2026-01-08.md    # 开发计划文档
└── demo_three_tier_architecture.py # 演示代码
```

## 开发计划

请参考 `plan2026-01-08.md` 文件了解详细的开发计划和路线图。

## 许可证

[请根据实际情况填写许可证信息]