<!-- src/components/AutoPredict.vue -->
<template>
  <div 
    class="autopredict-container power-predict-container" 
    v-loading="loading" 
    element-loading-text="加载中，请稍候..."
    :class="{'animated-background': isAnimatedBackground.value, 'static-background': !isAnimatedBackground.value}"
  >
    <h1 class="page-title">风电功率自动化预测功能管理</h1>
    <div class="hero-section">
      <div class="global-buttons">
        <el-button type="primary" @click="showConfirmDialog('saveSettings', '保存PM2配置', '确定要保存当前PM2配置吗？此操作将覆盖之前保存的配置。')">保存配置</el-button>
        <el-button type="primary" @click="showConfirmDialog('resurrectConfig', '加载PM2配置', '确定要加载已保存的PM2配置吗？此操作可能会影响当前运行的任务。')">加载配置</el-button>
        <el-button type="danger" @click="showConfirmDialog('clearSavedConfig', '删除已保存配置', '确定要删除已保存的PM2配置吗？此操作不可恢复。')">删除已保存配置</el-button>
        <el-button type="info" @click="openHistoryDialog">历史记录</el-button>
      </div>
      <el-row :gutter="24">
        <el-col :span="8" v-for="(item, index) in predictions" :key="index">
          <el-card class="prediction-card">
            <template #header>
              <span>{{ item.title }}</span>
            </template>
            <div class="button-group">
              <el-button 
                :type="item.status ? 'success' : 'primary'" 
                @click="showConfirmDialog('startTask', '启用预测任务', `确定要启用${item.title}吗？`, item.name)"
                :disabled="item.status"
              >
                {{ item.status ? '运行中' : '启用' }}
              </el-button>
              
              <el-button 
                type="danger" 
                @click="showConfirmDialog('stopTask', '停止预测任务', `确定要停止${item.title}吗？此操作会中断当前预测。`, item.name)"
                :disabled="!item.status"
              >
                停止
              </el-button>
              
              <el-button 
                type="warning" 
                @click="showScheduleDialog(item.name)"
              >
                定时重启
              </el-button>
            </div>
            <div class="button-group extra">
              <el-button type="danger" @click="showConfirmDialog('deleteTask', '删除预测任务', `确定要从PM2中删除${item.title}吗？此操作不会删除脚本文件，但会移除任务记录。`, item.name)">删除</el-button>
              <el-button type="info" @click="fetchScriptInfo(item.name)">详情</el-button>
              <el-button type="primary" @click="fetchLogs(item.name)">日志</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 操作确认对话框 -->
    <el-dialog 
      :title="confirmDialog.title" 
      v-model="confirmDialog.visible" 
      width="30%"
    >
      <p>{{ confirmDialog.message }}</p>
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button type="primary" @click="executeConfirmedAction">确定</el-button>
          <el-button @click="confirmDialog.visible = false">取消</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 定时重启设置对话框 -->
    <el-dialog 
      title="设置定时重启" 
      v-model="scheduleDialogVisible" 
      width="30%"
    >
      <el-time-picker
        v-model="scheduleTime"
        placeholder="选择每日重启时间"
        format="HH:mm"
        value-format="HH:mm"
      />
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button type="primary" @click="setSchedule">确定</el-button>
          <el-button @click="scheduleDialogVisible = false">取消</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 脚本详情对话框 -->
    <el-dialog 
      title="脚本详情" 
      v-model="scriptInfoDialogVisible" 
      width="80%"
    >
      <pre class="info-content">{{ scriptInfo }}</pre>
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button @click="scriptInfoDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 脚本日志对话框 -->
    <el-dialog 
      title="脚本日志" 
      v-model="logsDialogVisible" 
      width="80%"
    >
      <pre class="logs-content">{{ logsContent }}</pre>
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button type="primary" @click="fetchLogs(currentPrediction)">刷新</el-button>
          <el-button @click="logsDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 错误详情对话框 -->
    <el-dialog 
      :title="errorTitle"
      v-model="errorDialogVisible" 
      width="50%"
    >
      <pre class="error-content">{{ errorDetails }}</pre>
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button @click="errorDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 任务历史记录对话框 -->
    <el-dialog 
      title="任务历史记录" 
      v-model="historyDialogVisible" 
      width="80%"
    >
      <div class="history-filters">
        <el-form :inline="true">
          <el-form-item label="任务类型">
            <el-select v-model="historyFilters.taskType" placeholder="选择任务类型" clearable>
              <el-option label="超短期" value="ultra_short"></el-option>
              <el-option label="短期" value="short"></el-option>
              <el-option label="中期" value="medium"></el-option>
              <el-option label="全部" value="all"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="操作类型">
            <el-select v-model="historyFilters.action" placeholder="选择操作类型" clearable>
              <el-option label="启动" value="start"></el-option>
              <el-option label="停止" value="stop"></el-option>
              <el-option label="删除" value="delete"></el-option>
              <el-option label="定时重启" value="schedule"></el-option>
              <el-option label="保存配置" value="save"></el-option>
              <el-option label="加载配置" value="resurrect"></el-option>
              <el-option label="删除配置" value="clearsave"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchTaskHistory">查询</el-button>
            <el-button @click="resetHistoryFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table :data="historyRecords" style="width: 100%" border stripe>
        <el-table-column prop="created_at" label="时间" width="180"></el-table-column>
        <el-table-column prop="task_type" label="任务类型" width="120">
          <template #default="scope">
            <el-tag :type="getTaskTypeTagType(scope.row.task_type)">
              {{ getTaskTypeLabel(scope.row.task_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="操作" width="120">
          <template #default="scope">
            <el-tag :type="getActionTagType(scope.row.action)">
              {{ getActionLabel(scope.row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ getStatusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="details" label="详情">
          <template #default="scope">
            <el-button 
              v-if="scope.row.details" 
              type="text" 
              @click="showHistoryDetail(scope.row)"
            >
              查看详情
            </el-button>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          background
          layout="prev, pager, next, sizes, total"
          :page-sizes="[10, 20, 50, 100]"
          :page-size="historyPagination.pageSize"
          :current-page="historyPagination.currentPage"
          :total="historyPagination.total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        >
        </el-pagination>
      </div>
    </el-dialog>

    <!-- 历史记录详情对话框 -->
    <el-dialog 
      title="历史记录详情" 
      v-model="historyDetailDialogVisible" 
      width="50%"
      append-to-body
    >
      <pre class="history-detail-content">{{ historyDetailContent }}</pre>
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button @click="historyDetailDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, inject, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const isAnimatedBackground = inject('isAnimatedBackground');

const predictions = reactive([
  {
    name: 'ultra_short',
    title: '超短期风电功率预测',
    status: false
  },
  {
    name: 'short',
    title: '短期风电功率预测',
    status: false
  },
  {
    name: 'medium',
    title: '中期风电功率预测',
    status: false
  }
])

// loading 状态，用于页面加载时显示提示框
const loading = ref(true)

// 定时重启相关变量
const scheduleDialogVisible = ref(false)
const scheduleTime = ref('')
let currentPrediction = ''

// 脚本详情与日志相关变量
const scriptInfoDialogVisible = ref(false)
const scriptInfo = ref('')
const logsDialogVisible = ref(false)
const logsContent = ref('')

// 错误处理相关变量
const errorDialogVisible = ref(false)
const errorDetails = ref('')
const errorTitle = ref('操作失败')

// 操作确认对话框相关变量
const confirmDialog = reactive({
  visible: false,
  title: '',
  message: '',
  action: '',
  params: null
})

// 任务历史记录相关变量
const historyDialogVisible = ref(false)
const historyRecords = ref([])
const historyFilters = reactive({
  taskType: '',
  action: ''
})
const historyPagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})
const historyDetailDialogVisible = ref(false)
const historyDetailContent = ref('')

// 轮询间隔(毫秒)
const POLLING_INTERVAL = 60000
let intervalId = null

onMounted(() => {
  fetchStatus()
  // 设置定时刷新状态
  intervalId = setInterval(fetchStatus, POLLING_INTERVAL)
})

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
})

// 显示错误对话框
const showErrorDialog = (title, details) => {
  errorTitle.value = title || '操作失败'
  errorDetails.value = typeof details === 'object' ? JSON.stringify(details, null, 2) : String(details)
  errorDialogVisible.value = true
}

// 创建axios实例并添加拦截器
const apiClient = axios.create({
  timeout: 30000 // 30秒超时
})

// 添加响应拦截器处理所有请求的错误
apiClient.interceptors.response.use(
  response => {
    // 检查是否有警告消息，有则显示警告而不是错误
    if (response.data && response.data.warning) {
      ElMessage.warning(response.data.warning)
    }
    return response
  },
  error => {
    console.error('API请求出错:', error)
    
    // 构建错误详情
    let errorMessage = '请求失败'
    let errorDetails = {}
    
    if (error.response) {
      // 服务器返回了错误状态码
      errorMessage = `服务器返回错误 (${error.response.status})`
      errorDetails = {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data
      }
    } else if (error.request) {
      // 请求发送成功，但没有收到响应
      errorMessage = '服务器无响应'
      errorDetails = {
        message: '请求已发送，但未收到服务器响应',
        request: error.request
      }
    } else {
      // 请求配置出错
      errorMessage = '请求配置错误'
      errorDetails = {
        message: error.message
      }
    }
    
    // 特殊处理PM2相关错误
    if (errorDetails.data && errorDetails.data.error && errorDetails.data.error.includes('PM2')) {
      errorMessage = 'PM2服务错误'
    }
    
    // 对用户显示简短错误信息
    ElMessage.error(errorMessage)
    
    // 将详细错误信息记录到控制台
    console.error('详细错误:', errorDetails)
    
    return Promise.reject(error)
  }
)

// 获取初始状态
const fetchStatus = async () => {
  loading.value = true
  try {
    const res = await apiClient.get('/api/status')
    predictions.forEach(p => {
      p.status = res.data[p.name] || false
    })
  } catch (error) {
    console.error('获取状态失败:', error)
    // 这里不显示ElMessage，因为已在拦截器处理
  } finally {
    loading.value = false
  }
}

// 显示操作确认对话框
const showConfirmDialog = (action, title, message, params = null) => {
  confirmDialog.action = action
  confirmDialog.title = title
  confirmDialog.message = message
  confirmDialog.params = params
  confirmDialog.visible = true
}

// 执行确认的操作
const executeConfirmedAction = () => {
  confirmDialog.visible = false
  
  switch (confirmDialog.action) {
    case 'startTask':
      handleControl(confirmDialog.params, 'start')
      break
    case 'stopTask':
      handleControl(confirmDialog.params, 'stop')
      break
    case 'deleteTask':
      handleControl(confirmDialog.params, 'delete')
      break
    case 'saveSettings':
      saveSettings()
      break
    case 'resurrectConfig':
      resurrectConfig()
      break
    case 'clearSavedConfig':
      clearSavedConfig()
      break
    default:
      console.warn('未知操作:', confirmDialog.action)
  }
}

// 处理控制按钮（包含 start, stop, delete 操作）
const handleControl = async (name, action) => {
  console.log('handleControl invoked', name, action)
  loading.value = true
  try {
    const res = await apiClient.post(`/api/${action}`, { type: name })
    
    // 检查是否有警告消息
    if (res.data.warning) {
      ElMessage.warning(res.data.warning)
    } else {
      ElMessage.success(res.data.message || '操作成功')
    }
    
    // 操作完成后延迟一秒再刷新状态，让PM2有时间更新
    setTimeout(async () => {
      await fetchStatus()
    }, 1000)
  } catch (error) {
    // 尝试提取更详细的错误信息
    if (error.response && error.response.data) {
      const errorData = error.response.data
      showErrorDialog(
        `${action} ${name} 失败`, 
        errorData.details || errorData.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 显示定时对话框
const showScheduleDialog = (name) => {
  currentPrediction = name
  scheduleDialogVisible.value = true
}

// 设置定时重启
const setSchedule = async () => {
  if (!scheduleTime.value) {
    ElMessage.warning('请选择时间')
    return
  }
  
  loading.value = true
  try {
    const res = await apiClient.post('/api/schedule', {
      type: currentPrediction,
      time: scheduleTime.value
    })
    ElMessage.success(res.data.message || '定时设置成功')
    scheduleDialogVisible.value = false
    setTimeout(async () => {
      await fetchStatus()
    }, 1000)
  } catch (error) {
    if (error.response && error.response.data) {
      showErrorDialog(
        '设置定时重启失败', 
        error.response.data.details || error.response.data.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 保存 PM2 配置（全局）
const saveSettings = async () => {
  loading.value = true
  try {
    const res = await apiClient.post('/api/save')
    ElMessage.success(res.data.message || 'PM2 配置已保存')
  } catch (error) {
    if (error.response && error.response.data) {
      showErrorDialog(
        '保存配置失败', 
        error.response.data.details || error.response.data.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 加载 PM2 已保存的配置
const resurrectConfig = async () => {
  loading.value = true
  try {
    const res = await apiClient.post('/api/resurrect')
    
    // 检查是否有警告消息
    if (res.data.warning) {
      ElMessage.warning(res.data.warning || '加载配置成功，但状态可能不准确')
    } else {
      ElMessage.success(res.data.message || '配置加载成功')
    }
    
    // 无论是否有警告，都刷新状态
    setTimeout(async () => {
      await fetchStatus() // 更新状态
    }, 1000)
  } catch (error) {
    console.error('加载配置失败:', error)
    if (error.response && error.response.data) {
      showErrorDialog(
        '恢复配置失败', 
        error.response.data.details || error.response.data.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 删除已保存的PM2配置
const clearSavedConfig = async () => {
  loading.value = true
  try {
    const res = await apiClient.post('/api/clearsave')
    ElMessage.success(res.data.message || 'PM2 保存的配置已删除')
  } catch (error) {
    if (error.response && error.response.data) {
      showErrorDialog(
        '删除保存配置失败', 
        error.response.data.details || error.response.data.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 查询脚本详情
const fetchScriptInfo = async (name) => {
  loading.value = true
  try {
    const res = await apiClient.get('/api/script_info', { params: { type: name }})
    
    // 检查是否有警告消息
    if (res.data.warning) {
      ElMessage.warning(res.data.warning)
    }
    
    scriptInfo.value = res.data.info || '暂无详情信息'
    scriptInfoDialogVisible.value = true
  } catch (error) {
    console.error('查询脚本详情失败:', error)
    if (error.response && error.response.data) {
      showErrorDialog(
        '查询脚本详情失败', 
        error.response.data.details || error.response.data.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 获取脚本日志
const fetchLogs = async (name) => {
  currentPrediction = name
  loading.value = true
  try {
    const res = await apiClient.get('/api/logs', { params: { type: name, lines: 100 } })
    logsContent.value = res.data.logs || '暂无日志信息'
    logsDialogVisible.value = true
  } catch (error) {
    console.error('获取日志失败:', error)
    if (error.response && error.response.data) {
      showErrorDialog(
        '获取日志失败', 
        error.response.data.details || error.response.data.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 打开历史记录对话框
const openHistoryDialog = () => {
  historyDialogVisible.value = true
  fetchTaskHistory()
}

// 获取任务历史记录
const fetchTaskHistory = async () => {
  loading.value = true
  try {
    const params = {
      limit: historyPagination.pageSize,
      offset: (historyPagination.currentPage - 1) * historyPagination.pageSize
    }
    
    if (historyFilters.taskType && historyFilters.taskType !== 'all') {
      params.type = historyFilters.taskType
    }
    
    if (historyFilters.action) {
      params.action = historyFilters.action
    }
    
    const res = await apiClient.get('/api/history', { params })
    historyRecords.value = res.data.data || []
    historyPagination.total = res.data.total || 0
    
  } catch (error) {
    console.error('获取历史记录失败:', error)
    if (error.response && error.response.data) {
      showErrorDialog(
        '获取历史记录失败', 
        error.response.data.details || error.response.data.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 重置历史记录筛选条件
const resetHistoryFilters = () => {
  historyFilters.taskType = ''
  historyFilters.action = ''
  historyPagination.currentPage = 1
  fetchTaskHistory()
}

// 分页大小变化处理
const handleSizeChange = (size) => {
  historyPagination.pageSize = size
  fetchTaskHistory()
}

// 当前页变化处理
const handleCurrentChange = (page) => {
  historyPagination.currentPage = page
  fetchTaskHistory()
}

// 显示历史记录详情
const showHistoryDetail = (row) => {
  historyDetailContent.value = row.details || '无详细信息'
  historyDetailDialogVisible.value = true
}

// 获取任务类型标签类型
const getTaskTypeTagType = (taskType) => {
  const typeMap = {
    'ultra_short': 'success',
    'short': 'warning',
    'medium': 'danger',
    'all': 'info'
  }
  return typeMap[taskType] || 'info'
}

// 获取任务类型标签文本
const getTaskTypeLabel = (taskType) => {
  const labelMap = {
    'ultra_short': '超短期',
    'short': '短期',
    'medium': '中期',
    'all': '全部'
  }
  return labelMap[taskType] || taskType
}

// 获取操作类型标签类型
const getActionTagType = (action) => {
  const typeMap = {
    'start': 'success',
    'stop': 'danger',
    'delete': 'danger',
    'schedule': 'warning',
    'save': 'info',
    'resurrect': 'primary',
    'clearsave': 'danger',
    'script_info': 'info',
    'logs': 'info'
  }
  return typeMap[action] || 'info'
}

// 获取操作类型标签文本
const getActionLabel = (action) => {
  const labelMap = {
    'start': '启动',
    'stop': '停止',
    'delete': '删除',
    'schedule': '定时重启',
    'save': '保存配置',
    'resurrect': '加载配置',
    'clearsave': '删除配置',
    'script_info': '查看详情',
    'logs': '查看日志'
  }
  return labelMap[action] || action
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    'success': 'success',
    'failed': 'danger',
    'warning': 'warning'
  }
  return typeMap[status] || 'info'
}

// 获取状态标签文本
const getStatusLabel = (status) => {
  const labelMap = {
    'success': '成功',
    'failed': '失败',
    'warning': '警告'
  }
  return labelMap[status] || status
}
</script>

<style scoped>
.autopredict-container {
  min-height: 100vh;
  padding: 40px;
  position: relative;
  z-index: 1;
}

.power-predict-container {
  min-height: 100vh;
  background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
  background-size: 400% 400%;
  animation: gradient 15s ease infinite;
  position: relative;
}

@keyframes gradient {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

.page-title {
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 添加 Hero Section 样式 */
.hero-section {
  text-align: center;
  padding: 60px 20px;
  position: relative;
}

.hero-section::before {
  content: "✨";
  position: absolute;
  top: 0;
  left: 0;
  font-size: 24px;
  opacity: 0.7;
}

.hero-section::after {
  content: "✨";
  position: absolute;
  bottom: 0;
  right: 0;
  font-size: 24px;
  opacity: 0.7;
}

.autopredict-container h2 {
  font-size: 48px;
  font-weight: 600;
  margin-bottom: 40px;
  text-align: center;
  color: #1d1d1f;
  letter-spacing: -0.003em;
  line-height: 1.1;
}

.global-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 24px;
}

/* 按钮基础样式 */
.el-button {
  height: 40px;  /* 统一按钮高度 */
  padding: 0 20px;
  font-size: 15px;
  font-weight: 500;
  border-radius: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  letter-spacing: -0.01em;
  border: none;
  min-width: 100px; /* 设置最小宽度确保按钮大小一致 */
}

/* 主要操作按钮（启用、保存配置等） */
.el-button--primary {
  background: #0071e3;
  color: #ffffff;
}

.el-button--primary:hover {
  background: #0077ed;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 113, 227, 0.12);
}

/* 成功状态按钮（运行中） */
.el-button--success {
  background: #34c759;
  color: #ffffff;
}

.el-button--success:hover {
  background: #30b753;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(52, 199, 89, 0.12);
}

/* 危险操作按钮（停止、删除） */
.el-button--danger {
  background: #ff3b30;
  color: #ffffff;
}

.el-button--danger:hover {
  background: #ff291e;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(255, 59, 48, 0.12);
}

/* 警告按钮（定时重启） */
.el-button--warning {
  background: #ff9500;
  color: #ffffff;
}

.el-button--warning:hover {
  background: #ff8500;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(255, 149, 0, 0.12);
}

/* 信息按钮（详情） */
.el-button--info {
  background: #8e8e93;
  color: #ffffff;
}

.el-button--info:hover {
  background: #7c7c82;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(142, 142, 147, 0.12);
}

/* 禁用状态 */
.el-button.is-disabled,
.el-button.is-disabled:hover {
  background: #e5e5ea;
  color: #8e8e93;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 按钮组样式调整 */
.button-group {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  justify-content: center;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 0;
}

.button-group .el-button {
  width: 100%;
  justify-content: center;
  min-width: 80px;
}

.el-row {
  margin: 24px -16px;
}

.el-col {
  padding: 0 16px;
  margin-bottom: 24px;
}

.el-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid #f0f0f0;
  border-radius: 20px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  padding: 16px;
}

.el-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}

.prediction-card {
  padding: 30px;
  border: none;
}

.prediction-card :deep(.el-card__header) {
  padding: 0 0 20px 0;
  border-bottom: 1px solid #f2f2f2;
}

.prediction-card :deep(.el-card__header span) {
  font-size: 24px;
  font-weight: 500;
  color: #1d1d1f;
}

.el-dialog {
  border-radius: 20px;
  overflow: hidden;
  transform: none !important;
  margin: 0 auto !important;
  position: relative;
  max-width: 90%;
  /* 确保对话框垂直居中 */
  top: 50%;
  margin-top: 0 !important;
}

:deep(.el-overlay-dialog) {
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
}

.el-dialog :deep(.el-dialog__header) {
  padding: 24px;
  margin: 0;
  background: #f5f5f7;
}

.el-dialog :deep(.el-dialog__title) {
  font-size: 20px;
  font-weight: 500;
  color: #1d1d1f;
}

.el-dialog :deep(.el-dialog__body) {
  padding: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.el-dialog :deep(.el-dialog__body p) {
  margin: 0;
  text-align: center;
  width: 100%;
}

.el-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px 24px;
  text-align: center;
}

.dialog-footer-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  width: 100%;
}

.dialog-footer-buttons .el-button {
  margin-left: 0;
  flex: 0 0 auto;
  min-width: 100px;
}

.info-content, .logs-content, .error-content, .history-detail-content {
  max-height: 600px;
  overflow-y: auto;
  background: #fafafa;
  padding: 24px;
  border-radius: 12px;
  font-family: "SF Mono", Monaco, Menlo, Consolas, monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #1d1d1f;
}

.history-filters {
  margin-bottom: 24px;
}

.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .autopredict-container {
    padding: 20px;
  }

  .autopredict-container h2 {
    font-size: 32px;
  }

  .el-button {
    height: 40px;
    padding: 0 20px;
    font-size: 14px;
  }

  .el-row {
    gap: 16px;  /* 移动端减少间距 */
    margin: 0 10px;  /* 移动端减少两侧留白 */
  }
  
  .el-col {
    margin-bottom: 16px;  /* 移动端减少底部间距 */
  }
  
  .global-buttons {
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
}
</style>