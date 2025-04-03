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
              <template v-if="item.name === 'ultra_short'">
                <el-button 
                  :type="item.status ? 'success' : 'primary'" 
                  @click="showUltraStartDialog()"
                  :disabled="item.status"
                >
                  {{ item.status ? '运行中' : '启用' }}
                </el-button>
              </template>
              <template v-else>
                <el-button 
                  :type="item.status ? 'success' : 'primary'" 
                  @click="showConfirmDialog('startTask', '启用预测任务', `确定要启用${item.title}吗？`, item.name)"
                  :disabled="item.status"
                >
                  {{ item.status ? '运行中' : '启用' }}
                </el-button>
              </template>
              
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

    <!-- 超短期预测启动对话框 -->
    <el-dialog 
      title="启动超短期预测" 
      v-model="ultraStartDialogVisible" 
      width="30%"
    >
      <div class="ultra-start-options">
        <p>超短期预测包含两个独立的脚本，您可以选择启动的脚本：</p>
        <el-checkbox v-model="ultraStartOptions.training" label="训练脚本 (scheduler_supershort.py)">
          负责每日模型训练和每周参数优化
        </el-checkbox>
        <el-checkbox v-model="ultraStartOptions.prediction" label="预测脚本 (scheduler_predict.py)">
          负责每15分钟执行一次预测
        </el-checkbox>
      </div>
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button type="primary" @click="startUltraShortTask" :disabled="!canStartUltraShort">确定</el-button>
          <el-button @click="ultraStartDialogVisible = false">取消</el-button>
        </div>
      </template>
    </el-dialog>

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
      title="任务详情" 
      v-model="scriptInfoDialogVisible" 
      width="80%"
    >
      <div class="task-info-container">
        <div class="task-date-selector">
          <el-form :inline="true">
            <el-form-item label="查询日期">
              <el-date-picker
                v-model="taskDateInfo.selectedDate"
                type="date"
                placeholder="选择日期"
                format="YYYY-MM-DD"
                value-format="YYYYMMDD"
                style="min-width: 180px;"
                @change="fetchTaskStatusByDate"
              ></el-date-picker>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="fetchTaskStatusByDate">查询</el-button>
              <el-button @click="resetTaskDateInfo">今天</el-button>
            </el-form-item>
          </el-form>
        </div>
        
        <h3 class="task-info-title">{{ getTaskTitle(currentPrediction) }}任务状态 ({{ taskDateInfo.displayDate }})</h3>
        
        <div class="task-status-cards">
          <el-card class="task-status-card">
            <template #header>
              <div class="task-card-header">
                <span>每日训练任务</span>
                <el-tag :type="taskStatus.training ? 'success' : 'danger'">
                  {{ taskStatus.training ? '已完成' : '未完成' }}
                </el-tag>
              </div>
            </template>
            <div class="task-card-content">
              <p>执行时间: 每天 02:00</p>
              <p v-if="taskStatus.trainingTime">上次完成: {{ taskStatus.trainingTime }}</p>
            </div>
          </el-card>
          
          <el-card class="task-status-card">
            <template #header>
              <div class="task-card-header">
                <span>预测任务</span>
                <el-tag :type="getTaskPredictionType(taskStatus)">
                  {{ getTaskPredictionStatus(taskStatus) }}
                </el-tag>
              </div>
            </template>
            <div class="task-card-content">
              <div v-if="currentPrediction === 'ultra_short'">
                <p>执行频率: 每15分钟一次 (共96次/天)</p>
                <p>今日完成: {{ taskStatus.predictionCount || 0 }}/96</p>
              </div>
              <p v-else>执行频率: 每天一次</p>
              <p v-if="taskStatus.predictionTime">上次执行: {{ taskStatus.predictionTime }}</p>
            </div>
          </el-card>
          
          <el-card class="task-status-card">
            <template #header>
              <div class="task-card-header">
                <span>参数优化任务</span>
                <el-tag :type="taskStatus.paramOpt ? 'success' : 'danger'">
                  {{ taskStatus.paramOpt ? '已完成' : '未完成' }}
                </el-tag>
              </div>
            </template>
            <div class="task-card-content">
              <p>执行时间: {{ getParamOptWeekday(currentPrediction) }} 01:00</p>
              <p v-if="taskStatus.paramOptTime">上次完成: {{ taskStatus.paramOptTime }}</p>
            </div>
          </el-card>
        </div>
        
        <div class="script-info-section">
          <h4>脚本详情</h4>
          <pre class="info-content">{{ scriptInfo }}</pre>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button type="primary" @click="refreshTaskStatus">刷新状态</el-button>
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
      <div class="logs-filters">
        <el-form :inline="true">
          <el-form-item label="日志类型">
            <el-select v-model="logsFilters.logType" placeholder="选择日志类型" @change="handleLogTypeChange" style="min-width: 180px;">
              <el-option v-for="option in getLogTypeOptions()" :key="option.value" :label="option.label" :value="option.value"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="日期">
            <el-date-picker
              v-model="logsFilters.date"
              type="date"
              placeholder="选择日期"
              format="YYYY-MM-DD"
              value-format="YYYYMMDD"
              style="min-width: 180px;"
            ></el-date-picker>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchLogsByFilter">查询</el-button>
            <el-button @click="resetLogsFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      <pre class="logs-content">{{ logsContent }}</pre>
      <template #footer>
        <div class="dialog-footer-buttons">
          <el-button type="primary" @click="fetchLogsByFilter">刷新</el-button>
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
            <el-select v-model="historyFilters.taskType" placeholder="选择任务类型" clearable style="min-width: 180px;">
              <el-option label="超短期" value="ultra_short"></el-option>
              <el-option label="短期" value="short"></el-option>
              <el-option label="中期" value="medium"></el-option>
              <el-option label="全部" value="all"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="操作类型">
            <el-select v-model="historyFilters.action" placeholder="选择操作类型" clearable style="min-width: 180px;">
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
import { ref, reactive, inject, onMounted, onUnmounted, computed } from 'vue'
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
const logsFilters = reactive({
  logType: '',
  date: ''
})

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

