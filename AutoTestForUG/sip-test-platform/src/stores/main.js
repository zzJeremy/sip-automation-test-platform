import { defineStore } from 'pinia'

export const useMainStore = defineStore('main', {
  state: () => ({
    // 测试套件相关状态
    testSuites: [],
    selectedSuite: null,
    suiteStats: {},
    
    // 测试场景相关状态
    scenarios: [],
    scenarioTemplates: [],
    
    // 测试执行相关状态
    executionStatus: 'idle', // idle, running, paused, stopped, completed
    executionProgress: 0,
    executionLogs: [],
    currentExecutionId: null,
    
    // 测试报告相关状态
    testResults: [],
    reportData: {},
    reportStats: {},
    
    // 系统配置相关状态
    systemConfig: {},
    sipClientsConfig: {},
    
    // 连接状态
    isConnected: false,
    connectionStatus: 'disconnected' // disconnected, connecting, connected
  }),
  
  getters: {
    getTestSuiteById: (state) => (id) => {
      return state.testSuites.find(suite => suite.id === id)
    },
    getSelectedSuiteScenarios: (state) => {
      if (!state.selectedSuite) return []
      return state.selectedSuite.scenarios || []
    }
  },
  
  actions: {
    // 测试套件相关操作
    addTestSuite(suite) {
      this.testSuites.push(suite)
    },
    removeTestSuite(id) {
      this.testSuites = this.testSuites.filter(suite => suite.id !== id)
    },
    selectSuite(suite) {
      this.selectedSuite = suite
    },
    updateSuiteStats(stats) {
      this.suiteStats = { ...this.suiteStats, ...stats }
    },
    
    // 测试场景相关操作
    addScenario(scenario) {
      this.scenarios.push(scenario)
    },
    removeScenario(id) {
      this.scenarios = this.scenarios.filter(scenario => scenario.id !== id)
    },
    updateScenarioTemplates(templates) {
      this.scenarioTemplates = templates
    },
    
    // 执行相关操作
    startExecution(executionId = null) {
      this.executionStatus = 'running'
      this.executionProgress = 0
      if (executionId) {
        this.currentExecutionId = executionId
      }
    },
    pauseExecution() {
      this.executionStatus = 'paused'
    },
    stopExecution() {
      this.executionStatus = 'stopped'
      this.executionProgress = 100
    },
    completeExecution() {
      this.executionStatus = 'completed'
      this.executionProgress = 100
    },
    updateProgress(progress) {
      this.executionProgress = progress
    },
    setExecutionId(id) {
      this.currentExecutionId = id
    },
    addLog(log) {
      this.executionLogs.push(log)
      // 限制日志数量，避免内存占用过多
      if (this.executionLogs.length > 1000) {
        this.executionLogs.shift()
      }
    },
    clearLogs() {
      this.executionLogs = []
    },
    
    // 报告相关操作
    addTestResult(result) {
      this.testResults.push(result)
    },
    updateReportStats(stats) {
      this.reportStats = { ...this.reportStats, ...stats }
    },
    
    // 系统配置相关操作
    updateSystemConfig(config) {
      this.systemConfig = { ...this.systemConfig, ...config }
    },
    updateSipClientsConfig(config) {
      this.sipClientsConfig = { ...this.sipClientsConfig, ...config }
    },
    
    // 连接相关操作
    connect() {
      this.connectionStatus = 'connecting'
    },
    setConnected() {
      this.isConnected = true
      this.connectionStatus = 'connected'
    },
    disconnect() {
      this.isConnected = false
      this.connectionStatus = 'disconnected'
    }
  }
})