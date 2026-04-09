<template>
  <div class="scenario-editor-container">
    <div class="page-header">
      <h2>测试场景编辑器</h2>
      <div class="header-actions">
        <el-button type="primary" @click="saveScenario">保存</el-button>
        <el-button @click="previewScenario">预览</el-button>
        <el-button @click="toggleMode">{{ isVisualMode ? '切换到代码模式' : '切换到可视化模式' }}</el-button>
      </div>
    </div>

    <el-card class="editor-card">
      <el-form :model="scenarioForm" :rules="scenarioRules" ref="scenarioFormRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="场景名称" prop="name">
              <el-input v-model="scenarioForm.name" placeholder="请输入场景名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="描述" prop="description">
              <el-input v-model="scenarioForm.description" placeholder="请输入场景描述" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="客户端类型">
              <el-select v-model="scenarioForm.clientType" placeholder="请选择客户端类型">
                <el-option label="Socket" value="socket" />
                <el-option label="PJSIP" value="pjsip" />
                <el-option label="SIPp" value="sipp" />
                <el-option label="Asterisk" value="asterisk" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-select v-model="scenarioForm.priority" placeholder="请选择优先级">
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <div class="mode-toggle">
        <el-radio-group v-model="currentTab" size="small">
          <el-radio-button label="visual">可视化编辑</el-radio-button>
          <el-radio-button label="code">代码编辑</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 可视化编辑器 -->
      <div v-if="currentTab === 'visual'" class="visual-editor">
        <div class="step-toolbar">
          <el-button type="primary" @click="addStep">添加步骤</el-button>
          <el-button @click="clearSteps">清空</el-button>
        </div>

        <el-table 
          :data="scenarioForm.steps" 
          style="width: 100%"
          row-key="id"
          :empty-text="'暂无测试步骤，请点击上方按钮添加'"
        >
          <el-table-column prop="stepNumber" label="序号" width="80" />
          <el-table-column prop="keyword" label="关键字" width="200">
            <template #default="{ row, $index }">
              <el-select 
                v-model="row.keyword" 
                placeholder="选择关键字"
                @change="onKeywordChange($index)"
              >
                <el-option 
                  v-for="kw in keywords" 
                  :key="kw.value" 
                  :label="kw.label" 
                  :value="kw.value" 
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="参数" min-width="300">
            <template #default="{ row }">
              <div v-for="(param, idx) in row.parameters" :key="idx" class="param-row">
                <el-input 
                  v-model="param.name" 
                  placeholder="参数名" 
                  style="width: 120px; margin-right: 10px;"
                />
                <el-input 
                  v-model="param.value" 
                  :placeholder="getPlaceholder(row.keyword, param.name)" 
                  style="flex: 1;"
                />
              </div>
              <el-button 
                type="text" 
                size="small" 
                @click="addParameter(row)"
                style="margin-top: 5px;"
              >
                + 添加参数
              </el-button>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row, $index }">
              <el-button size="small" @click="moveUp($index)" :disabled="$index === 0">上移</el-button>
              <el-button size="small" @click="moveDown($index)" :disabled="$index === scenarioForm.steps.length - 1">下移</el-button>
              <el-button size="small" type="danger" @click="removeStep($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="step-preview">
          <h4>实时预览</h4>
          <div class="preview-content">
            <div v-for="(step, index) in scenarioForm.steps" :key="step.id" class="preview-step">
              <span class="step-index">{{ index + 1 }}.</span>
              <span class="step-keyword">{{ getKeywordLabel(step.keyword) }}</span>
              <span class="step-params">
                <span v-for="(param, idx) in step.parameters" :key="idx">
                  {{ param.name }}={{ param.value }}{{ idx < step.parameters.length - 1 ? ', ' : '' }}
                </span>
              </span>
            </div>
            <div v-if="scenarioForm.steps.length === 0" class="no-steps">
              暂无测试步骤，请添加步骤
            </div>
          </div>
        </div>
      </div>

      <!-- 代码编辑器 -->
      <div v-if="currentTab === 'code'" class="code-editor">
        <div class="editor-wrapper">
          <div ref="monacoContainer" class="editor-container"></div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as monaco from 'monaco-editor'
import { scenarioApi } from '@/utils/api'
import { useMainStore } from '@/stores/main'

