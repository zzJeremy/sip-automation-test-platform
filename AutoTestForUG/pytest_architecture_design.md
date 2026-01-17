# SIP自动化测试平台 - Pytest架构设计文档

## 1. 架构概述

### 1.1 设计理念
采用"开源测试框架 + 轻量领域层（DSL/adapter）"的混合方案，以pytest作为执行引擎，构建SIP自动化测试平台。该架构充分利用pytest的生态系统，同时在pytest之上实现SIP特定的领域层。

### 1.2 架构目标
- 利用pytest成熟的测试执行和管理能力
- 提供SIP协议特定的领域特定语言（DSL）
- 支持YAML/JSON格式的可读性测试用例定义
- 实现灵活的资源管理和测试执行策略
- 提供多格式的测试报告

## 2. 架构组件

### 2.1 核心执行层 - Pytest
- **pytest框架**: 提供测试发现、执行、报告等核心功能
- **pytest-xdist**: 支持并行测试执行
- **pytest-rerunfailures**: 支持失败测试重试
- **allure-pytest**: 生成详细的测试报告

### 2.2 领域特定语言层（DSL）

#### 2.2.1 SIP DSL模块 (`sip_dsl.py`)
- **SIPCallFlow**: 定义SIP呼叫流程的DSL类
- **SIPMessageValidator**: SIP消息验证器
- **SIPTestScenario**: SIP测试场景定义
- **便捷函数**: `define_call_scenario`, `define_test_scenario`

#### 2.2.2 DSL功能特性
- 流式API设计，支持链式调用
- 完整的SIP方法枚举支持
- 呼叫状态管理
- 消息格式验证

### 2.3 资源管理层 - Fixtures

#### 2.3.1 核心fixtures (`fixtures.py`)
- **port_pool**: 全局端口池管理，用于分配SIP测试端口
- **sip_client_factory**: SIP客户端工厂，自动管理客户端生命周期
- **temp_test_dir**: 临时测试目录
- **test_logger**: 测试日志记录器
- **basic_call_scenario**: 基础呼叫场景
- **sip_test_config**: SIP测试配置
- **pcap_collector**: PCAP包收集器（模拟实现）
- **sip_trace_collector**: SIP消息追踪收集器

#### 2.3.2 资源管理特性
- 自动资源分配和清理
- 会话级和函数级作用域管理
- 异常安全的资源释放

### 2.4 测试用例管理层

#### 2.4.1 测试用例解析器 (`test_case_parser.py`)
- **TestCaseParser**: YAML/JSON格式测试用例解析
- **SIPTestCaseDefinition**: 测试用例数据结构定义
- **TestSuiteExecutor**: 测试套件执行器

#### 2.4.2 测试用例格式支持
- YAML格式定义
- JSON格式定义
- 参数化测试支持
- 元数据和标签支持

### 2.5 报告生成层 (`report_generator.py`)

#### 2.5.1 报告格式支持
- JSON格式报告
- HTML格式报告
- 文本格式报告
- 集成pytest-html报告

#### 2.5.2 报告特性
- 详细测试结果记录
- SIP消息追踪
- 性能指标统计
- 错误分析和分类

### 2.6 执行管理层 (`test_executor.py`)

#### 2.6.1 执行器功能
- YAML/JSON测试用例执行
- pytest参数传递
- 环境变量设置
- 执行结果处理

## 3. 测试用例定义

