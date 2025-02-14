<template>
  <div class="model-train-container">
    <!-- 页面标题 -->
    <h1 class="page-title">风电功率预测模型训练</h1>

    <!-- Hero Section 装饰在标题之后 -->
    <div class="hero-section"></div>

    <!-- 主体内容区域：左右两栏 -->
      <div class="content-area">
        <!-- 左侧：文件上传、模型选择与操作面板 -->
        <div class="left-panel">
          <!-- 数据集上传区域 -->
          <section class="panel-section">
            <h2>选择训练数据集</h2>
            <FileUploader
              :processing="processing"
              :acceptedFormats="['csv']"
              :uploadText="customUploadText_modeltrain"
              @file-selected="onFileSelected"
            />
            <p class="upload-tip">请上传CSV文件，且不超过200MB</p>
          </section>

          <!-- 文件信息区域 -->
          <section class="panel-section" v-if="fileInfo">
            <h2>文件信息</h2>
            <FileInfo 
              :fileInfo="fileInfo" 
              @remove-file="removeSelectedFile"
              @start-upload="handleManualUpload"
            />
          </section>

          <!-- 模型选择区域 -->
          <section class="panel-section" v-if="fileInfo">
            <h2>选择训练模型</h2>
            <ModelSelector 
              :fileId="fileId" 
              :processing="processing" 
              :selectedModel="selectedModel" 
              :wfCapacity="wfCapacity"
              :predictionstate="predictionstate"
              @model-selected="onModelSelected"
              @model_wf_capacity="onWindFarmCapacityChange"
            />
          </section>

          <!-- 操作面板区域 -->
          <section class="panel-section">
            <h2>操作面板</h2>
            <div v-if="!fileInfo || !selectedModel" class="empty-operation-panel">
              <el-icon class="empty-icon"><InfoFilled /></el-icon>
              <p class="empty-text">请完成文件上传和模型选择</p>
            </div>
            <PredictionButtons 
              v-else
              :selectedFile="selectedFile" 
              :uploading="uploading" 
              :fileId="fileId" 
              :wfCapacity="wfCapacity"
              :processing="processing" 
              :downloadUrl="downloadUrl"
              :reportDownloadUrl="reportDownloadUrl"
              @start-upload="handleManualUpload"
              @start-prediction="startPrediction"
              @download-file="downloadFile"
              @fetch-daily-metrics="fetchDailyMetrics"
            />
          </section>
        </div>

        <!-- 右侧：日志展示区域 -->
        <div class="right-panel">
          <!-- 训练日志区域 -->
          <section class="panel-section log-section">
            <h2>训练日志</h2>
            <div v-if="!logs" class="empty-log-panel">
              <el-icon class="empty-icon"><InfoFilled /></el-icon>
              <p class="empty-text">暂无日志信息</p>
            </div>
            <LogViewer 
              v-if="logs"
              :logs="logs" 
              @clear-logs="clearLogs"
            />
          </section>
        </div>
      </div>
    

    <!-- 上传进度与加载提示 -->
    <UploadProgress 
      :visible="uploading" 
      :percentage="uploadProgress" 
      :status="uploadProgress === 100 ? 'success' : 'active'"
    />
    <LoadingIndicator 
      :visible="uploading" 
      message="上传中..."
    />
    <LoadingIndicator 
      :visible="processing" 
      message="训练中...请耐心等待"
    />

    <!-- 图表展示区域 -->
    <section class="charts-section" v-if="chartData">
      <h2>训练结果分析</h2>
      <div class="chart-grid">
        <div
          v-for="(chart, index) in chartData" 
          :key="index"
          class="chart-wrapper"
        >
          <canvas :ref="`chart${index}`"></canvas>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import { upload_train_csv, modeltrain } from '@/services/apiService';  
import { useSocket } from '@/composables/useSocket'; 
import FileUploader from './FileUploader.vue';
import FileInfo from './FileInfo.vue';
import ModelSelector from './ModelSelector.vue';
import PredictionButtons from './PredictionButtons.vue';
import LogViewer from './LogViewer.vue';
import LoadingIndicator from './LoadingIndicator.vue';
import UploadProgress from './UploadProgress.vue';
import Papa from 'papaparse';
import axios from 'axios';
import { Chart, CategoryScale, LinearScale, LineElement, PointElement, Title, Tooltip, Legend, LineController } from 'chart.js';
Chart.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  LineController
);