// 详情相关变量
const taskStatus = reactive({
  training: false,
  prediction: false,
  paramOpt: false,
  trainingTime: '',
  predictionTime: '',
  paramOptTime: '',
  predictionCount: 0,
  predictionCompleted: false
})

const taskDateInfo = reactive({
  selectedDate: new Date().toISOString().slice(0, 10).replace(/-/g, ''),
  displayDate: '今天'
})

// 轮询间隔(毫秒)
const POLLING_INTERVAL = 60000
let intervalId = null

// 超短期预测启动相关
const ultraStartDialogVisible = ref(false)
const ultraStartOptions = reactive({
  training: true,
  prediction: true
})

// 计算属性：是否可以启动超短期预测
const canStartUltraShort = computed(() => {
  return ultraStartOptions.training || ultraStartOptions.prediction
})

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
  currentPrediction = name
  loading.value = true
  try {
    const res = await apiClient.get('/api/script_info', { params: { type: name }})
    
    // 检查是否有警告消息
    if (res.data.warning) {
      ElMessage.warning(res.data.warning)
    }
    
    scriptInfo.value = res.data.info || '暂无详情信息'
    
    // 获取任务状态
    await fetchTaskStatus(name)
    
    // 设置当前日期显示
    taskDateInfo.selectedDate = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    taskDateInfo.displayDate = '今天'
    
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

// 获取任务状态
const fetchTaskStatus = async (name) => {
  try {
    // 获取参数优化的执行周期
    const paramOptDay = getParamOptDay(name);
    
    const params = {
      type: name,
      date: taskDateInfo.selectedDate,
      param_opt_day: paramOptDay // 添加参数优化天数参数
    }
    
    const res = await apiClient.get('/api/task_status', { params })
    
    // 更新任务状态
    if (res.data.status) {
      taskStatus.training = res.data.status.training || false
      taskStatus.prediction = res.data.status.prediction || false
      taskStatus.paramOpt = res.data.status.paramOpt || false
      taskStatus.trainingTime = res.data.status.trainingTime || ''
      taskStatus.predictionTime = res.data.status.predictionTime || ''
      taskStatus.paramOptTime = res.data.status.paramOptTime || ''
      taskStatus.predictionCount = res.data.status.predictionCount || 0
      taskStatus.predictionCompleted = res.data.status.predictionCompleted || false
    } else {
      // 如果后端没有返回 status 对象，重置所有状态为 false
      taskStatus.training = false
      taskStatus.prediction = false
      taskStatus.paramOpt = false
      taskStatus.trainingTime = ''
      taskStatus.predictionTime = ''
      taskStatus.paramOptTime = ''
      taskStatus.predictionCount = 0
      taskStatus.predictionCompleted = false
    }
  } catch (error) {
    console.error('获取任务状态失败:', error)
    ElMessage.warning('获取任务状态失败，请检查后端服务')
  }
}

// 刷新任务状态
const refreshTaskStatus = async () => {
  loading.value = true
  try {
    await fetchTaskStatus(currentPrediction)
    ElMessage.success('任务状态已刷新')
  } catch (error) {
    console.error('刷新任务状态失败:', error)
  } finally {
    loading.value = false
  }
}

// 按日期查询任务状态
const fetchTaskStatusByDate = async () => {
  loading.value = true
  try {
    if (!taskDateInfo.selectedDate) {
      taskDateInfo.selectedDate = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    }
    
    // 设置显示日期
    const selectedDate = taskDateInfo.selectedDate
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10).replace(/-/g, '')
    
    if (selectedDate === today) {
      taskDateInfo.displayDate = '今天'
    } else if (selectedDate === yesterday) {
      taskDateInfo.displayDate = '昨天'
    } else {
      // 格式化为 YYYY-MM-DD
      taskDateInfo.displayDate = `${selectedDate.slice(0, 4)}-${selectedDate.slice(4, 6)}-${selectedDate.slice(6, 8)}`
    }
    
    await fetchTaskStatus(currentPrediction)
    ElMessage.success(`已查询${taskDateInfo.displayDate}的任务状态`)
  } catch (error) {
    console.error('按日期查询任务状态失败:', error)
    ElMessage.warning('查询失败，请重试')
  } finally {
    loading.value = false
  }
}

