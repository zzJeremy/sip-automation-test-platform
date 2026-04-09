<template>
  <div class="report-center-container">
    <div class="page-header">
      <h2>测试报告中心</h2>
    </div>

    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="套件名称">
          <el-select v-model="searchForm.suiteName" placeholder="请选择套件" style="width: 200px;">
            <el-option label="全部" value="" />
            <el-option label="注册业务测试套件" value="注册业务测试套件" />
            <el-option label="呼叫业务测试套件" value="呼叫业务测试套件" />
            <el-option label="会议业务测试套件" value="会议业务测试套件" />
            <el-option label="转接业务测试套件" value="转接业务测试套件" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" style="width: 150px;">
            <el-option label="全部" value="" />
            <el-option label="成功" value="成功" />
            <el-option label="失败" value="失败" />
            <el-option label="进行中" value="进行中" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchReports">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table 
      :data="reports" 
      v-loading="loading"
      style="width: 100%"
      row-key="id"
      @row-click="viewReportDetail"
    >
      <el-table-column prop="id" label="报告ID" width="100" />
      <el-table-column prop="suiteName" label="套件名称" width="200" />
      <el-table-column prop="startTime" label="开始时间" width="180" />
      <el-table-column prop="endTime" label="结束时间" width="180" />
      <el-table-column prop="duration" label="耗时(s)" width="100" />
      <el-table-column prop="total" label="总计" width="80" />
      <el-table-column prop="passed" label="通过" width="80" />
      <el-table-column prop="failed" label="失败" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click.stop="viewReportDetail(row)">查看</el-button>
          <el-button size="small" @click.stop="rerunTest(row)">重跑</el-button>
          <el-dropdown size="small" @command="(command) => handleCommand(command, row)">
            <el-button size="small">
              更多 <el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="export-json">导出JSON</el-dropdown-item>
                <el-dropdown-item command="export-html">导出HTML</el-dropdown-item>
                <el-dropdown-item command="export-pdf">导出PDF</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pagination"
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
      :current-page="pagination.currentPage"
      :page-sizes="[10, 20, 50, 100]"
      :page-size="pagination.pageSize"
      layout="total, sizes, prev, pager, next, jumper"
      :total="pagination.total"
    />

    <!-- 报告详情对话框 -->
    <el-dialog 
      v-model="detailDialogVisible" 
      title="测试报告详情"
      width="90%"
      top="5vh"
      :before-close="closeDetailDialog"
    >
      <div v-if="selectedReport" class="report-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="报告ID">{{ selectedReport.id }}</el-descriptions-item>
          <el-descriptions-item label="套件名称">{{ selectedReport.suiteName }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ selectedReport.startTime }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ selectedReport.endTime }}</el-descriptions-item>
          <el-descriptions-item label="总耗时">{{ selectedReport.duration }}秒</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedReport.status)">{{ selectedReport.status }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-row :gutter="20" class="summary-stats">
          <el-col :span="4">
            <div class="stat-card">
              <div class="stat-value">{{ selectedReport.total }}</div>
              <div class="stat-label">总计</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-card success">
              <div class="stat-value">{{ selectedReport.passed }}</div>
              <div class="stat-label">通过</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-card danger">
              <div class="stat-value">{{ selectedReport.failed }}</div>
              <div class="stat-label">失败</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-card warning">
              <div class="stat-value">{{ selectedReport.skipped }}</div>
              <div class="stat-label">跳过</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-card info">
              <div class="stat-value">{{ selectedReport.error }}</div>
              <div class="stat-label">错误</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-card primary">
              <div class="stat-value">{{ selectedReport.passRate }}%</div>
              <div class="stat-label">通过率</div>
            </div>
          </el-col>
        </el-row>

        <el-tabs v-model="activeTab" class="detail-tabs">
          <el-tab-pane label="场景结果" name="results">
            <el-tree 
              :data="selectedReport.results" 
              :props="treeProps"
              node-key="id"
              default-expand-all
              :expand-on-click-node="false"
            >
              <template #default="{ node, data }">
                <div class="tree-node">
                  <span class="node-type">{{ data.type }}</span>
                  <span class="node-name">{{ data.name }}</span>
                  <el-tag :type="getResultType(data.result)" size="small" style="margin-left: 10px;">
                    {{ data.result }}
                  </el-tag>
                  <span class="node-duration" v-if="data.duration">({{ data.duration }}ms)</span>
                </div>
              </template>
            </el-tree>
          </el-tab-pane>

          <el-tab-pane label="SIP信令" name="signaling">
            <el-timeline>
              <el-timeline-item 
                v-for="(message, index) in selectedReport.signaling" 
                :key="index"
                :timestamp="message.timestamp"
                :color="getMessageColor(message.type)"
              >
                <div class="signaling-message">
                  <div class="message-header">
                    <el-tag :type="getMessageType(message.type)">{{ message.type }}</el-tag>
                    <span class="message-method">{{ message.method }}</span>
                  </div>
                  <div class="message-body">
                    <pre>{{ message.content }}</pre>
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-tab-pane>

          <el-tab-pane label="性能指标" name="performance">
            <div ref="perfChartRef" class="perf-chart" style="height: 400px;"></div>
          </el-tab-pane>

          <el-tab-pane label="日志详情" name="logs">
            <div class="log-container">
              <div 
                v-for="(log, index) in selectedReport.logs" 
                :key="index" 
                class="log-item"
                :class="getLogClass(log.level)"
              >
                <span class="log-time">[{{ log.time }}]</span>
                <span class="log-level">[{{ log.level }}]</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeDetailDialog">关闭</el-button>
          <el-button type="primary" @click="exportReport">导出报告</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { ArrowDown } from '@element-plus/icons-vue'