export default {
  name: 'ModelTrain',
  components: {
    FileUploader,
    FileInfo,
    ModelSelector,
    PredictionButtons,
    LogViewer,
    LoadingIndicator,
    UploadProgress,
  },
  data() {
    return {
      backendBaseUrl: 'http://127.0.0.1:5000',
      customUploadText_modeltrain: '点击上传训练数据集文件',
      fileId: null,
      selectedFile: null,
      uploading: false,
      uploadProgress: 0,
      fileInfo: null,
      selectedModel: null,
      downloadUrl: '',
      reportDownloadUrl: '',
      logs: '',
      processing: false,
      socket: null,
      predictionReady: false,
      predictionstate: false,
      wfCapacity: 453.5,
      dailyMetrics: null,
      chartData: null,
      chartInstances: [],
    };
  },
  methods: {
    onFileSelected(file) {
      this.resetState();
      this.selectedFile = file;
      this.fileInfo = {
        name: file.name,
        size: file.size,
        type: file.type,
        uploadDate: new Date().toLocaleString(),
      };
      this.initializeSocket();
    },
    handleUploadSuccess(response) {
      this.uploading = false;
      this.uploadProgress = 0;
      if (response.file_id) {
        this.fileId = response.file_id;
        this.$message.success('文件上传成功！请点击选择模型类型。');
      }
      if (response.download_url) {
        this.downloadUrl = `${this.backendBaseUrl}${response.download_url}`;
        this.$message.success('文件上传并处理成功！');
      }
      if (response.report_download_url) {
        this.reportDownloadUrl = `${this.backendBaseUrl}${response.report_download_url}`;
        this.$message.success('预测报告已生成，您可以下载报告。');
      }
      this.selectedFile = null;
    },
    handleUploadError(error) {
      this.uploading = false;
      this.uploadProgress = 0;
      console.error('文件上传失败:', error);
      this.$message.error(`文件上传失败：${error.message || '未知错误'}`);
    },
    removeSelectedFile() {
      this.resetState();
      this.$message.info('已删除选中的文件。');
    },
    onModelSelected(model) {
      this.selectedModel = model;
    },
    onWindFarmCapacityChange(value) {
      this.wfCapacity = value;
    },
    onPredictionReady(value) {
      this.predictionReady = value;
    },
    handleManualUpload() {
      if (!this.selectedFile) {
        this.$message.error('请先选择一个文件！');
        return;
      }
      this.uploading = true;
      this.uploadProgress = 0;

      upload_train_csv(this.selectedFile, (progressEvent) => {
        if (progressEvent.lengthComputable) {
          this.uploadProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        }
      })
        .then(response => {
          this.handleUploadSuccess(response.data);
        })
        .catch(error => {
          this.handleUploadError(error);
        });
    },
    startPrediction() {
      if (!this.fileId || !this.selectedModel) {
        this.$message.error('请先选择文件并指定模型！');
        return;
      }
      this.processing = true;
      modeltrain(this.fileId, this.selectedModel, this.wfCapacity)
        .then(response => {
          if (response.data.download_url) {
            this.downloadUrl = `${this.backendBaseUrl}${response.data.download_url}`;
            this.$message.success('预测完成！您可以下载预测结果。');
          } else {
            this.$message.error('预测完成，但未返回下载链接。');
          }
          if (response.data.report_download_url) {
            this.reportDownloadUrl = `${this.backendBaseUrl}${response.data.report_download_url}`;
            this.$message.success('预测报告已生成，您可以下载报告。');
          } else {
            this.$message.error('预测完成，但未返回报告下载链接。');
          }
        })
        .catch(error => {
          this.$message.error(`预测失败：${error.response?.data?.error || '未知错误'}`);
        })
        .finally(() => {
          this.processing = false;
        });
      this.predictionstate = true;
    },
    downloadFile(downloadUrl) {
      window.open(downloadUrl);
    },
    initializeSocket() {
      if (this.socket) return;
      this.socket = useSocket(this.backendBaseUrl, { path: '/socket.io', transports: ['websocket'] });
      this.socket.on('connect', () => {});
      this.socket.on('log', (data) => {
        this.logs += `${data.message}\n`;
        this.$nextTick(() => {
          const logContent = this.$el.querySelector('.log-content');
          if (logContent) {
            logContent.scrollTop = logContent.scrollHeight;
          }
        });
      });
    },
    clearLogs() {
      this.logs = '';
    },
    resetState() {
      this.selectedFile = null;
      this.fileInfo = null;
      this.fileId = null;
      this.uploading = false;
      this.uploadProgress = 0;
      this.processing = false;
      this.selectedModel = null;
      this.downloadUrl = '';
      this.reportDownloadUrl = '';
      this.predictionstate = false;
    },
    async fetchDailyMetrics() {
      if (!this.fileId) {
        this.$message.error('请先上传文件！');
        return;
      }

      try {
        const response = await axios.get(`${this.backendBaseUrl}/get-daily-metrics?file_id=${this.fileId}`);
        
        if (!response.data) {
          this.$message.error('未获取到日常指标数据');
          return;
        }

        // 使用 Promise 包装 Papa.parse
        const parseData = new Promise((resolve) => {
          Papa.parse(response.data, {
            complete: (result) => {
              if (result.errors.length > 0) {
                this.$message.error('CSV 解析失败');
                console.error(result.errors);
                return;
              }
              resolve(result.data);
            }
          });
        });

        const data = await parseData;
        await this.processChartData(data);
        
      } catch (error) {
        this.$message.error(`获取日常指标失败：${error.message}`);
        console.error('Error fetching daily metrics:', error);
      }
    },
    async processChartData(data) {
      if (!data || data.length === 0) {
        this.$message.error('CSV 数据格式错误，请检查文件内容');
        return;
      }

      const labels = [];
      const maeValues = [];
      const mseValues = [];
      const rmseValues = [];
      const accValues = [];
      const kValues = [];
      const peValues = [];

      const dataRows = data.slice(1);
      dataRows.forEach(item => {
        const rawDate = item[0];
        const date = new Date(rawDate);
        if (isNaN(date.getTime())) {
          console.warn('Skipping invalid date:', rawDate);
          return;
        }
        const formattedDate = date.toISOString().slice(0, 10).replace(/-/g, '/');
        labels.push(formattedDate);
        
        const mae = parseFloat(item[1]);
        const mse = parseFloat(item[2]);
        const rmse = parseFloat(item[3]);
        const acc = parseFloat(item[4]);
        const k = parseFloat(item[5]);
        const pe = parseFloat(item[6]);

        if (isNaN(mae) || isNaN(mse) || isNaN(rmse) || isNaN(acc) || isNaN(k) || isNaN(pe)) {
          console.warn('Skipping row with invalid values:', item);
          return;
        }

        maeValues.push(mae);
        mseValues.push(mse);
        rmseValues.push(rmse);
        accValues.push(acc);
        kValues.push(k);
        peValues.push(pe);
      });

      if (labels.length === 0 || maeValues.length === 0) {
        this.$message.error('无效的数据，无法绘制图表');
        return;
      }

      // 先清空之前的图表数据
      this.chartData = null;
      await this.$nextTick();

      // 设置新的图表数据
      this.chartData = [
        { label: '平均绝对误差 MAE', data: maeValues, borderColor: '#4caf50', backgroundColor: 'rgba(76, 175, 80, 0.2)', fill: true },
        { label: '均方误差 MSE', data: mseValues, borderColor: '#ff5722', backgroundColor: 'rgba(255, 87, 34, 0.2)', fill: true },
        { label: '均方根误差 RMSE', data: rmseValues, borderColor: '#2196f3', backgroundColor: 'rgba(33, 150, 243, 0.2)', fill: true },
        { label: '预测精度 ACC', data: accValues, borderColor: '#ff9800', backgroundColor: 'rgba(255, 152, 0, 0.2)', fill: true },
        { label: '预测精度 K', data: kValues, borderColor: '#9c27b0', backgroundColor: 'rgba(156, 39, 176, 0.2)', fill: true },
        { label: '日均考核电量 Pe', data: peValues, borderColor: '#00bcd4', backgroundColor: 'rgba(0, 188, 212, 0.2)', fill: true },
      ];

      await this.$nextTick();
      this.renderCharts(labels);
    },
    renderCharts(labels) {
      // 确保之前的图表实例被销毁
      if (this.chartInstances) {
        this.chartInstances.forEach(chart => chart.destroy());
      }
      this.chartInstances = [];

      this.chartData.forEach((dataset, index) => {
        const canvas = this.$refs[`chart${index}`][0];
        if (canvas) {
          const ctx = canvas.getContext('2d');
          const chart = new Chart(ctx, {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{
                label: dataset.label,
                data: dataset.data,
                borderColor: dataset.borderColor,
                backgroundColor: dataset.backgroundColor,
                fill: dataset.fill
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: true,
              plugins: {
                legend: {
                  position: 'top'
                },
                title: {
                  display: true,
                  text: dataset.label
                }
              },
              scales: {
                y: {
                  beginAtZero: true
                }
              }
            }
          });
          this.chartInstances.push(chart);
        }
      });
    },
    beforeDestroy() {
      if (this.socket) {
        this.socket.disconnect();
        this.socket = null;
      }
      // 确保组件销毁时清理图表实例
      if (this.chartInstances) {
        this.chartInstances.forEach(chart => chart.destroy());
      }
    },
  },
};
</script>

