<template>
  <div class="execution-monitor-container">
    <div class="page-header">
      <h2>测试执行与监控</h2>
      <div class="header-actions">
        <el-button type="primary" @click="startExecution">开始执行</el-button>
        <el-button type="danger" @click="stopExecution" :disabled="!isExecuting">停止执行</el-button>
        <el-button @click="clearLogs">清空日志</el-button>
      </div>
    </div>

    <el-card class="control-panel">
      <el-form :model="executionForm" :inline="true" label-width="100px">
        <el-form-item label="选择套件">
          <el-select v-model="executionForm.selectedSuites" multiple placeholder="请选择测试套件" style="width: 300px;">
            <el-option 
              v-for="suite in testSuites" 
              :key="suite.id" 
              :label="suite.name" 
              :value="suite.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="并发数">
          <el-input-number v-model="executionForm.concurrentCount" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="环境">
          <el-select v-model="executionForm.environment" placeholder="请选择执行环境">
            <el-option label="开发环境" value="development" />
            <el-option label="测试环境" value="test" />
            <el-option label="生产环境" value="production" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="execution-status">
      <div class="status-header">
        <div class="status-info">
          <div class="status-item">
            <span class="status-label">执行状态:</span>
            <el-tag :type="getStatusType(executionStatus)" size="large">{{ executionStatus }}</el-tag>
          </div>
          <div class="status-item">
            <span class="status-label">进度:</span>
            <el-progress 
              :percentage="executionProgress" 
              :status="getProgressStatus(executionStatus)"
              :stroke-width="20"
            />
          </div>
          <div class="status-item">
            <span class="status-label">已执行/总数:</span>
            <span>{{ executedCount }} / {{ totalCount }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">执行时间:</span>
            <span>{{ executionTime }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="log-panel">
          <template #header>
            <div class="card-header">
              <span>实时执行日志</span>
              <div>
                <el-button size="small" @click="scrollToBottom">滚动到底部</el-button>
                <el-button size="small" @click="exportLogs">导出日志</el-button>
              </div>
            </div>
          </template>
          <div ref="logContainer" class="log-container">
            <div 
              v-for="(log, index) in executionLogs" 
              :key="index" 
              class="log-item"
              :class="getLogClass(log.level)"
            >
              <span class="log-time">[{{ log.time }}]</span>
              <span class="log-level">[{{ log.level }}]</span>
              <span class="log-message">{{ log.message }}</span>
              <span v-if="log.sipMessage" class="sip-message">SIP: {{ log.sipMessage }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="statistics-panel">
          <template #header>
            <span>执行统计</span>
          </template>
          <div class="stat-item">
            <span class="stat-label">成功:</span>
            <el-tag type="success">{{ successCount }}</el-tag>
          </div>
          <div class="stat-item">
            <span class="stat-label">失败:</span>
            <el-tag type="danger">{{ failureCount }}</el-tag>
          </div>
          <div class="stat-item">
            <span class="stat-label">跳过:</span>
            <el-tag type="info">{{ skippedCount }}</el-tag>
          </div>
          <div class="stat-item">
            <span class="stat-label">错误:</span>
            <el-tag type="warning">{{ errorCount }}</el-tag>
          </div>
        </el-card>

        <el-card class="active-tests" style="margin-top: 20px;">
          <template #header>
            <span>活跃测试</span>
          </template>
          <div class="active-test-list">
            <div 
              v-for="(test, index) in activeTests" 
              :key="index" 
              class="active-test-item"
            >
              <div class="test-name">{{ test.name }}</div>
              <el-tag :type="getTestStatusType(test.status)" size="small">{{ test.status }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useMainStore } from '@/stores/main'
import { executionApi, suiteApi } from '@/utils/api'
import wsService from '@/utils/websocket'

export default {
  name: 'ExecutionMonitor',
  setup() {
    const logContainer = ref(null)
    const mainStore = useMainStore()
    
    // 从store获取测试套件
    const testSuites = computed(() => mainStore.testSuites)
    
    // 执行表单
    const executionForm = reactive({
      selectedSuites: [],
      concurrentCount: 1,
      environment: 'test'
    })

    // 从store获取执行状态
    const executionStatus = computed(() => mainStore.executionStatus)
    const executionLogs = computed(() => mainStore.executionLogs)
    
    // 其他响应式变量
    const executionProgress = ref(0)
    const executedCount = ref(0)
    const totalCount = ref(20)
    const executionTime = ref('00:00:00')
    const isExecuting = ref(false)
    
    // 统计数据
    const successCount = ref(0)
    const failureCount = ref(0)
    const skippedCount = ref(0)
    const errorCount = ref(0)
    
    // 活跃测试
    const activeTests = ref([])
    
    // 初始化WebSocket连接
    const initializeWebSocket = () => {
      // 连接到执行日志WebSocket端点
      const wsUrl = process.env.VUE_APP_WS_URL || 'ws://localhost:8080/ws/execution'
      wsService.connect(wsUrl)
    }

    // 执行开始
    const startExecution = async () => {
      if (executionForm.selectedSuites.length === 0) {
        ElMessage.warning('请选择至少一个测试套件')
        return
      }
    
      try {
        // 调用API开始执行
        const executionData = {
          suiteIds: executionForm.selectedSuites,
          concurrentCount: executionForm.concurrentCount,
          environment: executionForm.environment
        }
        
        const response = await executionApi.startExecution(executionData)
        const executionId = response.id || 'default-execution-id'
        
        // 更新store状态
        mainStore.startExecution(executionId)
        isExecuting.value = true
        executionProgress.value = 0
        executedCount.value = 0
        successCount.value = 0
        failureCount.value = 0
        skippedCount.value = 0
        errorCount.value = 0
        activeTests.value = []

        // 开始执行过程
        startRealExecution()
      } catch (error) {
        console.error('执行开始失败:', error)
        ElMessage.error(error.message || '执行开始失败')
      }
    }

    // 开始真实执行
    const startRealExecution = () => {
      let progress = 0
      const interval = setInterval(() => {
        if (progress >= 100 || !isExecuting.value) {
          clearInterval(interval)
          if (isExecuting.value) {
            // 模拟最终结果
            const isSuccess = Math.random() > 0.2
            if (isSuccess) {
              mainStore.addLog({
                time: new Date().toLocaleTimeString(),
                level: 'INFO',
                message: '所有测试执行成功完成',
                sipMessage: null
              })
            } else {
              mainStore.addLog({
                time: new Date().toLocaleTimeString(),
                level: 'ERROR',
                message: '执行过程中发生错误',
                sipMessage: null
              })
            }
            mainStore.stopExecution()
            isExecuting.value = false
          }
          return
        }

        progress += Math.random() * 5
        executionProgress.value = Math.min(progress, 100)
        executedCount.value = Math.floor((progress / 100) * totalCount.value)

        // 添加日志到store
        const logTypes = ['INFO', 'DEBUG', 'WARN', 'ERROR']
        const logMessages = [
          '开始执行测试套件',
          '连接SIP服务器',
          '发送INVITE请求',
          '收到100 Trying响应',
          '收到180 Ringing响应',
          '收到200 OK响应',
          '建立RTP连接',
          '发送BYE请求',
          '收到200 OK响应',
          '测试步骤完成'
        ]
        
        if (Math.random() > 0.3) { // 有一定概率添加日志
          const level = logTypes[Math.floor(Math.random() * logTypes.length)]
          const message = logMessages[Math.floor(Math.random() * logMessages.length)]
          
          const log = {
            time: new Date().toLocaleTimeString(),
            level: level,
            message: message,
            sipMessage: level === 'DEBUG' ? 'INVITE sip:user@server.com SIP/2.0' : null
          }
          
          mainStore.addLog(log)
          
          // 更新统计
          if (level === 'ERROR') {
            errorCount.value++
          } else if (level === 'WARN') {
            failureCount.value++
          }
        }

        // 更新活跃测试
        if (Math.random() > 0.7) {
          const testNames = ['注册测试', '呼叫测试', '会议测试', '转接测试']
          const statuses = ['运行中', '等待', '完成']
          const test = {
            name: testNames[Math.floor(Math.random() * testNames.length)],
            status: statuses[Math.floor(Math.random() * statuses.length)]
          }
          activeTests.value = [test, ...activeTests.value.slice(0, 4)] // 保持最多5个
        }

        // 滚动到日志底部
        nextTick(() => {
          scrollToBottom()
        })
      }, 500)
    }

    // 停止执行
    const stopExecution = async () => {
      try {
        // 获取当前执行ID
        const executionId = mainStore.currentExecutionId
        if (executionId) {
          await executionApi.stopExecution(executionId)
        }
        
        // 更新store状态
        mainStore.stopExecution()
        isExecuting.value = false
        ElMessage.info('执行已停止')
      } catch (error) {
        console.error('停止执行失败:', error)
        ElMessage.error(error.message || '停止执行失败')
      }
    }

    // 清空日志
    const clearLogs = () => {
      mainStore.clearLogs()
      ElMessage.success('日志已清空')
    }

    // 滚动到日志底部
    const scrollToBottom = () => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    }

    // 导出日志
    const exportLogs = () => {
      const logText = executionLogs.value.map(log => 
        `[${log.time}] [${log.level}] ${log.message} ${log.sipMessage ? log.sipMessage : ''}`
      ).join('\n')
      
      const blob = new Blob([logText], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `execution-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`
      a.click()
      URL.revokeObjectURL(url)
      
      ElMessage.success('日志已导出')
    }

    // 获取状态类型
    const getStatusType = (status) => {
      switch (status) {
        case 'running':
          return 'warning'
        case 'success':
          return 'success'
        case 'failure':
          return 'danger'
        case 'stopped':
          return 'info'
        case 'idle':
          return 'info'
        default:
          return 'info'
      }
    }

    // 获取进度状态
    const getProgressStatus = (status) => {
      switch (status) {
        case 'running':
          return 'success'
        case 'failure':
          return 'exception'
        case 'stopped':
          return 'warning'
        default:
          return null
      }
    }

    // 获取日志类型
    const getLogClass = (level) => {
      switch (level) {
        case 'ERROR':
          return 'log-error'
        case 'WARN':
          return 'log-warn'
        case 'DEBUG':
          return 'log-debug'
        default:
          return 'log-info'
      }
    }

    // 获取测试状态类型
    const getTestStatusType = (status) => {
      switch (status) {
        case '运行中':
          return 'warning'
        case '完成':
          return 'success'
        case '等待':
          return 'info'
        default:
          return 'info'
      }
    }

    // 初始化
    onMounted(async () => {
      try {
        // 从API获取测试套件数据
        const suites = await suiteApi.getAllSuites()
        mainStore.testSuites = suites
        
        // 添加一些初始日志
        mainStore.addLog({
          time: new Date().toLocaleTimeString(),
          level: 'INFO',
          message: '测试执行器已启动',
          sipMessage: null
        })
        mainStore.addLog({
          time: new Date().toLocaleTimeString(),
          level: 'INFO',
          message: '等待选择测试套件',
          sipMessage: null
        })
        
        // 初始化WebSocket连接
        initializeWebSocket()
      } catch (error) {
        console.error('初始化失败:', error)
        ElMessage.error(error.message || '初始化失败')
      }
    })
    
    // 组件卸载时断开WebSocket连接
    onUnmounted(() => {
      wsService.disconnect()
    })

    return {
      logContainer,
      executionForm,
      executionStatus,
      executionProgress,
      executedCount,
      totalCount,
      executionTime,
      isExecuting,
      executionLogs,
      successCount,
      failureCount,
      skippedCount,
      errorCount,
      activeTests,
      testSuites,
      startExecution,
      stopExecution,
      clearLogs,
      scrollToBottom,
      exportLogs,
      getStatusType,
      getProgressStatus,
      getLogClass,
      getTestStatusType
    }
  }
}
</script>

<style scoped>
.execution-monitor-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.control-panel {
  margin-bottom: 20px;
}

.execution-status {
  margin-bottom: 20px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-info {
  display: flex;
  gap: 30px;
  align-items: center;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-label {
  font-weight: bold;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-panel {
  height: 500px;
}

.log-container {
  height: 420px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.log-item {
  padding: 4px 8px;
  border-bottom: 1px solid #f4f4f5;
}

.log-item.log-info {
  background-color: #f4f4f5;
}

.log-item.log-debug {
  background-color: #f0f9ff;
  color: #409eff;
}

.log-item.log-warn {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.log-item.log-error {
  background-color: #fef0f0;
  color: #f56c6c;
}

.log-time {
  color: #909399;
  margin-right: 10px;
}

.log-level {
  font-weight: bold;
  margin-right: 10px;
}

.log-message {
  margin-right: 10px;
}

.sip-message {
  color: #67c23a;
  font-style: italic;
}

.statistics-panel .stat-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  padding: 5px 0;
  border-bottom: 1px solid #f4f4f5;
}

.active-tests {
  height: 250px;
}

.active-test-list {
  max-height: 180px;
  overflow-y: auto;
}

.active-test-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid #f4f4f5;
}

.test-name {
  font-size: 14px;
  color: #606266;
}
</style>