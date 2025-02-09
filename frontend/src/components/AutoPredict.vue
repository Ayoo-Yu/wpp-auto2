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
        <el-button type="primary" @click="saveSettings">保存配置</el-button>
        <el-button type="primary" @click="resurrectConfig">加载配置</el-button>
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
                @click="handleControl(item.name, 'start')"
                :disabled="item.status"
              >
                {{ item.status ? '运行中' : '启用' }}
              </el-button>
              
              <el-button 
                type="danger" 
                @click="handleControl(item.name, 'stop')"
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
              <el-button type="danger" @click="handleControl(item.name, 'delete')">删除</el-button>
              <el-button type="info" @click="fetchScriptInfo(item.name)">详情</el-button>
              <el-button type="primary" @click="fetchLogs(item.name)">日志</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>


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
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="setSchedule">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog 
      title="脚本详情" 
      v-model="scriptInfoDialogVisible" 
      width="80%"
    >
      <pre class="info-content">{{ scriptInfo }}</pre>
      <template #footer>
        <el-button @click="scriptInfoDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog 
      title="脚本日志" 
      v-model="logsDialogVisible" 
      width="80%"
    >
      <pre class="logs-content">{{ logsContent }}</pre>
      <template #footer>
        <el-button @click="logsDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="fetchLogs(currentPrediction)">刷新</el-button>
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

// 新增：loading 状态，用于页面加载时显示提示框
const loading = ref(true)

const scheduleDialogVisible = ref(false)
const scheduleTime = ref('')
let currentPrediction = ''

// 新增变量：脚本详情与日志
const scriptInfoDialogVisible = ref(false)
const scriptInfo = ref('')
const logsDialogVisible = ref(false)
const logsContent = ref('')

let intervalId = null

onMounted(() => {
  fetchStatus()
  intervalId = setInterval(fetchStatus, 60000)
})

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
})

// 获取初始状态
const fetchStatus = async () => {
  loading.value = true  // 如果需要，可以在每次请求前设置
  try {
    const res = await axios.get('/api/status')
    predictions.forEach(p => {
      p.status = res.data[p.name] || false
    })
  } catch (error) {
    ElMessage.error('获取状态失败')
  } finally {
    loading.value = false
  }
}

// 处理控制按钮（包含 start, stop, delete 操作）
const handleControl = async (name, action) => {
  console.log('handleControl invoked', name, action)
  try {
    await axios.post(`/api/${action}`, { type: name })
    ElMessage.success('操作成功')
    await fetchStatus() // 操作成功后立即刷新状态
  } catch (error) {
    console.error('操作出错：', error)
    ElMessage.error('操作失败')
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
  
  try {
    await axios.post('/api/schedule', {
      type: currentPrediction,
      time: scheduleTime.value
    })
    ElMessage.success('定时设置成功')
    scheduleDialogVisible.value = false
    await fetchStatus() // 设置成功后立即刷新状态
  } catch (error) {
    ElMessage.error('设置失败')
  }
}

// 保存 PM2 配置（全局）
const saveSettings = async () => {
  try {
    await axios.post('/api/save')
    ElMessage.success('PM2 配置已保存')
  } catch (error) {
    ElMessage.error('保存配置失败')
  }
}

// 新增：加载 PM2 已保存的配置
const resurrectConfig = async () => {
  try {
    await axios.post('/api/resurrect')
    ElMessage.success('配置加载成功')
    await fetchStatus() // 更新状态
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败')
  }
}

// 查询脚本详情
const fetchScriptInfo = async (name) => {
  try {
    const res = await axios.get('/api/script_info', { params: { type: name }})
    scriptInfo.value = res.data.info || '暂无详情信息'
    scriptInfoDialogVisible.value = true
  } catch (error) {
    console.error('查询脚本详情失败:', error)
    ElMessage.error('查询脚本详情失败')
  }
}

// 获取脚本日志
const fetchLogs = async (name) => {
  try {
    const res = await axios.get('/api/logs', { params: { type: name, lines: 100 } })
    logsContent.value = res.data.logs || '暂无日志信息'
    logsDialogVisible.value = true
  } catch (error) {
    console.error('获取日志失败:', error)
    ElMessage.error('获取日志失败')
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

.info-content, .logs-content {
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
}
</style>