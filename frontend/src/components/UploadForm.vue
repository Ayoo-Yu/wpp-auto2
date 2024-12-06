<!-- src/components/UploadForm.vue -->
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
    }
  },

  beforeUnmount() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
};
</script>

<style scoped>
/* 现有样式 */
</style>
