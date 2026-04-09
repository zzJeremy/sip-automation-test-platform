<template>
  <div class="test-case-browser-container">
    <div class="page-header">
      <h2>测试用例浏览器</h2>
      <div class="header-actions">
        <el-button type="primary" @click="refreshTestCases">刷新</el-button>
        <el-button @click="runSelectedTest">执行选中测试</el-button>
      </div>
    </div>

    <el-card class="browser-card">
      <el-tabs v-model="activeCategory" type="card">
        <el-tab-pane 
          v-for="(tests, category) in categorizedTests" 
          :key="category" 
          :label="getCategoryLabel(category)" 
          :name="category"
        >
          <el-table
            :data="tests"
            style="width: 100%"
            @selection-change="handleSelectionChange"
            row-key="id"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="name" label="测试用例名称" width="200" />
            <el-table-column prop="description" label="描述" min-width="300" />
            <el-table-column prop="type" label="类型" width="120">
              <template #default="{ row }">
                <el-tag :type="getTypeType(row.type)">
                  {{ getTypeLabel(row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button size="small" @click="viewDetails(row)">详情</el-button>
                <el-button size="small" type="primary" @click="runSingleTest(row)">执行</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 测试用例详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="测试用例详情" width="60%">
      <div v-if="selectedTestCase">
        <h4>{{ selectedTestCase.name }}</h4>
        <p><strong>描述:</strong> {{ selectedTestCase.description }}</p>
        <p><strong>类型:</strong> 
          <el-tag :type="getTypeType(selectedTestCase.type)">
            {{ getTypeLabel(selectedTestCase.type) }}
          </el-tag>
        </p>
        <p><strong>分类:</strong> {{ getCategoryLabel(selectedTestCase.category) }}</p>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="runSingleTest(selectedTestCase)">执行此测试</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 执行配置对话框 -->
    <el-dialog v-model="configDialogVisible" title="测试执行配置" width="50%">
      <el-form :model="testConfig" label-width="120px">
        <el-form-item label="服务器主机">
          <el-input v-model="testConfig.server_host" placeholder="如: 192.168.30.66" />
        </el-form-item>
        <el-form-item label="服务器端口">
          <el-input v-model.number="testConfig.server_port" placeholder="如: 5060" />
        </el-form-item>
        <el-form-item label="主叫号码">
          <el-input v-model="testConfig.caller_uri" placeholder="如: sip:670491@192.168.30.66:5060" />
        </el-form-item>
        <el-form-item label="被叫号码">
          <el-input v-model="testConfig.callee_uri" placeholder="如: sip:670492@192.168.30.66:5060" />
        </el-form-item>
        <el-form-item label="前转目标">
          <el-input v-model="testConfig.forward_to_uri" placeholder="如: sip:670493@192.168.30.66:5060" />
        </el-form-item>
        <el-form-item label="认证用户名">
          <el-input v-model="testConfig.proxy_username" placeholder="如: 670491" />
        </el-form-item>
        <el-form-item label="认证密码">
          <el-input v-model="testConfig.proxy_password" type="password" placeholder="如: 1234" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="configDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmExecuteTest">确认执行</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { testCaseApi } from '@/utils/api'

export default {
  name: 'TestCaseBrowser',
  setup() {
    const categorizedTests = ref({})
    const activeCategory = ref('')
    const multipleSelection = ref([])
    const detailDialogVisible = ref(false)
    const configDialogVisible = ref(false)
    const selectedTestCase = ref(null)
    const testConfig = reactive({
      server_host: '192.168.30.66',
      server_port: 5060,
      caller_uri: 'sip:670491@192.168.30.66:5060',
      callee_uri: 'sip:670492@192.168.30.66:5060',
      forward_to_uri: 'sip:670493@192.168.30.66:5060',
      proxy_username: '670491',
      proxy_password: '1234'
    })

    // 获取测试用例分类
    const loadTestCases = async () => {
      try {
        const response = await testCaseApi.getTestBrowser()
        categorizedTests.value = response.categories
        activeCategory.value = Object.keys(response.categories)[0] || ''
      } catch (error) {
        ElMessage.error('加载测试用例失败: ' + error.message)
      }
    }

    // 刷新测试用例
    const refreshTestCases = () => {
      loadTestCases()
    }

    // 选择变化处理
    const handleSelectionChange = (val) => {
      multipleSelection.value = val
    }

    // 查看详情
    const viewDetails = (testCase) => {
      selectedTestCase.value = testCase
      detailDialogVisible.value = true
    }

    // 执行选中的测试
    const runSelectedTest = () => {
      if (multipleSelection.value.length === 0) {
        ElMessage.warning('请至少选择一个测试用例')
        return
      }
      
      if (multipleSelection.value.length > 1) {
        ElMessage.warning('目前只支持执行单个测试用例，请选择一个测试用例')
        return
      }
      
      selectedTestCase.value = multipleSelection.value[0]
      configDialogVisible.value = true
    }

    // 执行单个测试
    const runSingleTest = (testCase) => {
      selectedTestCase.value = testCase
      configDialogVisible.value = true
    }

    // 确认执行测试
    const confirmExecuteTest = async () => {
      if (!selectedTestCase.value) {
        ElMessage.error('没有选择测试用例')
        return
      }

      try {
        ElMessage.info('正在执行测试...')
        const response = await testCaseApi.executeTestCase(selectedTestCase.value.id, testConfig)
        
        if (response.status === 'success') {
          ElMessage.success(`测试执行成功: ${response.result.name}`)
          console.log('测试结果:', response.result)
        } else {
          ElMessage.error(`测试执行失败: ${response.message}`)
        }
      } catch (error) {
        ElMessage.error('执行测试用例失败: ' + error.message)
      } finally {
        configDialogVisible.value = false
      }
    }

    // 获取类型标签文本
    const getTypeLabel = (type) => {
      const labels = {
        'functional': '功能测试',
        'validation': '验证测试',
        'business': '业务测试',
        'performance': '性能测试'
      }
      return labels[type] || type
    }

    // 获取类型样式
    const getTypeType = (type) => {
      const types = {
        'functional': 'success',
        'validation': 'info',
        'business': 'warning',
        'performance': 'danger'
      }
      return types[type] || 'default'
    }

    // 获取分类标签文本
    const getCategoryLabel = (category) => {
      const labels = {
        'basic': '基础功能',
        'protocol': '协议验证',
        'advanced': '高级业务',
        'performance': '性能测试'
      }
      return labels[category] || category
    }

    onMounted(() => {
      loadTestCases()
    })

    return {
      categorizedTests,
      activeCategory,
      multipleSelection,
      detailDialogVisible,
      configDialogVisible,
      selectedTestCase,
      testConfig,
      loadTestCases,
      refreshTestCases,
      handleSelectionChange,
      viewDetails,
      runSelectedTest,
      runSingleTest,
      confirmExecuteTest,
      getTypeLabel,
      getTypeType,
      getCategoryLabel
    }
  }
}
</script>

<style scoped>
.test-case-browser-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.browser-card {
  margin-top: 20px;
}

.param-row {
  display: flex;
  margin-bottom: 5px;
}

.dialog-footer {
  text-align: right;
}
</style>