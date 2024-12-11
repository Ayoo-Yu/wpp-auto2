<template>
  <div>
    <FileUploader 
      :backendBaseUrl="backendBaseUrl"
      @file-selected="onFileSelected"
      @upload-success="handleUploadSuccess"
      @upload-error="handleUploadError"
    />

    <UploadProgress 
      :visible="uploading" 
      :percentage="uploadProgress" 
      :status="uploadStatus"
    />

    <FileInfo 
      v-if="fileInfo" 
      :fileInfo="fileInfo" 
      @remove-file="removeSelectedFile"
    />

    <ModelSelector 
      v-if="showModelSelector" 
      :fileId="fileId" 
      :processing="processing" 
      :selectedModel="selectedModel" 
      @model-selected="onModelSelected"
    />

    <PredictionButtons 
      :selectedFile="selectedFile" 
      :uploading="uploading" 
      :fileId="fileId" 
      :selectedModel="selectedModel"
      :processing="processing" 
      :downloadUrl="downloadUrl"
      :reportDownloadUrl="reportDownloadUrl"
      @start-upload="handleManualUpload"
      @start-prediction="startPrediction"
      @download-file="downloadFile"
      @download-report="downloadReport"
    />

    <LoadingIndicator 
      :visible="uploading" 
      message="上传中..." 
    />

    <LoadingIndicator 
      :visible="processing" 
      message="预测中..." 
    />

    <LogViewer 
      :logs="logs" 
      @clear-logs="clearLogs" 
    />

    <!-- 获取日常指标按钮 -->
    <button @click="fetchDailyMetrics" v-if="fileId && !processing">获取日常指标</button>

    <!-- 图表展示 -->
    <div v-if="chartData" class="charts-container">
      <div v-for="(chart, index) in chartData" :key="index" class="chart-container">
        <canvas :id="'chart' + index"></canvas>
        <p>{{ chart.label }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { uploadFile, predict } from '@/services/apiService';  // 使用 API 服务
import { useSocket } from '@/composables/useSocket'; // 使用组合式 API 来管理 WebSocket
import Papa from 'papaparse';
import FileUploader from './FileUploader.vue';
import FileInfo from './FileInfo.vue';
import ModelSelector from './ModelSelector.vue';
import PredictionButtons from './PredictionButtons.vue';
import LogViewer from './LogViewer.vue';
import LoadingIndicator from './LoadingIndicator.vue';
import UploadProgress from './UploadProgress.vue';
import axios from 'axios';
import { Chart, CategoryScale, LinearScale, LineElement, PointElement, Title, Tooltip, Legend, LineController } from 'chart.js';
// 注册所需的组件，包括 LineController
Chart.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  LineController  // 注册 LineController
);


