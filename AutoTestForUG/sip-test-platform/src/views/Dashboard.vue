<template>
  <div class="dashboard-container">
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalExecutions }}</div>
              <div class="stat-label">总执行次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-icon success">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.successRate }}%</div>
              <div class="stat-label">成功率</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-icon danger">
              <el-icon><CircleClose /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.failureRate }}%</div>
              <div class="stat-label">失败率</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-icon average">
              <el-icon><Timer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.avgDuration }}s</div>
              <div class="stat-label">平均耗时</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-row">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <span>最近7天测试趋势</span>
          </template>
          <div ref="trendChartRef" class="chart-container" style="height: 400px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="quick-actions-card">
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" size="large" icon="VideoPlay" @click="runQuickTest">
              快速执行测试
            </el-button>
            <el-button type="success" size="large" icon="EditPen" @click="createNewSuite">
              创建新套件
            </el-button>
          </div>
        </el-card>
        <el-card class="recent-tests-card" style="margin-top: 20px;">
          <template #header>
            <span>最新测试记录</span>
          </template>
          <el-table :data="recentTests" style="width: 100%" :show-header="false">
            <el-table-column prop="suiteName" label="套件名称"></el-table-column>
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { 
  Document, 
  CircleCheck, 
  CircleClose, 
  Timer, 
  VideoPlay, 
  EditPen 
} from '@element-plus/icons-vue'
import { dashboardApi } from '@/utils/api'
import { ElMessage } from 'element-plus'
import { useMainStore } from '@/stores/main'

export default {
  name: 'Dashboard',
  components: {
    Document,
    CircleCheck,
    CircleClose,
    Timer,
    VideoPlay,
    EditPen
  },
  setup() {
    const trendChartRef = ref(null)
    let chartInstance = null

    // 统计数据
    const stats = ref({
      totalExecutions: 0,
      successRate: 0,
      failureRate: 0,
      avgDuration: 0
    })

    // 最近测试记录
    const recentTests = ref([])

    // 获取状态标签类型
    const getStatusType = (status) => {
      switch (status) {
        case '成功':
          return 'success'
        case '失败':
          return 'danger'
        case '进行中':
          return 'warning'
        default:
          return 'info'
      }
    }

    // 加载仪表板数据
    const loadDashboardData = async () => {
      try {
        // 获取统计信息
        const statsResponse = await dashboardApi.getStats()
        stats.value = statsResponse.data || statsResponse
        
        // 获取最近测试记录
        const recentTestsResponse = await dashboardApi.getRecentTests()
        recentTests.value = recentTestsResponse.data || recentTestsResponse
        
        // 更新store中的统计信息
        const mainStore = useMainStore()
        mainStore.updateSuiteStats(stats.value)
      } catch (error) {
        console.error('加载仪表板数据失败:', error)
        ElMessage.error(error.message || '加载仪表板数据失败')
      }
    }

    // 运行快速测试
    const runQuickTest = async () => {
      try {
        const response = await dashboardApi.runQuickTest()
        ElMessage.success(response.message || '快速测试已启动')
      } catch (error) {
        console.error('启动快速测试失败:', error)
        ElMessage.error(error.message || '启动快速测试失败')
      }
    }

    // 创建新套件
    const createNewSuite = () => {
      // 导航到套件创建页面
      window.location.hash = '#/suite-management'
    }

    // 初始化图表
    onMounted(async () => {
      // 加载数据
      await loadDashboardData()
      
      if (trendChartRef.value) {
        chartInstance = echarts.init(trendChartRef.value)
        
        // 获取趋势数据
        try {
          const trendData = await dashboardApi.getTrendData()
          const option = {
            tooltip: {
              trigger: 'axis'
            },
            legend: {
              data: ['成功', '失败']
            },
            grid: {
              left: '3%',
              right: '4%',
              bottom: '3%',
              containLabel: true
            },
            xAxis: {
              type: 'category',
              boundaryGap: false,
              data: trendData.labels || ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            },
            yAxis: {
              type: 'value'
            },
            series: [
              {
                name: '成功',
                type: 'line',
                stack: '总量',
                data: trendData.successData || [12, 11, 13, 10, 15, 12, 14]
              },
              {
                name: '失败',
                type: 'line',
                stack: '总量',
                data: trendData.failureData || [1, 2, 1, 3, 0, 1, 2]
              }
            ]
          }
          
          chartInstance.setOption(option)
        } catch (error) {
          console.error('加载趋势数据失败:', error)
          ElMessage.error(error.message || '加载趋势数据失败')
          
          // 使用默认数据
          const option = {
            tooltip: {
              trigger: 'axis'
            },
            legend: {
              data: ['成功', '失败']
            },
            grid: {
              left: '3%',
              right: '4%',
              bottom: '3%',
              containLabel: true
            },
            xAxis: {
              type: 'category',
              boundaryGap: false,
              data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            },
            yAxis: {
              type: 'value'
            },
            series: [
              {
                name: '成功',
                type: 'line',
                stack: '总量',
                data: [12, 11, 13, 10, 15, 12, 14]
              },
              {
                name: '失败',
                type: 'line',
                stack: '总量',
                data: [1, 2, 1, 3, 0, 1, 2]
              }
            ]
          }
          
          chartInstance.setOption(option)
        }
      }
    })

    return {
      trendChartRef,
      stats,
      recentTests,
      getStatusType,
      runQuickTest,
      createNewSuite
    }
  }
}
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  height: 100px;
}

.stat-item {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: #f0f9ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.stat-icon.success {
  background-color: #f0f9ff;
  color: #67c23a;
}

.stat-icon.danger {
  background-color: #fef0f0;
  color: #f56c6c;
}

.stat-icon.average {
  background-color: #f4f4f5;
  color: #909399;
}

.stat-icon .el-icon {
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.charts-row {
  margin-bottom: 20px;
}

.chart-card {
  height: 460px;
}

.quick-actions-card {
  height: 200px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.recent-tests-card {
  height: 250px;
}

.chart-container {
  width: 100%;
  height: 100%;
}
</style>