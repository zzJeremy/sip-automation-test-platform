import axios from 'axios'

// 创建axios实例
const apiClient = axios.create({
  baseURL: '/api', // 使用Vite配置的代理
  timeout: 30000, // 增加超时时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    // 在发送请求之前做些什么，比如添加认证token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 添加请求时间戳
    config.metadata = { startTime: new Date() }
    
    return config
  },
  error => {
    // 对请求错误做些什么
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    // 计算请求耗时
    const endTime = new Date()
    const startTime = response.config.metadata?.startTime
    const duration = startTime ? endTime - startTime : 0
    
    console.log(`API请求 ${response.config.url} 耗时: ${duration}ms`)
    
    // 检查响应状态
    if (response.status >= 200 && response.status < 300) {
      return response.data
    } else {
      throw new Error(`HTTP错误: ${response.status}`)
    }
  },
  error => {
    // 对响应错误做点什么
    let errorMessage = 'API请求失败'
    
    if (error.response) {
      // 服务器返回了错误状态码
      const { status, data } = error.response
      
      switch (status) {
        case 400:
          errorMessage = '请求参数错误'
          break
        case 401:
          errorMessage = '未授权，请重新登录'
          // 可以在这里跳转到登录页
          break
        case 403:
          errorMessage = '权限不足'
          break
        case 404:
          errorMessage = '请求的资源不存在'
          break
        case 500:
          errorMessage = '服务器内部错误'
          break
        default:
          errorMessage = `请求失败 (${status}): ${data.message || data.detail || '未知错误'}`
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      errorMessage = '网络错误或服务器无响应'
    } else {
      // 其他错误
      errorMessage = error.message || '未知错误'
    }
    
    console.error('API请求错误:', errorMessage, error)
    
    // 显示错误消息（可以替换为实际的UI提示）
    console.error('错误详情:', errorMessage)
    
    return Promise.reject({ ...error, message: errorMessage })
  }
)

// 测试套件相关API
export const suiteApi = {
  // 获取所有测试套件
  getAllSuites: (params = {}) => apiClient.get('/suites', { params }),
  
  // 获取单个测试套件
  getSuiteById: (id) => apiClient.get(`/suites/${id}`),
  
  // 获取测试套件详情（包含关联的测试场景）
  getSuiteWithScenarios: (id) => apiClient.get(`/suites/${id}/scenarios`),
  
  // 创建测试套件
  createSuite: (suiteData) => apiClient.post('/suites', suiteData),
  
  // 更新测试套件
  updateSuite: (id, suiteData) => apiClient.put(`/suites/${id}`, suiteData),
  
  // 删除测试套件
  deleteSuite: (id) => apiClient.delete(`/suites/${id}`),
  
  // 批量删除测试套件
  bulkDeleteSuites: (ids) => apiClient.delete('/suites/bulk', { data: { ids } }),
  
  // 获取测试套件统计信息
  getSuiteStats: () => apiClient.get('/suites/stats'),
  
  // 导出测试套件
  exportSuite: (id) => apiClient.get(`/suites/${id}/export`, { responseType: 'blob' }),
  
  // 导入测试套件
  importSuite: (formData) => apiClient.post('/suites/import', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 测试场景相关API
export const scenarioApi = {
  // 获取所有测试场景
  getAllScenarios: (params = {}) => apiClient.get('/scenarios', { params }),
  
  // 获取单个测试场景
  getScenarioById: (id) => apiClient.get(`/scenarios/${id}`),
  
  // 获取测试场景详情（包含步骤和配置）
  getScenarioWithDetails: (id) => apiClient.get(`/scenarios/${id}/details`),
  
  // 创建测试场景
  createScenario: (scenarioData) => apiClient.post('/scenarios', scenarioData),
  
  // 更新测试场景
  updateScenario: (id, scenarioData) => apiClient.put(`/scenarios/${id}`, scenarioData),
  
  // 删除测试场景
  deleteScenario: (id) => apiClient.delete(`/scenarios/${id}`),
  
  // 批量删除测试场景
  bulkDeleteScenarios: (ids) => apiClient.delete('/scenarios/bulk', { data: { ids } }),
  
  // 复制测试场景
  copyScenario: (id) => apiClient.post(`/scenarios/${id}/copy`),
  
  // 获取测试场景模板
  getScenarioTemplates: () => apiClient.get('/scenarios/templates'),
  
  // 获取SIP协议相关的预定义步骤
  getSipSteps: () => apiClient.get('/scenarios/sip-steps'),
  
  // 验证测试场景配置
  validateScenario: (scenarioData) => apiClient.post('/scenarios/validate', scenarioData)
}

// 测试执行相关API
export const executionApi = {
  // 获取所有执行记录
  getAllExecutions: (params = {}) => apiClient.get('/executions', { params }),
  
  // 开始执行测试
  startExecution: (executionData) => apiClient.post('/executions', executionData),
  
  // 批量执行测试
  startBulkExecution: (executionData) => apiClient.post('/executions/bulk', executionData),
  
  // 停止执行测试
  stopExecution: (id) => apiClient.delete(`/executions/${id}`),
  
  // 暂停执行测试
  pauseExecution: (id) => apiClient.put(`/executions/${id}/pause`),
  
  // 恢复执行测试
  resumeExecution: (id) => apiClient.put(`/executions/${id}/resume`),
  
  // 获取执行状态
  getExecutionStatus: (id) => apiClient.get(`/executions/${id}/status`),
  
  // 获取执行详情
  getExecutionDetail: (id) => apiClient.get(`/executions/${id}/detail`),
  
  // 获取执行日志
  getExecutionLogs: (id, params = {}) => apiClient.get(`/executions/${id}/logs`, { params }),
  
  // 获取执行结果
  getExecutionResults: (id) => apiClient.get(`/executions/${id}/results`),
  
  // 重新执行测试
  reExecute: (id) => apiClient.post(`/executions/${id}/reexecute`),
  
  // 获取执行统计信息
  getExecutionStats: (params = {}) => apiClient.get('/executions/stats', { params }),
  
  // 获取实时执行指标
  getRealtimeMetrics: (id) => apiClient.get(`/executions/${id}/metrics`)
}

// 仪表板相关API
export const dashboardApi = {
  // 获取统计信息
  getStats: () => apiClient.get('/dashboard/stats'),
  
  // 获取最近测试记录
  getRecentTests: (params = {}) => apiClient.get('/dashboard/recent-tests', { params }),
  
  // 获取趋势数据
  getTrendData: (params = {}) => apiClient.get('/dashboard/trends', { params }),
  
  // 运行快速测试
  runQuickTest: (testData = {}) => apiClient.post('/dashboard/quick-test', testData),
  
  // 获取系统健康状态
  getSystemHealth: () => apiClient.get('/dashboard/health'),
  
  // 获取实时指标
  getLiveMetrics: () => apiClient.get('/dashboard/metrics')
}

// 测试用例相关API
export const testCaseApi = {
  // 获取所有测试用例
  getAllTestCases: () => apiClient.get('/test_cases'),
  
  // 获取测试用例浏览器数据
  getTestBrowser: () => apiClient.get('/test_browser'),
  
  // 执行特定测试用例
  executeTestCase: (testCaseId, config = {}) => apiClient.post(`/test_cases/${testCaseId}/execute`, config),
  
  // 获取测试用例详情
  getTestCaseDetail: (id) => apiClient.get(`/test_cases/${id}`),
  
  // 获取测试用例分类统计
  getTestCaseStats: () => apiClient.get('/test_cases/stats')
}

// 测试报告相关API
export const reportApi = {
  // 获取所有报告
  getAllReports: (params = {}) => apiClient.get('/reports', { params }),
  
  // 获取单个报告
  getReportById: (id) => apiClient.get(`/reports/${id}`),
  
  // 获取报告详情（包含完整数据）
  getReportDetail: (id) => apiClient.get(`/reports/${id}/detail`),
  
  // 获取报告统计数据
  getReportStats: () => apiClient.get('/reports/stats'),
  
  // 获取趋势分析数据
  getTrendAnalysis: (params = {}) => apiClient.get('/reports/trends', { params }),
  
  // 生成报告
  generateReport: (reportData) => apiClient.post('/reports/generate', reportData),
  
  // 导出报告（支持多种格式）
  exportReport: (id, format = 'pdf') => apiClient.get(`/reports/${id}/export?format=${format}`, { 
    responseType: 'blob' 
  }),
  
  // 导出JSON格式报告
  exportReportJson: (id) => apiClient.get(`/reports/${id}/export/json`, { 
    responseType: 'blob' 
  }),
  
  // 导出HTML格式报告
  exportReportHtml: (id) => apiClient.get(`/reports/${id}/export/html`, { 
    responseType: 'blob' 
  }),
  
  // 导出PDF格式报告
  exportReportPdf: (id) => apiClient.get(`/reports/${id}/export/pdf`, { 
    responseType: 'blob' 
  }),
  
  // 批量导出报告
  bulkExportReports: (ids, format = 'pdf') => apiClient.post('/reports/export/bulk', { 
    ids, 
    format 
  }, {
    responseType: 'blob'
  }),
  
  // 删除报告
  deleteReport: (id) => apiClient.delete(`/reports/${id}`),
  
  // 批量删除报告
  bulkDeleteReports: (ids) => apiClient.delete('/reports/bulk', { data: { ids } }),
  
  // 重跑测试
  rerunTest: (id) => apiClient.post(`/reports/${id}/rerun`),
  
  // 获取报告模板
  getReportTemplates: () => apiClient.get('/reports/templates'),
  
  // 获取SIP测试专用报告
  getSipSpecificReport: (id) => apiClient.get(`/reports/${id}/sip-specific`)
}

// 系统配置相关API
export const configApi = {
  // 获取系统配置
  getSystemConfig: () => apiClient.get('/config/system'),
  
  // 更新系统配置
  updateSystemConfig: (configData) => apiClient.put('/config/system', configData),
  
  // 获取SIP客户端配置
  getSipClientsConfig: () => apiClient.get('/config/sip-clients'),
  
  // 测试SIP连接
  testSipConnection: (connectionData) => apiClient.post('/config/test-connection', connectionData)
}

export default apiClient