export default {
  name: 'UploadForm',
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
      dailyMetrics: null,  // 用于存储获取到的日常指标数据
      chartData: null,  // 用于存储可视化的图表数据
    };
  },
  computed: {
    showModelSelector() {
      return this.fileInfo && !this.processing;
    },
    uploadStatus() {
      return this.uploadProgress === 100 ? 'success' : 'active';
    }
  },
  methods: {
    // 处理文件选择
    onFileSelected(file) {
      this.resetState();
      this.selectedFile = file;
      this.fileInfo = {
        name: file.name,
        size: file.size,
        type: file.type,
        uploadDate: new Date().toLocaleString(),
      };
    },

    // 上传成功回调
    handleUploadSuccess(response) {
      this.uploading = false;
      this.uploadProgress = 0;
      if (response.file_id) {
        this.fileId = response.file_id;
        this.$message.success('文件上传成功！请点击“开始预测”以执行预测。');
        this.initializeSocket();
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

    // 上传失败回调
    handleUploadError(error) {
      this.uploading = false;
      this.uploadProgress = 0;
      console.error('文件上传失败:', error);
      this.$message.error(`文件上传失败：${error.message || '未知错误'}`);
    },

    // 删除文件
    removeSelectedFile() {
      this.resetState();
      this.$message.info('已删除选中的文件。');
    },

    // 选择模型回调
    onModelSelected(model) {
      this.selectedModel = model;
    },

    // 手动触发上传
    handleManualUpload() {
      if (!this.selectedFile) {
        this.$message.error('请先选择一个文件！');
        return;
      }
      this.uploading = true;
      this.uploadProgress = 0;

      uploadFile(this.selectedFile, (progressEvent) => {
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

    // 手动触发预测
    startPrediction() {
      if (!this.fileId || !this.selectedModel) {
        this.$message.error('请先选择文件并指定模型！');
        return;
      }
      this.processing = true;
      predict(this.fileId, this.selectedModel)
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
    },

    // 下载文件
    downloadFile() {
      window.open(this.downloadUrl);
    },

    // 下载报告
    downloadReport() {
      if (this.reportDownloadUrl) {
        window.open(this.reportDownloadUrl);
      } else {
        this.$message.error('报告下载链接不可用。');
      }
    },

    // 初始化 WebSocket 连接
    initializeSocket() {
      if (this.socket) return;

      this.socket = useSocket(this.backendBaseUrl);
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

    // 清空日志
    clearLogs() {
      this.logs = '';
    },

    // 重置状态
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
    },

    // 获取 daily-metrics.csv 数据
    fetchDailyMetrics() {
      if (!this.fileId) {
        this.$message.error('请先上传文件！');
        return;
      }

      axios
        .get(`${this.backendBaseUrl}/get-daily-metrics?file_id=${this.fileId}`)
        .then(response => {
          console.log('Response data:', response.data);  // 打印返回的数据，查看是否为 CSV 格式
          if (!response.data) {
            this.$message.error('未获取到日常指标数据');
            return;
          }

          Papa.parse(response.data, {
            complete: (result) => {
              console.log('Parsed result:', result); // 查看解析后的数据
              if (result.errors.length > 0) {
                this.$message.error('CSV 解析失败');
                console.error(result.errors);
                return;
              }
              this.processChartData(result.data);
            }
          });
        })
        .catch(error => {
          this.$message.error(`获取日常指标失败：${error.message}`);
          console.error('Error fetching daily metrics:', error);
        });
    },
    processChartData(data) {
      if (!data || data.length === 0) {
        this.$message.error('CSV 数据格式错误，请检查文件内容');
        return;
      }

      const labels = [];  // 日期列表
      const maeValues = [];  // MAE 数值列表
      const mseValues = [];  // MSE 数值列表
      const rmseValues = []; // RMSE 数值列表
      const accValues = [];  // ACC 数值列表
      const kValues = [];    // K 数值列表

      const dataRows = data.slice(1); // 跳过标题行，从第二行开始处理

      dataRows.forEach(item => {
        const rawDate = item[0]; // 原始日期字符串
        const date = new Date(rawDate);  // 转换为 Date 对象
        if (isNaN(date.getTime())) {  // 如果日期无效，跳过该行
          console.warn('Skipping invalid date:', rawDate);
          return;
        }

        // 格式化日期为 `YYYYMMDD`
        const formattedDate = date.toISOString().slice(0, 10).replace(/-/g, '/');
        labels.push(formattedDate);

        const mae = parseFloat(item[1]);
        const mse = parseFloat(item[2]);
        const rmse = parseFloat(item[3]);
        const acc = parseFloat(item[4]);
        const k = parseFloat(item[5]);

        if (isNaN(mae) || isNaN(mse) || isNaN(rmse) || isNaN(acc) || isNaN(k)) {
          console.warn('Skipping row with invalid values:', item);
          return;
        }

        maeValues.push(mae);
        mseValues.push(mse);
        rmseValues.push(rmse);
        accValues.push(acc);
        kValues.push(k);
      });

      if (labels.length === 0 || maeValues.length === 0) {
        this.$message.error('无效的数据，无法绘制图表');
        return;
      }

      this.chartData = [
        { label: 'MAE', data: maeValues, borderColor: '#4caf50', backgroundColor: 'rgba(76, 175, 80, 0.2)', fill: true },
        { label: 'MSE', data: mseValues, borderColor: '#ff5722', backgroundColor: 'rgba(255, 87, 34, 0.2)', fill: true },
        { label: 'RMSE', data: rmseValues, borderColor: '#2196f3', backgroundColor: 'rgba(33, 150, 243, 0.2)', fill: true },
        { label: 'ACC', data: accValues, borderColor: '#ff9800', backgroundColor: 'rgba(255, 152, 0, 0.2)', fill: true },
        { label: 'K', data: kValues, borderColor: '#9c27b0', backgroundColor: 'rgba(156, 39, 176, 0.2)', fill: true },
      ];

      this.renderCharts(labels);
    },




    renderCharts(labels) {
      console.log('Rendering charts with labels:', labels);  // 查看传入的 labels

      this.$nextTick(() => {
        this.chartData.forEach((dataset, index) => {
          const canvasId = `chart${index}`;
          const canvasElement = document.getElementById(canvasId);

          if (canvasElement) {
            // 销毁已存在的图表实例
            if (canvasElement.chart) {
              canvasElement.chart.destroy();
            }

            const ctx = canvasElement.getContext('2d');
            console.log('Rendering chart with dataset:', dataset);  // 查看 dataset
            canvasElement.chart = new Chart(ctx, {
              type: 'line',
              data: {
                labels: labels,  // x 轴标签
                datasets: [dataset],  // 数据集
              },
              options: {
                responsive: true,
                scales: {
                  x: {
                    type: 'category',
                    title: {
                      display: false,
                      text: '日期',
                    },
                  },
                  y: {
                    type: 'linear',
                    title: {
                      display: false,
                      text: dataset.label,
                    },
                  },
                },
              },
            });
          } else {
            console.error(`Canvas element with id ${canvasId} not found`);
          }
        });
      });
    }
  },
};
</script>

<style scoped>
.charts-container {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 20px;
}
.chart-container {
  width: 45%;
}
</style>
