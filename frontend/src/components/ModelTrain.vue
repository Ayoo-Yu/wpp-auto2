<template>
  <div>
    <!-- //包含一个训练集上传组件，文件上传后调用onFileSelected事件 -->
    <FileUploader 
      @file-selected="onFileSelected"
    />

    <!-- // 包含一个上传进度条组件，用于显示上传进度条 -->
    <UploadProgress 
      :visible="uploading" 
      :percentage="uploadProgress" 
      :status="uploadProgress === 100 ? 'success' : 'active'"
    />
 
    <!-- // 当文件确定上传后，显示上传的文件详细信息，包含删除功能 -->
    <FileInfo 
      v-if="fileInfo" 
      :fileInfo="fileInfo" 
      @remove-file="removeSelectedFile"
    />

    <!-- // 包含一个模型选择器组件，文件上传后且未处于处理状态时显示 -->
    <ModelSelector 
      v-if="fileInfo && !processing"
      :fileId="fileId" 
      :processing="processing" 
      :selectedModel="selectedModel" 
      :predictionstate="predictionstate"
      @model-selected="onModelSelected"
    />

    <!-- // 预测按钮，根据不同的状态显示不同的按钮以触发相应的操作 -->
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
      v-if="fileId"
      :logs="logs" 
      @clear-logs="clearLogs" 
    />
    <!-- 获取测试集预测指标并可视化 -->
    <GetDailyMetrics
      v-if="fileId &&!processing && downloadUrl"
      :fileId="fileId"
      :backendBaseUrl="backendBaseUrl"
      :processing="processing"
      :downloadUrl="downloadUrl"
      :chartData="chartData"
      @fetch-daily-metrics="fetchDailyMetrics"
    />
  </div>
</template>

<script>
import { uploadFile, predict } from '@/services/apiService';  // 使用 API 服务
import { useSocket } from '@/composables/useSocket'; // 使用组合式 API 来管理 WebSocket
import FileUploader from './FileUploader.vue';
import FileInfo from './FileInfo.vue';
import ModelSelector from './ModelSelector.vue';
import PredictionButtons from './PredictionButtons.vue';
import LogViewer from './LogViewer.vue';
import LoadingIndicator from './LoadingIndicator.vue';
import UploadProgress from './UploadProgress.vue';
import GetDailyMetrics from './GetDailyMetrics.vue';

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
    GetDailyMetrics,
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
      predictionstate:false,
    };
  },
  methods: {
    // 处理文件选择
    onFileSelected(file) {
      console.log('触发了onFileSelected事件，文件已选择');
      this.resetState();//文件信息初始化
      this.selectedFile = file;
      this.fileInfo = {
        name: file.name,
        size: file.size,
        type: file.type,
        uploadDate: new Date().toLocaleString(),
      };
      console.log('@',file.name);
      console.log('@',this.selectedFile);
    },

    // 上传成功回调
    handleUploadSuccess(response) {
      console.log('触发了handleUploadSuccess事件');
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
      this.predictionstate = true;
    },

    // 下载文件
    downloadFile(downloadUrl) {
      window.open(downloadUrl);
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
      this.selectedFile = null;// 是否已经选择文件
      this.fileInfo = null;// 上传的文件信息
      this.fileId = null;// 上传的文件 ID
      this.uploading = false;// 是否正在上传
      this.uploadProgress = 0;// 上传进度
      this.processing = false;// 是否正在处理
      this.selectedModel = null;// 选择的模型
      this.downloadUrl = '';// 测试集预测数据下载链接
      this.reportDownloadUrl = '';//模型训练报告下载链接
      this.predictionstate = false;
    },
  },
};
</script>

<style scoped>
</style>