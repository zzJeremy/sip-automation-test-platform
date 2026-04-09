<template>
  <div class="suite-management-container">
    <div class="page-header">
      <h2>测试套件管理</h2>
      <el-button type="primary" @click="openCreateDialog">新建套件</el-button>
    </div>

    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="套件名称">
          <el-input v-model="searchForm.name" placeholder="请输入套件名称" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchSuites">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table 
      :data="suites" 
      v-loading="loading"
      style="width: 100%"
      row-key="id"
    >
      <el-table-column prop="name" label="套件名称" width="200" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="scenarioCount" label="场景数" width="100" />
      <el-table-column prop="lastStatus" label="最后执行状态" width="120">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.lastStatus)">{{ row.lastStatus }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="lastRunTime" label="最后执行时间" width="180" />
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button size="small" @click="runSuite(row)">运行</el-button>
          <el-button size="small" @click="editSuite(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteSuite(row)">删除</el-button>
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

    <!-- 新建/编辑套件对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogTitle"
      width="800px"
      :before-close="closeDialog"
    >
      <el-form :model="currentSuite" :rules="suiteRules" ref="suiteFormRef" label-width="100px">
        <el-form-item label="套件名称" prop="name">
          <el-input v-model="currentSuite.name" placeholder="请输入套件名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input 
            v-model="currentSuite.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入套件描述" 
          />
        </el-form-item>
        <el-form-item label="执行环境">
          <el-select v-model="currentSuite.environment" placeholder="请选择执行环境">
            <el-option label="开发环境" value="development" />
            <el-option label="测试环境" value="test" />
            <el-option label="生产环境" value="production" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <div class="drag-area">
        <h4>拖拽式场景编排</h4>
        <el-row :gutter="20">
          <el-col :span="12">
            <div class="available-scenarios">
              <h5>可用场景</h5>
              <draggable 
                :list="availableScenarios" 
                :group="{ name: 'scenarios', pull: 'clone', put: false }"
                :sort="false"
                item-key="id"
                class="scenario-list"
              >
                <template #item="{ element }">
                  <div class="scenario-item">
                    {{ element.name }}
                  </div>
                </template>
              </draggable>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="selected-scenarios">
              <h5>已选场景</h5>
              <draggable 
                :list="currentSuite.selectedScenarios" 
                :group="{ name: 'scenarios' }"
                item-key="id"
                class="scenario-list"
              >
                <template #item="{ element }">
                  <div class="scenario-item selected">
                    {{ element.name }}
                    <el-button 
                      type="danger" 
                      size="small" 
                      circle 
                      @click="removeScenario(element.id)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </template>
              </draggable>
            </div>
          </el-col>
        </el-row>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeDialog">取消</el-button>
          <el-button type="primary" @click="saveSuite">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import draggable from 'vuedraggable'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { suiteApi } from '@/utils/api'
import { useMainStore } from '@/stores/main'