<style scoped>
.model-train-container {
  min-height: 100vh;
  padding: 40px;
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

.content-area {
  display: grid;
  grid-template-columns: minmax(400px, 1fr) minmax(500px, 1.2fr);
  gap: 32px;
  margin-bottom: 40px;
  align-items: start;
  min-height: calc(100vh - 200px);
}

.left-panel, .right-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
  height: 100%;
}

.left-panel {
  display: flex;
  flex-direction: column;
}

.panel-section {
  background: #ffffff;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border-radius: 24px;
  padding: 32px;
  margin-bottom: 24px;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.panel-section:last-child {
  margin-bottom: 0;
}

.panel-section:hover {
  transform: translateY(-4px);
  box-shadow: var(--hover-shadow);
}

.panel-section h2 {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.panel-section h3 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 500;
  color: #1d1d1f;
}

.upload-tip {
  color: #606266;
  margin-top: 12px;
  font-size: 13px;
  text-align: center;
}

.log-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 600px;
  margin-bottom: 0;
}

.log-section .log-content {
  flex: 1;
  background: #ffffff;
  border-radius: 12px;
  padding: 16px;
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 13px;
  line-height: 1.5;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #909399 #f4f4f5;
}

.log-section .log-content::-webkit-scrollbar {
  width: 6px;
}

