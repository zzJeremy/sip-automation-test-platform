// websocket.js - WebSocket服务模块
import { useMainStore } from '@/stores/main'

class WebSocketService {
  constructor() {
    this.ws = null
    this.store = useMainStore()
    this.isReconnecting = false
    this.reconnectInterval = 5000 // 重连间隔5秒
    this.maxReconnectAttempts = 5 // 最大重连次数
    this.reconnectAttempts = 0
  }

  // 连接WebSocket
  connect(url) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket已连接')
      return
    }

    try {
      this.ws = new WebSocket(url)
      this.store.connect()

      this.ws.onopen = (event) => {
        console.log('WebSocket连接已建立', event)
        this.reconnectAttempts = 0
        this.isReconnecting = false
        this.store.setConnected()
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (error) {
          console.error('解析WebSocket消息失败:', error)
          // 添加原始消息到日志
          this.store.addLog({
            time: new Date().toLocaleTimeString(),
            level: 'ERROR',
            message: `无法解析消息: ${event.data}`,
            sipMessage: null
          })
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket连接已关闭', event)
        this.store.disconnect()
        this.attemptReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
        this.store.disconnect()
        this.store.addLog({
          time: new Date().toLocaleTimeString(),
          level: 'ERROR',
          message: `WebSocket连接错误: ${error.message}`,
          sipMessage: null
        })
      }
    } catch (error) {
      console.error('创建WebSocket连接失败:', error)
      this.store.disconnect()
      this.store.addLog({
        time: new Date().toLocaleTimeString(),
        level: 'ERROR',
        message: `创建WebSocket连接失败: ${error.message}`,
        sipMessage: null
      })
      this.attemptReconnect()
    }
  }

  // 处理接收到的消息
  handleMessage(data) {
    // 根据消息类型处理不同的数据
    switch (data.type) {
      case 'log':
        // 添加日志到store
        this.store.addLog({
          time: data.timestamp || new Date().toLocaleTimeString(),
          level: data.level || 'INFO',
          message: data.message || '',
          sipMessage: data.sipMessage || null
        })
        break
      case 'executionStatus':
        // 更新执行状态
        this.updateExecutionStatus(data.status)
        break
      case 'progress':
        // 更新执行进度
        this.updateExecutionProgress(data.progress)
        break
      case 'stats':
        // 更新统计信息
        this.updateStatistics(data.stats)
        break
      case 'executionResult':
        // 处理执行结果
        this.handleExecutionResult(data.result)
        break
      case 'executionMetrics':
        // 处理执行指标
        this.handleExecutionMetrics(data.metrics)
        break
      case 'systemNotification':
        // 处理系统通知
        this.handleSystemNotification(data.notification)
        break
      default:
        console.warn('未知的消息类型:', data.type, data)
        break
    }
  }

  // 更新执行状态
  updateExecutionStatus(status) {
    // 根据需要更新store中的执行状态
    if (status === 'completed' || status === 'failed') {
      this.store.stopExecution()
    } else if (status === 'running') {
      this.store.startExecution()
    }
  }

  // 更新执行进度
  updateExecutionProgress(progress) {
    // 在这里可以添加进度更新逻辑
    console.log('执行进度更新:', progress)
  }

  // 更新统计信息
  updateStatistics(stats) {
    // 在这里可以添加统计信息更新逻辑
    console.log('统计信息更新:', stats)
  }

  // 处理执行结果
  handleExecutionResult(result) {
    console.log('处理执行结果:', result)
    // 可以在这里更新store中的测试结果
    if (result && result.id) {
      this.store.addTestResult(result)
    }
  }

  // 处理执行指标
  handleExecutionMetrics(metrics) {
    console.log('处理执行指标:', metrics)
    // 可以在这里更新store中的执行指标
    if (metrics && metrics.progress !== undefined) {
      this.store.updateProgress(metrics.progress)
    }
  }

  // 处理系统通知
  handleSystemNotification(notification) {
    console.log('处理系统通知:', notification)
    // 根据通知类型执行相应操作
    switch(notification.type) {
      case 'info':
        console.info('系统通知:', notification.message)
        break
      case 'warning':
        console.warn('系统警告:', notification.message)
        break
      case 'error':
        console.error('系统错误:', notification.message)
        break
      default:
        console.log('系统通知:', notification.message)
    }
  }

  // 发送消息
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.error('WebSocket未连接，无法发送消息')
      this.store.addLog({
        time: new Date().toLocaleTimeString(),
        level: 'ERROR',
        message: 'WebSocket未连接，无法发送消息',
        sipMessage: null
      })
    }
  }

  // 尝试重连
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts && !this.isReconnecting) {
      this.isReconnecting = true
      this.reconnectAttempts++

      console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)

      setTimeout(() => {
        console.log('正在尝试重新连接...')
        this.connect(process.env.VUE_APP_WS_URL || 'ws://localhost:8080/ws/execution')
        this.isReconnecting = false
      }, this.reconnectInterval)
    } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('达到最大重连次数，停止重连')
      this.store.addLog({
        time: new Date().toLocaleTimeString(),
        level: 'ERROR',
        message: 'WebSocket连接失败，已达到最大重连次数',
        sipMessage: null
      })
    }
  }

  // 断开连接
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.store.disconnect()
    this.reconnectAttempts = 0
    this.isReconnecting = false
  }

  // 检查连接状态
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }

  // 获取连接状态
  getConnectionStatus() {
    if (!this.ws) {
      return 'disconnected'
    }

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'disconnected'
      default:
        return 'unknown'
    }
  }
}

// 创建单例实例
const wsService = new WebSocketService()

export default wsService