export default {
  name: 'ScenarioEditor',
  setup() {
    const scenarioFormRef = ref(null)
    const currentTab = ref('visual') // visual or code
    const monacoContainer = ref(null)
    let editor = null

    // 场景表单数据
    const scenarioForm = reactive({
      id: '',
      name: '',
      description: '',
      clientType: '',
      priority: 'medium',
      steps: []
    })

    // 关键字定义
    const keywords = [
      { value: 'make_sip_call', label: '发起SIP呼叫' },
      { value: 'wait_for_answer', label: '等待接听' },
      { value: 'send_dtmf', label: '发送DTMF' },
      { value: 'hang_up', label: '挂断通话' },
      { value: 'register_sip', label: 'SIP注册' },
      { value: 'unregister_sip', label: 'SIP注销' },
      { value: 'send_message', label: '发送消息' },
      { value: 'wait_for_response', label: '等待响应' },
      { value: 'validate_response', label: '验证响应' },
      { value: 'wait_for_time', label: '等待时间' },
      // 添加高级业务功能关键词
      { value: 'setup_unconditional_forward', label: '设置无条件前转' },
      { value: 'setup_busy_forward', label: '设置遇忙前转' },
      { value: 'setup_noanswer_forward', label: '设置无应答前转' },
      { value: 'setup_conference_call', label: '设置会议呼叫' },
      { value: 'add_participant', label: '添加会议参与者' },
      { value: 'remove_participant', label: '移除会议参与者' },
      { value: 'setup_call_waiting', label: '设置呼叫等待' },
      { value: 'setup_call_transfer', label: '设置呼叫转移' },
      { value: 'setup_secretary_service', label: '设置秘书服务' },
      { value: 'setup_hotline', label: '设置热线' },
      { value: 'setup_outbound_restriction', label: '设置呼出限制' },
      { value: 'setup_do_not_disturb', label: '设置免打扰' },
      { value: 'setup_designated_answer', label: '设置指定代答' },
      { value: 'setup_multi_party_call', label: '设置多方通话' },
      { value: 'setup_abbreviated_dialing', label: '设置缩位拨号' }
    ]

    // 表单验证规则
    const scenarioRules = {
      name: [
        { required: true, message: '请输入场景名称', trigger: 'blur' }
      ]
    }

    // 添加步骤
    const addStep = () => {
      const newStep = {
        id: Date.now(),
        stepNumber: scenarioForm.steps.length + 1,
        keyword: '',
        parameters: []
      }
      scenarioForm.steps.push(newStep)
    }

    // 删除步骤
    const removeStep = (index) => {
      scenarioForm.steps.splice(index, 1)
      updateStepNumbers()
    }

    // 上移步骤
    const moveUp = (index) => {
      if (index === 0) return
      swapSteps(index, index - 1)
    }

    // 下移步骤
    const moveDown = (index) => {
      if (index === scenarioForm.steps.length - 1) return
      swapSteps(index, index + 1)
    }

    // 交换步骤
    const swapSteps = (fromIndex, toIndex) => {
      [scenarioForm.steps[fromIndex], scenarioForm.steps[toIndex]] = 
      [scenarioForm.steps[toIndex], scenarioForm.steps[fromIndex]]
      updateStepNumbers()
    }

    // 更新步骤编号
    const updateStepNumbers = () => {
      scenarioForm.steps.forEach((step, index) => {
        step.stepNumber = index + 1
      })
    }

    // 添加参数
    const addParameter = (step) => {
      step.parameters.push({ name: '', value: '' })
    }

    // 关键字变化处理
    const onKeywordChange = (index) => {
      const step = scenarioForm.steps[index]
      // 根据关键字设置默认参数
      step.parameters = []
      
      switch (step.keyword) {
        case 'make_sip_call':
          step.parameters.push({ name: 'callee', value: '' })
          step.parameters.push({ name: 'caller', value: '' })
          break
        case 'register_sip':
          step.parameters.push({ name: 'username', value: '' })
          step.parameters.push({ name: 'password', value: '' })
          step.parameters.push({ name: 'server', value: '' })
          break
        case 'send_dtmf':
          step.parameters.push({ name: 'digits', value: '' })
          break
        case 'wait_for_time':
          step.parameters.push({ name: 'seconds', value: '5' })
          break
      }
    }

    // 获取关键字标签
    const getKeywordLabel = (keyword) => {
      const kw = keywords.find(k => k.value === keyword)
      return kw ? kw.label : keyword
    }

    // 获取参数占位符
    const getPlaceholder = (keyword, paramName) => {
      const placeholders = {
        'callee': '被叫号码',
        'caller': '主叫号码',
        'username': '用户名',
        'password': '密码',
        'server': '服务器地址',
        'digits': '数字序列',
        'seconds': '秒数'
      }
      
      return placeholders[paramName] || paramName
    }

    // 清空步骤
    const clearSteps = () => {
      scenarioForm.steps = []
    }

    // 保存场景
    const saveScenario = async () => {
      try {
        if (scenarioForm.id) {
          // 编辑模式
          await scenarioApi.updateScenario(scenarioForm.id, {
            name: scenarioForm.name,
            description: scenarioForm.description,
            clientType: scenarioForm.clientType,
            priority: scenarioForm.priority,
            steps: scenarioForm.steps
          })
          ElMessage.success('场景更新成功')
        } else {
          // 新建模式
          const newScenario = await scenarioApi.createScenario({
            name: scenarioForm.name,
            description: scenarioForm.description,
            clientType: scenarioForm.clientType,
            priority: scenarioForm.priority,
            steps: scenarioForm.steps
          })
          scenarioForm.id = newScenario.id || 'new'
          ElMessage.success('场景创建成功')
        }
        
        // 更新store中的场景数据
        const mainStore = useMainStore()
        if (scenarioForm.id) {
          mainStore.addScenario(scenarioForm)
        }
      } catch (error) {
        console.error('保存场景失败:', error)
        ElMessage.error(error.message || '保存场景失败')
      }
    }

    // 预览场景
    const previewScenario = () => {
      ElMessage.info('预览功能开发中...')
    }

    // 切换模式
    const toggleMode = () => {
      currentTab.value = currentTab.value === 'visual' ? 'code' : 'visual'
    }

    // 初始化Monaco编辑器
    const initMonacoEditor = async () => {
      await nextTick()
      
      if (monacoContainer.value) {
        editor = monaco.editor.create(monacoContainer.value, {
          value: `# SIP测试场景定义
name: "SIP呼叫测试"
description: "测试基本SIP呼叫功能"
client_type: "socket"
priority: "medium"

steps:
  - action: "register_sip"
    params:
      username: "test_user"
      password: "test_pass"
      server: "192.168.1.100"
  
  - action: "make_sip_call"
    params:
      caller: "1001"
      callee: "1002"
  
  - action: "wait_for_answer"
    params:
      timeout: 30
  
  - action: "hang_up"
    params:
      reason: "normal"
`,
          language: 'yaml',
          theme: 'vs-dark',
          minimap: { enabled: true },
          automaticLayout: true
        })
      }
    }

    // 监听当前选项卡变化，初始化编辑器
    watch(currentTab, (newVal) => {
      if (newVal === 'code') {
        nextTick(() => {
          if (!editor && monacoContainer.value) {
            initMonacoEditor()
          }
        })
      }
    })

    // 初始化数据
    onMounted(async () => {
      // 如果有场景ID，则从API加载场景数据
      const urlParams = new URLSearchParams(window.location.search)
      const scenarioId = urlParams.get('id')
      
      if (scenarioId) {
        try {
          scenarioForm.id = scenarioId
          const scenarioData = await scenarioApi.getScenarioById(scenarioId)
          Object.assign(scenarioForm, scenarioData)
        } catch (error) {
          console.error('加载场景数据失败:', error)
          ElMessage.error('加载场景数据失败')
        }
      } else {
        // 添加一个示例步骤
        scenarioForm.steps.push({
          id: Date.now(),
          stepNumber: 1,
          keyword: 'register_sip',
          parameters: [
            { name: 'username', value: 'test_user' },
            { name: 'password', value: 'test_pass' },
            { name: 'server', value: '192.168.1.100' }
          ]
        })
      }
    })

    return {
      scenarioFormRef,
      currentTab,
      monacoContainer,
      scenarioForm,
      keywords,
      scenarioRules,
      addStep,
      removeStep,
      moveUp,
      moveDown,
      addParameter,
      onKeywordChange,
      getKeywordLabel,
      getPlaceholder,
      clearSteps,
      saveScenario,
      previewScenario,
      toggleMode
    }
  }
}
</script>

<style scoped>
.scenario-editor-container {
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

.editor-card {
  min-height: 600px;
}

.mode-toggle {
  margin: 20px 0;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.visual-editor {
  padding-top: 10px;
}

.step-toolbar {
  margin-bottom: 20px;
}

.param-row {
  display: flex;
  margin-bottom: 5px;
}

.step-preview {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.preview-content {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  min-height: 100px;
  max-height: 300px;
  overflow-y: auto;
}

.preview-step {
  margin-bottom: 10px;
  padding: 8px;
  background-color: white;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.step-index {
  font-weight: bold;
  color: #606266;
  margin-right: 10px;
}

.step-keyword {
  color: #409eff;
  font-weight: bold;
  margin-right: 10px;
}

.step-params {
  color: #909399;
}

.no-steps {
  text-align: center;
  color: #909399;
  padding: 20px;
}

.code-editor {
  height: 500px;
}

.editor-wrapper {
  height: 100%;
}

.editor-container {
  width: 100%;
  height: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}
</style>