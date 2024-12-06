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
      :status="uploadProgress === 100 ? 'success' : 'active'"
    />

    <FileInfo 
      v-if="fileInfo" 
      :fileInfo="fileInfo" 
      @remove-file="removeSelectedFile" 
    />

    <ModelSelector 
      v-if="fileInfo && !processing" 
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
      :reportDownloadUrl="report_download_url"
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
import axios from 'axios';
import { io } from 'socket.io-client';

import FileUploader from './FileUploader.vue';
import FileInfo from './FileInfo.vue';
import ModelSelector from './ModelSelector.vue';
import PredictionButtons from './PredictionButtons.vue';
import LogViewer from './LogViewer.vue';
import LoadingIndicator from './LoadingIndicator.vue';
import UploadProgress from './UploadProgress.vue'; // 新增

export default {
  name: 'UploadForm',
  components: {
    FileUploader,
    FileInfo,
    ModelSelector,
    PredictionButtons,
    LogViewer,
    LoadingIndicator,
    UploadProgress // 注册
  },
  data() {
    return {
      downloadUrl: '',
      report_download_url: '',
      backendBaseUrl: 'http://127.0.0.1:5000',
      fileId: null,
      processing: false,
      selectedFile: null,
      uploading: false,
      uploadProgress: 0, // 新增
      fileInfo: null,
      selectedModel: null,
      logs: '',
      socket: null,
    };
  },
  methods: {
    // 处理选中的文件
    onFileSelected(file) {
      this.resetState();
      this.selectedFile = file;
      this.fileInfo = {
        name: file.name,
        size: file.size,
        type: file.type,
        uploadDate: new Date().toLocaleString()
      };
    },
    // 上传成功的回调
    handleUploadSuccess(response) {
      this.uploading = false;
      this.uploadProgress = 0; // 重置进度

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
        this.report_download_url = `${this.backendBaseUrl}${response.report_download_url}`;
        this.$message.success('预测报告已生成，您可以下载报告。');
      }

      if (this.fileInfo) {
        this.fileInfo.uploadDate = new Date().toLocaleString();
      }

      if (!response.file_id && !response.download_url && !response.report_download_url) {
        this.$message.error('未知的服务器响应。');
      }

      this.selectedFile = null;
    },
    // 上传失败的回调
    handleUploadError(error) {
      this.uploading = false;
      this.uploadProgress = 0; // 重置进度
      console.error('文件上传失败:', error);
      if (error && error.message) {
        this.$message.error(`文件上传失败：${error.message}`);
      } else {
        this.$message.error('文件上传失败！');
      }
    },
    // 删除选中的文件
    removeSelectedFile() {
      this.resetState();
      this.$message.info('已删除选中的文件。');
    },
    // 模型选择的回调
    onModelSelected(model) {
      this.selectedModel = model;
    },
    // 手动触发上传的函数
    handleManualUpload() {
      if (!this.selectedFile) {
        this.$message.error('请先选择一个文件！');
        return;
      }
      this.uploading = true;
      this.uploadProgress = 0; // 初始化进度
      const formData = new FormData();
      formData.append('file', this.selectedFile);

      axios.post(`${this.backendBaseUrl}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.lengthComputable) {
            this.uploadProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        }
      })
      .then(response => {
        this.handleUploadSuccess(response.data);
      })
      .catch(error => {
        this.uploading = false;
        this.uploadProgress = 0; // 重置进度
        this.handleUploadError(error);
      });
    },
    // 手动触发预测的函数
    startPrediction() {
      if (!this.fileId || !this.selectedModel) {
        this.$message.error('请先选择文件并指定模型！');
        return;
      }
      this.processing = true;
      axios.post(`${this.backendBaseUrl}/predict`, { 
        file_id: this.fileId, 
        model: this.selectedModel 
      })
      .then(response => {
        if (response.data.download_url) {
          this.downloadUrl = `${this.backendBaseUrl}${response.data.download_url}`;
          this.$message.success('预测完成！您可以下载预测结果。');
        } else {
          this.$message.error('预测完成，但未返回下载链接。');
        }
        if (response.data.report_download_url) {
          this.report_download_url = `${this.backendBaseUrl}${response.data.report_download_url}`;
          this.$message.success('预测报告已生成，您可以下载报告。');
        } else {
          this.$message.error('预测完成，但未返回报告下载链接。');
        }
      })
      .catch(error => {
        if (error.response && error.response.data && error.response.data.error) {
          this.$message.error(`预测失败：${error.response.data.error}`);
        } else {
          this.$message.error('预测失败！请稍后重试。');
        }
      })
      .finally(() => {
        this.processing = false;
      });
    },
    // 下载预测结果的函数
    downloadFile() {
      window.open(this.downloadUrl);
    },
    // 下载报告的函数
    downloadReport() {
      if (this.report_download_url) {
        window.open(this.report_download_url);
      } else {
        this.$message.error('报告下载链接不可用。');
      }
    },
    // 初始化 Socket.IO 连接
    initializeSocket() {
      if (this.socket) {
        return;
      }
      this.socket = io(this.backendBaseUrl);

      this.socket.on('connect', () => {
        console.log('Connected to SocketIO server');
        this.logs += '[系统] 已连接到日志服务器。\n';
      });

      this.socket.on('disconnect', () => {
        console.log('Disconnected from SocketIO server');
        this.logs += '[系统] 与日志服务器断开连接。\n';
      });

      this.socket.on('log', (data) => {
        this.logs += `${data.message}\n`;
        this.$nextTick(() => {
          const logContent = this.$el.querySelector('.log-content');
          if (logContent) {
            logContent.scrollTop = logContent.scrollHeight;
          }
        });
      });

      this.socket.on('response', (data) => {
        console.log(data.message);
        this.logs += `[系统] ${data.message}\n`;
      });
    },
    // 清空日志
    clearLogs() {
      this.logs = '';
    },
    // 重置所有相关状态
    resetState() {
      this.selectedFile = null;
      this.fileInfo = null;
      this.fileId = null;
      this.downloadUrl = '';
      this.uploading = false;
      this.uploadProgress = 0; // 重置进度
      this.processing = false;
      this.selectedModel = null;
      this.report_download_url = '';
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