### 3.1 YAML测试用例示例
```yaml
test_cases:
  - name: "基础呼叫建立测试"
    description: "测试基本的SIP呼叫建立流程：INVITE -> 200 OK -> ACK -> BYE"
    type: "basic_call"
    config:
      server_host: "127.0.0.1"
      server_port: 5060
      local_host: "127.0.0.1"
      local_port: 5080
      timeout: 30
      retry_count: 3
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
      - action: "maintain_call"
        description: "维持通话连接"
      - action: "send_bye"
        description: "发送BYE请求终止呼叫"
      - action: "wait_for_200ok_bye"
        description: "等待BYE的200 OK响应"
    expected_results:
      - "成功发送INVITE请求"
      - "在规定时间内收到200 OK响应"
      - "成功发送ACK确认"
      - "通话维持指定时长"
      - "成功发送BYE请求"
      - "收到BYE的200 OK响应"
    metadata:
      priority: "high"
      category: "functional"
      author: "sip-test-team"
      tags: ["basic", "call", "regression"]
      environment: "local"
    prerequisites:
      - "SIP服务器正在运行"
      - "网络连接正常"
      - "端口5060可用"
```

### 3.2 pytest测试用例示例
```python
@pytest.mark.sip_basic
@pytest.mark.parametrize("test_config", [
    {
        "caller_uri": "sip:alice@127.0.0.1:5060",
        "callee_uri": "sip:bob@127.0.0.1:5060",
        "call_duration": 5
    },
    {
        "caller_uri": "sip:charlie@127.0.0.1:5060", 
        "callee_uri": "sip:diana@127.0.0.1:5060",
        "call_duration": 3
    }
])
def test_basic_sip_call(sip_client_factory, test_config: Dict[str, Any]):
    """测试基础SIP呼叫功能"""
    caller_client = sip_client_factory(
        client_id="caller",
        local_port=test_config.get("local_port", 5080)
    )
    
    # 执行呼叫
    result = caller_client.make_basic_call(
        caller_uri=test_config["caller_uri"],
        callee_uri=test_config["callee_uri"], 
        call_duration=test_config["call_duration"]
    )
    
    assert result is True, f"基础呼叫失败: {test_config['caller_uri']} -> {test_config['callee_uri']}"
```

## 4. 配置管理

### 4.1 pytest配置 (`conftest.py`)
- 自定义标记定义
- fixtures自动发现
- 测试环境配置

### 4.2 标记系统
- `@pytest.mark.sip_basic`: 基础SIP功能测试
- `@pytest.mark.sip_call_flow`: SIP呼叫流程测试
- `@pytest.mark.sip_message`: SIP消息格式测试
- `@pytest.mark.sip_integration`: SIP集成测试

## 5. 执行流程

### 5.1 测试执行流程
1. pytest发现测试用例
2. fixtures初始化（端口分配、客户端创建等）
3. 测试用例执行
4. DSL层处理SIP呼叫流程
5. fixtures清理（资源释放）

### 5.2 执行器模式
- 直接pytest执行
- 通过测试执行器执行
- YAML配置文件驱动执行

## 6. 扩展性设计

### 6.1 插件化设计
- fixtures可扩展
- DSL方法可扩展
- 报告格式可扩展

### 6.2 集成能力
- 与CI/CD系统集成
- 与监控系统集成
- 与缺陷管理系统集成

## 7. 性能和并发

### 7.1 并发执行
- pytest-xdist支持并行执行
- 端口池管理避免端口冲突
- 客户端隔离确保测试独立性

### 7.2 资源优化
- 会话级资源复用
- 自动资源清理
- 内存使用优化

## 8. 错误处理和调试

### 8.1 错误处理
- fixtures异常安全
- 客户端连接异常处理
- 网络异常处理

### 8.2 调试支持
- 详细的日志记录
- SIP消息追踪
- 执行流程记录

## 9. 部署和运维

### 9.1 依赖管理
- requirements.txt定义
- Python版本兼容性
- 第三方库版本锁定

### 9.2 运行环境
- 本地开发环境
- CI/CD环境
- 生产测试环境

## 10. 测试策略

### 10.1 测试类型
- 单元测试：验证DSL方法
- 集成测试：验证端到端流程
- 系统测试：验证与SIP服务器交互

### 10.2 测试覆盖
- 功能覆盖
- 异常路径覆盖
- 性能指标覆盖