export default {
  name: 'SuiteManagement',
  components: {
    draggable,
    Delete
  },
  setup() {
    // 数据
    const suites = ref([])
    const loading = ref(false)
    const dialogVisible = ref(false)
    const dialogTitle = ref('')
    const currentSuite = ref({
      id: '',
      name: '',
      description: '',
      environment: '',
      selectedScenarios: []
    })
    const availableScenarios = ref([
      { id: 1, name: 'SIP注册测试场景' },
      { id: 2, name: 'SIP呼叫测试场景' },
      { id: 3, name: 'SIP会议测试场景' },
      { id: 4, name: 'SIP转接测试场景' },
      { id: 5, name: 'SIP IVR测试场景' },
      { id: 6, name: 'SIP认证测试场景' }
    ])
    const suiteFormRef = ref(null)

    // 搜索表单
    const searchForm = reactive({
      name: ''
    })

    // 分页信息
    const pagination = reactive({
      currentPage: 1,
      pageSize: 10,
      total: 0
    })

    // 表单验证规则
    const suiteRules = {
      name: [
        { required: true, message: '请输入套件名称', trigger: 'blur' }
      ]
    }

    // 获取套件列表
    const loadSuites = async () => {
      loading.value = true
      
      try {
        // 从API获取套件列表和统计信息
        const [suitesResponse, statsResponse] = await Promise.all([
          suiteApi.getAllSuites({
            page: pagination.currentPage,
            size: pagination.pageSize,
            name: searchForm.name
          }),
          suiteApi.getSuiteStats().catch(() => ({ total: 0, active: 0, inactive: 0 }))
        ])
        
        suites.value = suitesResponse.data || suitesResponse
        const mainStore = useMainStore()
        mainStore.updateSuiteStats(statsResponse.data || statsResponse)
        pagination.total = suitesResponse.total || suitesResponse.length
      } catch (error) {
        console.error('加载测试套件失败:', error)
        ElMessage.error(error.message || '加载测试套件失败')
      } finally {
        loading.value = false
      }
    }

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

    // 打开新建对话框
    const openCreateDialog = () => {
      dialogTitle.value = '新建测试套件'
      currentSuite.value = {
        id: '',
        name: '',
        description: '',
        environment: '',
        selectedScenarios: []
      }
      dialogVisible.value = true
    }

    // 编辑套件
    const editSuite = (row) => {
      dialogTitle.value = '编辑测试套件'
      currentSuite.value = { ...row }
      // 如果没有selectedScenarios，初始化为空数组
      if (!currentSuite.value.selectedScenarios) {
        currentSuite.value.selectedScenarios = []
      }
      dialogVisible.value = true
    }

    // 运行套件
    const runSuite = (row) => {
      ElMessage.success(`正在运行套件: ${row.name}`)
    }

    // 删除套件
    const deleteSuite = async (row) => {
      ElMessageBox.confirm(
        `确定要删除套件 "${row.name}" 吗？`,
        '确认删除',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        try {
          await suiteApi.deleteSuite(row.id)
          ElMessage.success('删除成功')
          // 重新加载套件列表
          await loadSuites()
        } catch (error) {
          console.error('删除套件失败:', error)
          ElMessage.error(error.message || '删除套件失败')
        }
      }).catch(() => {
        // 用户取消删除
      })
    }

    // 移除已选场景
    const removeScenario = (id) => {
      currentSuite.value.selectedScenarios = currentSuite.value.selectedScenarios.filter(
        scenario => scenario.id !== id
      )
    }

    // 保存套件
    const saveSuite = async () => {
      try {
        if (currentSuite.value.id) {
          // 编辑模式
          await suiteApi.updateSuite(currentSuite.value.id, {
            name: currentSuite.value.name,
            description: currentSuite.value.description,
            environment: currentSuite.value.environment,
            scenarioIds: currentSuite.value.selectedScenarios.map(s => s.id)
          })
          ElMessage.success('更新成功')
        } else {
          // 新建模式
          const newSuite = await suiteApi.createSuite({
            name: currentSuite.value.name,
            description: currentSuite.value.description,
            environment: currentSuite.value.environment,
            scenarioIds: currentSuite.value.selectedScenarios.map(s => s.id)
          })
          ElMessage.success('创建成功')
        }
        
        // 重新加载套件列表
        await loadSuites()
        closeDialog()
      } catch (error) {
        console.error('保存套件失败:', error)
        ElMessage.error(error.message || '保存套件失败')
      }
    }

    // 关闭对话框
    const closeDialog = () => {
      dialogVisible.value = false
    }

    // 搜索套件
    const searchSuites = () => {
      // 重置到第一页再搜索
      pagination.currentPage = 1
      loadSuites()
    }

    // 重置搜索
    const resetSearch = () => {
      searchForm.name = ''
      loadSuites()
    }

    // 分页事件
    const handleSizeChange = (val) => {
      pagination.pageSize = val
      pagination.currentPage = 1  // 切换每页大小时回到第一页
      loadSuites()
    }

    const handleCurrentChange = (val) => {
      pagination.currentPage = val
      loadSuites()
    }

    // 初始化数据
    onMounted(async () => {
      await loadSuites()
    })

    return {
      suites,
      loading,
      dialogVisible,
      dialogTitle,
      currentSuite,
      availableScenarios,
      suiteFormRef,
      searchForm,
      pagination,
      suiteRules,
      getStatusType,
      openCreateDialog,
      editSuite,
      runSuite,
      deleteSuite,
      removeScenario,
      saveSuite,
      closeDialog,
      searchSuites,
      resetSearch,
      handleSizeChange,
      handleCurrentChange
    }
  }
}
</script>

<style scoped>
.suite-management-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.search-card {
  margin-bottom: 20px;
}

.drag-area {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.available-scenarios, .selected-scenarios {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 15px;
  min-height: 300px;
}

.scenario-list {
  min-height: 250px;
  border: 1px dashed #dcdfe6;
  padding: 10px;
  border-radius: 4px;
}

.scenario-item {
  padding: 8px 12px;
  margin: 5px 0;
  background-color: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: move;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.scenario-item.selected {
  background-color: #e6f7ff;
  border-color: #91d5ff;
}

.pagination {
  margin-top: 20px;
  text-align: right;
}
</style>