.log-section .log-content::-webkit-scrollbar-track {
  background: #f4f4f5;
  border-radius: 3px;
}

.log-section .log-content::-webkit-scrollbar-thumb {
  background: #909399;
  border-radius: 3px;
}

.log-section .log-content::-webkit-scrollbar-thumb:hover {
  background: #606266;
}

.charts-section {
  background: #ffffff;
  border: 1px solid #ebeef5;
  padding: 32px;
  border-radius: 20px;
  margin-top: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.charts-section h2 {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.chart-wrapper {
  aspect-ratio: 16/9;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

@media (max-width: 1200px) {
  .content-area {
    grid-template-columns: 1fr;
  }
  
  .panel-section {
    padding: 24px;
  }
  
  .chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .model-train-container {
    padding: 24px 16px;
  }
  
  .page-title {
    font-size: 28px;
    margin-bottom: 32px;
  }
  
  .panel-section {
    padding: 20px;
  }
}

/* 新增动效 */
.section-enter-active, .section-leave-active {
  transition: all 0.3s ease;
}
.section-enter, .section-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.empty-operation-panel, .empty-log-panel {
  padding: 32px;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.empty-icon {
  font-size: 24px;
  color: #909399;
  margin-bottom: 12px;
}

.empty-text {
  color: #909399;
  font-size: 14px;
  text-align: center;
  margin: 0;
}

/* 进度条样式 */
.el-progress-bar__inner {
  background: var(--primary-gradient) !important;
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
  bottom: 0;
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
</style>