import { reportApi } from '@/utils/api'
import { useMainStore } from '@/stores/main'

export default {
  name: 'ReportCenter',
  components: {
    ArrowDown
  },
  setup() {
    const perfChartRef = ref(null)
    let chartInstance = null
    
    // 报告列表
    const reports = ref([])
    const loading = ref(false)
    const detailDialogVisible = ref(false)
    const selectedReport = ref(null)
    const activeTab = ref('results')
    
    // 搜索表单
    const searchForm = reactive({
      suiteName: '',
      status: '',
      dateRange: []
    })
    
    // 分页信息
    const pagination = reactive({
      currentPage: 1,
      pageSize: 10,
      total: 0
    })
    
    // 树形控件属性
    const treeProps = {
      children: 'children',
      label: 'name'
    }

    // 加载报告列表
    const loadReports = async () => {
      loading.value = true
      
      try {
        // 从API获取报告列表
        const reportsResponse = await reportApi.getAllReports({
          page: pagination.currentPage,
          size: pagination.pageSize,
          suiteName: searchForm.suiteName,
          status: searchForm.status,
          startDate: searchForm.dateRange ? searchForm.dateRange[0] : null,
          endDate: searchForm.dateRange ? searchForm.dateRange[1] : null
        })
        
        reports.value = reportsResponse.data || reportsResponse
        pagination.total = reportsResponse.total || reportsResponse.length
        
        // 更新store中的报告统计数据
        const mainStore = useMainStore()
        if (reportsResponse.stats) {
          mainStore.updateReportStats(reportsResponse.stats)
        }
      } catch (error) {
        console.error('加载报告失败:', error)
        ElMessage.error(error.message || '加载报告失败')
      } finally {
        loading.value = false
      }
    }

    // 获取状态类型
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

    // 获取结果类型
    const getResultType = (result) => {
      switch (result) {
        case '通过':
          return 'success'
        case '失败':
          return 'danger'
        case '跳过':
          return 'info'
        case '错误':
          return 'warning'
        default:
          return 'info'
      }
    }

    // 获取消息类型
    const getMessageType = (type) => {
      switch (type) {
        case 'Request':
          return 'primary'
        case 'Response':
          return 'success'
        case 'Info':
          return 'info'
        default:
          return 'info'
      }
    }

    // 获取消息颜色
    const getMessageColor = (type) => {
      switch (type) {
        case 'Request':
          return '#409EFF'
        case 'Response':
          return '#67C23A'
        default:
          return '#909399'
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

    // 查看报告详情
    const viewReportDetail = async (row) => {
      try {
        // 从API获取详细的报告信息
        const reportDetail = await reportApi.getReportById(row.id)
        selectedReport.value = reportDetail
      } catch (error) {
        console.error('加载报告详情失败:', error)
        ElMessage.error(error.message || '加载报告详情失败')
        
        // 使用基本的报告信息，但仍然尝试加载详细数据
        selectedReport.value = {
          ...row,
          results: [],
          signaling: [],
          logs: []
        }
      }
      
      detailDialogVisible.value = true
      activeTab.value = 'results'
      
      // 初始化图表
      nextTick(() => {
        initPerformanceChart()
      })
    }

    // 初始化性能图表
    const initPerformanceChart = () => {
      if (perfChartRef.value) {
        chartInstance = echarts.init(perfChartRef.value)
        
        const option = {
          tooltip: {
            trigger: 'axis'
          },
          legend: {
            data: ['响应时间(ms)', '吞吐量(RPS)']
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
            data: ['0s', '10s', '20s', '30s', '40s', '50s', '60s']
          },
          yAxis: [
            {
              type: 'value',
              name: '响应时间',
              position: 'left',
              min: 0,
              max: 1000,
              axisLabel: {
                formatter: '{value} ms'
              }
            },
            {
              type: 'value',
              name: '吞吐量',
              position: 'right',
              min: 0,
              max: 100,
              axisLabel: {
                formatter: '{value} RPS'
              }
            }
          ],
          series: [
            {
              name: '响应时间(ms)',
              type: 'line',
              yAxisIndex: 0,
              data: [200, 350, 280, 420, 300, 250, 310]
            },
            {
              name: '吞吐量(RPS)',
              type: 'line',
              yAxisIndex: 1,
              data: [50, 65, 55, 70, 60, 55, 62]
            }
          ]
        }
        
        chartInstance.setOption(option)
      }
    }

    // 关闭详情对话框
    const closeDetailDialog = () => {
      detailDialogVisible.value = false
      selectedReport.value = null
    }

    // 重跑测试
    const rerunTest = async (row) => {
      ElMessageBox.confirm(
        `确定要重跑测试套件 "${row.suiteName}" 吗？`,
        '确认重跑',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        try {
          // 调用API重跑测试
          const response = await reportApi.rerunTest(row.id)
          ElMessage.success(response.message || '已提交重跑请求')
        } catch (error) {
          console.error('重跑测试失败:', error)
          ElMessage.error(error.message || '重跑测试失败')
        }
      }).catch(() => {
        // 用户取消
      })
    }

    // 处理更多操作
    const handleCommand = (command, row) => {
      switch (command) {
        case 'export-json':
          exportReportData(row, 'json')
          break
        case 'export-html':
          exportReportData(row, 'html')
          break
        case 'export-pdf':
          exportReportData(row, 'pdf')
          break
      }
    }

    // 导出报告数据
    const exportReportData = async (report, format) => {
      try {
        // 根据格式调用不同的导出API
        let response
        switch (format) {
          case 'json':
            response = await reportApi.exportReportJson(report.id)
            break
          case 'html':
            response = await reportApi.exportReportHtml(report.id)
            break
          case 'pdf':
            response = await reportApi.exportReportPdf(report.id)
            break
          default:
            throw new Error('不支持的导出格式')
        }
        
        // 创建下载链接
        const blob = new Blob([response], { type: getExportMimeType(format) })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${report.suiteName}_${report.id}.${format}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        
        ElMessage.success(`${format.toUpperCase()}格式报告导出成功`)
      } catch (error) {
        console.error(`导出${format}格式报告失败:`, error)
        ElMessage.error(error.message || `导出${format}格式报告失败`)
      }
    }

    // 获取导出文件的MIME类型
    const getExportMimeType = (format) => {
      switch (format) {
        case 'json':
          return 'application/json'
        case 'html':
          return 'text/html'
        case 'pdf':
          return 'application/pdf'
        default:
          return 'application/octet-stream'
      }
    }

    // 导出报告
    const exportReport = async () => {
      if (!selectedReport.value) {
        ElMessage.warning('请选择要导出的报告')
        return
      }
      
      try {
        // 导出完整的报告
        const response = await reportApi.exportReport(selectedReport.value.id)
        
        // 创建下载链接
        const blob = new Blob([response], { type: 'application/zip' }) // 假设完整报告是zip格式
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${selectedReport.value.suiteName}_${selectedReport.value.id}_full_report.zip`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        
        ElMessage.success('完整报告导出成功')
      } catch (error) {
        console.error('导出完整报告失败:', error)
        ElMessage.error(error.message || '导出完整报告失败')
      }
    }

    // 搜索报告
    const searchReports = () => {
      // 重置到第一页再搜索
      pagination.currentPage = 1
      loadReports()
    }

    // 重置搜索
    const resetSearch = () => {
      searchForm.suiteName = ''
      searchForm.status = ''
      searchForm.dateRange = []
      // 重置到第一页再搜索
      pagination.currentPage = 1
      loadReports()
    }

    // 分页事件
    const handleSizeChange = (val) => {
      pagination.pageSize = val
      loadReports()
    }

    const handleCurrentChange = (val) => {
      pagination.currentPage = val
      loadReports()
    }

    // 初始化
    onMounted(() => {
      loadReports()
    })

    return {
      perfChartRef,
      reports,
      loading,
      detailDialogVisible,
      selectedReport,
      activeTab,
      searchForm,
      pagination,
      treeProps,
      getStatusType,
      getResultType,
      getMessageType,
      getMessageColor,
      getLogClass,
      viewReportDetail,
      closeDetailDialog,
      rerunTest,
      handleCommand,
      exportReport,
      exportReportData,
      searchReports,
      resetSearch,
      handleSizeChange,
      handleCurrentChange
    }
  }
}
</script>

<style scoped>
.report-center-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.search-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  text-align: right;
}

.report-detail .el-descriptions {
  margin-bottom: 20px;
}

.summary-stats {
  margin: 20px 0;
}

.stat-card {
  text-align: center;
  padding: 15px;
  border-radius: 4px;
  background-color: #f5f7fa;
}

.stat-card.success {
  background-color: #f0f9ff;
  color: #67c23a;
}

.stat-card.danger {
  background-color: #fef0f0;
  color: #f56c6c;
}

.stat-card.warning {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.stat-card.info {
  background-color: #f4f4f5;
  color: #909399;
}

.stat-card.primary {
  background-color: #ecf5ff;
  color: #409eff;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  display: block;
}

.stat-label {
  font-size: 14px;
  margin-top: 5px;
}

.detail-tabs {
  margin-top: 20px;
}

.tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  font-size: 14px;
  padding-right: 8px;
}

.node-type {
  color: #909399;
  margin-right: 8px;
}

.node-name {
  color: #606266;
}

.node-duration {
  color: #909399;
  margin-left: 10px;
}

.signaling-message {
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fafafa;
}

.message-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.message-method {
  margin-left: 10px;
  font-weight: bold;
  color: #606266;
}

.message-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 12px;
  color: #909399;
}

.perf-chart {
  width: 100%;
  height: 100%;
}

.log-container {
  height: 400px;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background-color: #2d2d2d;
  color: #fff;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.log-item {
  padding: 4px 8px;
  border-bottom: 1px solid #4a4a4a;
}

.log-item.log-info {
  color: #f8f8f2;
}

.log-item.log-debug {
  color: #66d9ef;
}

.log-item.log-warn {
  color: #fd971f;
}

.log-item.log-error {
  color: #f92672;
}

.log-time {
  color: #75715e;
  margin-right: 10px;
}

.log-level {
  font-weight: bold;
  margin-right: 10px;
}

.log-message {
  margin-right: 10px;
}
</style>