// 重置任务日期信息
const resetTaskDateInfo = () => {
  taskDateInfo.selectedDate = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  taskDateInfo.displayDate = '今天'
  fetchTaskStatus(currentPrediction)
}

// 获取任务标题
const getTaskTitle = (taskType) => {
  const titleMap = {
    'ultra_short': '超短期',
    'short': '短期',
    'medium': '中期'
  }
  return titleMap[taskType] || taskType
}

// 获取脚本日志
const fetchLogs = async (name) => {
  currentPrediction = name
  logsDialogVisible.value = true
  // 初始化日志过滤条件
  logsFilters.logType = 'train'
  logsFilters.date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  // 加载日志
  fetchLogsByFilter()
}

// 根据过滤条件获取日志
const fetchLogsByFilter = async () => {
  loading.value = true
  try {
    const params = {
      type: currentPrediction,
      logType: logsFilters.logType || 'train',
      date: logsFilters.date || new Date().toISOString().slice(0, 10).replace(/-/g, ''),
      lines: 500
    }
    
    // 如果是参数优化日志，添加参数优化日
    if (logsFilters.logType === 'param') {
      params.param_opt_day = getParamOptDay(currentPrediction)
    }
    
    const res = await apiClient.get('/api/logs', { params })
    logsContent.value = res.data.logs || '暂无日志信息'
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

// 重置日志过滤条件
const resetLogsFilters = () => {
  logsFilters.logType = 'train'
  logsFilters.date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  fetchLogsByFilter()
}

// 根据预测类型获取日志类型选项
const getLogTypeOptions = () => {
  // 超短期预测有4种日志类型
  if (currentPrediction === 'ultra_short') {
    return [
      { label: '主日志', value: 'main' },
      { label: '训练日志', value: 'train' },
      { label: '预测日志', value: 'predict' },
      { label: '参数优化日志', value: 'param' }
    ]
  }
  // 短期和中期预测只有2种日志类型
  return [
    { label: '训练日志', value: 'train' },
    { label: '参数优化日志', value: 'param' }
  ]
}

// 日志类型变更处理
const handleLogTypeChange = () => {
  fetchLogsByFilter()
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

// 显示超短期启动对话框
const showUltraStartDialog = () => {
  // 重置选项
  ultraStartOptions.training = true
  ultraStartOptions.prediction = true
  ultraStartDialogVisible.value = true
}

// 启动超短期预测任务
const startUltraShortTask = async () => {
  ultraStartDialogVisible.value = false
  loading.value = true
  
  try {
    const params = {
      type: 'ultra_short',
      options: ultraStartOptions
    }
    
    const res = await apiClient.post('/api/start_ultra', params)
    
    ElMessage.success(res.data.message || '超短期预测任务启动成功')
    
    // 刷新状态
    setTimeout(async () => {
      await fetchStatus()
    }, 1000)
  } catch (error) {
    if (error.response && error.response.data) {
      showErrorDialog(
        '启动超短期预测失败', 
        error.response.data.details || error.response.data.error || error.message
      )
    }
  } finally {
    loading.value = false
  }
}

// 获取参数优化执行的星期
const getParamOptWeekday = (taskType) => {
  // 首先尝试从脚本详情中提取实际配置的参数优化星期
  // 如果脚本详情中包含相关信息，则使用实际配置值
  if (scriptInfo.value) {
    try {
      // 针对不同任务类型查找不同的关键词
      let searchTerm = '';
      if (taskType === 'ultra_short') {
        searchTerm = '超短期参数优化';
      } else if (taskType === 'short') {
        searchTerm = '短期参数优化';
      } else if (taskType === 'medium') {
        searchTerm = '中期参数优化';
      }
      
      // 查找包含关键词的行
      if (searchTerm && scriptInfo.value.includes(searchTerm)) {
        const lines = scriptInfo.value.split('\n');
        for (const line of lines) {
          if (line.includes(searchTerm) && line.includes('每周')) {
            // 从行中提取星期几
            if (line.includes('每周一')) return '每周一';
            if (line.includes('每周二')) return '每周二';
            if (line.includes('每周三')) return '每周三';
            if (line.includes('每周四')) return '每周四';
            if (line.includes('每周五')) return '每周五';
            if (line.includes('每周六')) return '每周六';
            if (line.includes('每周日')) return '每周日';
          }
        }
      }
    } catch (e) {
      console.error('解析脚本信息失败:', e);
    }
  }
  
  // 如果无法从脚本详情中提取，则使用默认配置
  const weekdayMap = {
    'ultra_short': '每周六',
    'short': '每周五',
    'medium': '每周四'
  }
  return weekdayMap[taskType] || '每周六';
}

// 获取参数优化日(周几)，返回0-6的数字，对应周一到周日
const getParamOptDay = (taskType) => {
  // 先从getParamOptWeekday获取参数优化的星期几
  const weekdayStr = getParamOptWeekday(taskType);
  
  // 将中文星期几转换为数字(0-6)
  const weekdayMap = {
    '每周一': 0,
    '每周二': 1,
    '每周三': 2,
    '每周四': 3,
    '每周五': 4,
    '每周六': 5,
    '每周日': 6
  };
  
  return weekdayMap[weekdayStr] !== undefined ? weekdayMap[weekdayStr] : 
         (taskType === 'ultra_short' ? 5 : // 默认超短期是周六
          taskType === 'short' ? 4 :       // 默认短期是周五
          taskType === 'medium' ? 3 : 5);  // 默认中期是周四，其他默认周六
}

// 获取预测任务的状态类型
const getTaskPredictionType = (taskStatus) => {
  // 如果是超短期预测
  if (currentPrediction === 'ultra_short') {
    if (taskStatus.predictionCount >= 96) {
      // 完成了96次预测表示当天预测任务已完成
      return 'success';
    } else if (taskStatus.prediction && taskStatus.predictionCount > 0) {
      // 预测任务正在运行但尚未完成
      return 'warning';
    } else if (taskStatus.prediction) {
      // PM2 进程在运行但还没有任何预测完成 (可能是刚启动)
      return 'warning';
    } else {
      // 预测任务未运行
      return 'danger';
    }
  } 
  // 如果是短期或中期预测
  else {
    if (taskStatus.predictionCompleted) {
      // 任务已完成 (基于标志文件)
      return 'success';
    } else if (taskStatus.prediction) {
      // 任务正在运行 (当天PM2在线但无标志文件)
      return 'warning';
    } else {
      // 任务未运行
      return 'danger';
    }
  }
}

// 获取预测任务的状态文本
const getTaskPredictionStatus = (taskStatus) => {
  // 如果是超短期预测
  if (currentPrediction === 'ultra_short') {
    if (taskStatus.predictionCount >= 96) {
      // 完成了96次预测表示当天预测任务已完成
      return '已完成';
    } else if (taskStatus.prediction && taskStatus.predictionCount > 0) {
      // 预测任务正在运行但尚未完成
      return '运行中';
    } else if (taskStatus.prediction) {
        // PM2 进程在运行但还没有任何预测完成 (可能是刚启动)
        return '运行中';
    } else {
      // 预测任务未运行
      return '未运行';
    }
  } 
  // 如果是短期或中期预测
  else {
    if (taskStatus.predictionCompleted) {
      // 任务已完成 (基于标志文件)
      return '已完成';
    } else if (taskStatus.prediction) {
      // 任务正在运行 (当天PM2在线但无标志文件)
      return '运行中';
    } else {
      // 任务未运行
      return '未运行';
    }
  }
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

.logs-filters {
  margin-bottom: 20px;
  background: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
}

.task-info-container {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.task-info-title {
  font-size: 20px;
  margin-bottom: 24px;
  color: #303133;
  text-align: center;
}

.task-status-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.task-status-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.task-status-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.task-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-card-content {
  padding: 10px 0;
}

.task-card-content p {
  margin: 8px 0;
  font-size: 14px;
  color: #606266;
}

.script-info-section {
  margin-top: 20px;
}

.script-info-section h4 {
  margin-bottom: 10px;
  font-size: 16px;
  color: #303133;
}

.ultra-start-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin: 20px 0;
  text-align: left;
}

.ultra-start-options p {
  margin-bottom: 10px;
}

.ultra-start-options .el-checkbox {
  display: flex;
  margin-left: 20px;
  height: auto;
  align-items: flex-start;
}

.ultra-start-options .el-checkbox :deep(.el-checkbox__label) {
  white-space: normal;
  line-height: 1.5;
}

.task-date-selector {
  margin-bottom: 20px;
  text-align: center;
  background: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
}
</style>