<template>
  <div class="power-predict-container">
    <h1 class="page-title">风电功率预测</h1>


    <div class="main-content">
      <div class="upload-section">
        <!-- 数据集上传区域 -->
        <div class="upload-card">
          <div class="card-header">
            <h2>选择预测数据集</h2>
            <div class="step-number">1</div>
          </div>
          <FileUploader
            :processing="processing"
            :acceptedFormats="['csv']"
            :uploadText="customUploadText_datacsv"
            @file-selected="onCsvFileSelected"
          />
          <FileInfo 
            :fileInfo="csvfileInfo" 
            @remove-file="removeSelectedCsvFile"
            @start-upload="csvHandleManualUpload"
          />
        </div>

        <!-- 模型上传区域 -->
        <div class="upload-card">
          <div class="card-header">
            <h2>选择预测模型</h2>
            <div class="step-number">2</div>
          </div>
          <FileUploader
            :processing="processing"
            :acceptedFormats="['joblib']"
            :uploadText="customUploadText_model"
            @file-selected="onModelFileSelected"
            :disabled="!csvfileId"
          />
          <FileInfo 
            :fileInfo="modelfileInfo" 
            @remove-file="removeSelectedModelFile"
            @start-upload="modelHandleManualUpload"
          />
        </div>

        <!-- 归一化模型上传区域 -->
        <div class="upload-card">
          <div class="card-header">
            <h2>选择归一化模型</h2>
            <div class="step-number">3</div>
          </div>
          <FileUploader
            :processing="processing"
            :acceptedFormats="['joblib']"
            :uploadText="customUploadText_scaler"
            @file-selected="onScalerFileSelected"
            :disabled="!modelfileId"
          />
          <FileInfo 
            :fileInfo="scalerfileInfo"
            @remove-file="removeSelectedScalerFile"
            @start-upload="scalerHandleManualUpload"
          />
        </div>
      </div>

      <div class="right-panel">
        <!-- 步骤提示 -->
        <div class="status-card">
          <h3>预测文件ID</h3>
          <StepHintBox 
            :csvfileid="csvfileId" 
            :modelfileid="modelfileId" 
            :scalerfileid="scalerfileId"
          />
        </div>

        <!-- 操作按钮 -->
        <div class="action-card">
          <div v-if="!csvfileId || !modelfileId || !scalerfileId" class="empty-action-panel">
            <el-icon class="empty-icon"><InfoFilled /></el-icon>
            <p class="empty-text">请完成所有文件上传后开始预测</p>
          </div>
          <div v-else class="action-buttons">
            <button 
              type="button" 
              class="action-button predict-button"
              @click="handlePredict"
              :disabled="processing"
            >
              {{ processing ? '预测中...' : '开始预测' }}
            </button>
            <button 
              v-if="downloadUrl"
              type="button" 
              class="action-button download-button"
              @click="downloadFile(downloadUrl)"
            >
              下载预测结果
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 日志查看器 -->
    <div class="log-section">
      <h3>预测日志</h3>
      <div v-if="!csvfileInfo" class="empty-log-panel">
        <el-icon class="empty-icon"><InfoFilled /></el-icon>
        <p class="empty-text">暂无日志信息</p>
      </div>
      <LogViewer 
        v-else
        :logs="logs" 
        @clear-logs="clearLogs" 
      />
    </div>
  </div>
</template>

<script>
import { upload_predict_csv,upload_model,upload_scaler,predict } from '@/services/apiService';  // 使用 API 服务
import { useSocket } from '@/composables/useSocket'; // 使用组合式 API 来管理 WebSocket
import FileUploader from './FileUploader.vue';
import StepHintBox from "./StepHintBox.vue";
import FileInfo from './FileInfo.vue';
import LogViewer from './LogViewer.vue';

export default {
  name: 'PowerPredict',
  components: {
    FileUploader,
    FileInfo,
    LogViewer,
    StepHintBox,
  },
  data() {
    return {
      backendBaseUrl: 'http://127.0.0.1:5000',
      customUploadText_datacsv: '选择预测数据集',
      customUploadText_model: '请选择预测模型',
      customUploadText_scaler: '请选择归一化模型',
      csvfileId: null,
      modelfileId: null,
      scalerfileId: null,
      selectedCsvFile: null,
      selecteModelFile: null,
      selectedScalerFile: null,
      uploading: false,
      uploadProgress: 0,
      csvfileInfo: null,
      modelfileInfo: null,
      scalerfileInfo: null,
      downloadUrl: '',
      logs: '',
      processing: false,
      socket: null,
    };
  },
  methods: {
    // 模型文件处理
    onModelFileSelected(file) {
      this.onFileSelected(file, 'Model');
    },
    modelHandleUploadSuccess(response) {
      this.handleUploadSuccess(response, 'Model', '模型文件上传成功，请继续选择本地归一化文件！');
    },
    removeSelectedModelFile() {
      this.removeSelectedFile('Model');
    },
    modelHandleManualUpload() {
      this.handleManualUpload(
        'Model',
        '请先选择一个文件！',
        this.modelHandleUploadSuccess
      );
    },

    // Scaler文件处理
    onScalerFileSelected(file) {
      this.onFileSelected(file, 'Scaler');
    },
    scalerHandleUploadSuccess(response) {
      this.handleUploadSuccess(response, 'Scaler', '归一化模型文件上传成功，请点击"开始预测"以执行预测！');
    },
    removeSelectedScalerFile() {
      this.removeSelectedFile('Scaler');
    },
    scalerHandleManualUpload() {
      this.handleManualUpload(
        'Scaler',
        '请先选择一个文件！',
        this.scalerHandleUploadSuccess
      );
    },
    // Csv文件处理
    onCsvFileSelected(file) {
      this.onFileSelected(file, 'Csv');
    },
    csvHandleUploadSuccess(response) {
      this.handleUploadSuccess(response, 'Csv', 'Csv文件选择成功，请继续选择本地模型文件！');
    },
    removeSelectedCsvFile() {
      this.removeSelectedFile('Csv');
    },
    csvHandleManualUpload() {
      this.handleManualUpload(
        'Csv',
        '请选择一个不同的文件！',
        this.csvHandleUploadSuccess
      );
    },

    onFileSelected(file, type) {
      this.resetState(type);
      this[`selected${type}File`] = file;
      this[`${type.toLowerCase()}fileInfo`] = {
        name: file.name,
        size: file.size,
        type: type === 'Csv' ? file.type : 'joblib',
        uploadDate: new Date().toLocaleString(),
      };
      this.initializeSocket();
    },

    handleUploadSuccess(response, type, successMessage) {
      this.uploading = false;
      this.uploadProgress = 0;
      if (response.file_id) {
        this[`${type.toLowerCase()}fileId`] = response.file_id;
        this.$message.success(successMessage);
      }
      this[`selected${type}File`] = null;
    },

    handleUploadError(error) {
      this.uploading = false;
      this.uploadProgress = 0;
      console.error('文件上传失败:', error);
      this.$message.error(`文件上传失败：${error.message || '未知错误'}`);
    },

    removeSelectedFile(type) {
      this.resetState(type);
      this.$message.info('已删除选中的文件。');
    },

    handleManualUpload(type, errorMessage, successCallback) {
      const file = this[`selected${type}File`];
      if (!file) {
        this.$message.error(errorMessage);
        return;
      }

      this.uploading = true;
      this.uploadProgress = 0;

      if (type === 'Csv') {
        upload_predict_csv(file, (progressEvent) => {
          if (progressEvent.lengthComputable) {
            this.uploadProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        })
        .then(response => {
          successCallback(response.data);
        })
        .catch(error => {
          this.handleUploadError(error);
        });
      } else if (type === 'Model') {
        upload_model(file, (progressEvent) => {
          if (progressEvent.lengthComputable) {
            this.uploadProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        })
        .then(response => {
          successCallback(response.data);
        })
        .catch(error => {
          this.handleUploadError(error);
        });
      } else if (type === 'Scaler') {
        upload_scaler(file, (progressEvent) => {
          if (progressEvent.lengthComputable) {
            this.uploadProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        })
        .then(response => {
          successCallback(response.data);
        })
        .catch(error => {
          this.handleUploadError(error);
        });
      } else {
        this.$message.error('文件类型错误！');
      }
    },

    handlePredict() {
      if (!this.csvfileId || !this.modelfileId || !this.scalerfileId) {
        this.$message.error('请先选择所有文件！');
        return;
      }
      this.processing = true;
      predict(this.csvfileId, this.modelfileId,this.scalerfileId)
        .then(response => {
          if (response.data.download_url) {
            console.log(response.data.download_url);
            this.downloadUrl = `${this.backendBaseUrl}${response.data.download_url}`;
            this.$message.success('预测完成！您可以下载预测结果。');
          } else {
            this.$message.error('预测完成，但未返回下载链接。');
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
    downloadFile(downloadUrl) {
      window.open(downloadUrl);
    },

    // 初始化 WebSocket 连接
    initializeSocket() {
      if (this.socket) return;
      this.socket = useSocket(this.backendBaseUrl, { path: '/socket.io', transports: ['websocket'] });
      this.socket.on('connect', () => {
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
    },

    clearLogs() {
      this.logs = '';
    },

    resetState(type) {
      this[`selected${type}File`] = null;
      this[`${type.toLowerCase()}fileInfo`] = null;
      this[`${type.toLowerCase()}fileId`] = null;
      this.uploading = false;
      this.uploadProgress = 0;
      this.processing = false;
      this.selectedModel = null;
      this.downloadUrl = '';
    },

    beforeDestroy() {
      if (this.socket) {
        this.socket.disconnect();
        this.socket = null;
      }
    },
  },
};
</script>

<style scoped>
.power-predict-container {
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
  font-size: 42px !important; /* 强制使用统一大小 */
  font-weight: 600;
  color: white;
  text-align: center;
  margin-bottom: 48px;
  letter-spacing: -0.003em;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.main-content {
  display: flex;
  gap: 50px;  /* 更大的间距 */
  margin-bottom: 60px;
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
  position: relative;  /* 用于装饰元素定位 */
}

/* 添加装饰元素 */
.main-content::before {
  content: "✨";
  position: absolute;
  top: -20px;
  left: -10px;
  font-size: 24px;
  opacity: 0.5;
}

.main-content::after {
  content: "✨";
  position: absolute;
  bottom: -20px;
  right: -10px;
  font-size: 24px;
  opacity: 0.5;
}

.upload-section {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 40px;  /* 更大的卡片间距 */
}

.upload-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 30px;  /* 更大的圆角 */
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  border: 1px solid rgba(0, 0, 0, 0.03);
  position: relative;  /* 用于装饰元素定位 */
}

/* 添加卡片装饰 */
.upload-card::before {
  content: "✦";
  position: absolute;
  top: 20px;
  right: 20px;
  font-size: 16px;
  color: #0077ED;
  opacity: 0.5;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 20px;
  background: linear-gradient(135deg, #0077ED 0%, #00A2FF 100%);  /* 渐变背景 */
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 18px;
  box-shadow: 0 4px 12px rgba(0, 119, 237, 0.2);
}

.upload-card h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
  letter-spacing: -0.003em;
}

.right-panel {
  width: 340px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.status-card, .action-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 30px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.03);
  max-width: 300px;  /* 设置最大宽度 */
  width: 100%;  /* 确保宽度为100% */
}

.status-card h3 {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 24px 0;
  letter-spacing: -0.003em;
}

.action-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 30px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.03);
  display: flex;  /* 添加 flex 布局 */
  justify-content: center;  /* 水平居中 */
  align-items: center;  /* 垂直居中 */
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;  /* 确保按钮容器占满整个宽度 */
  align-items: center;  /* 按钮水平居中 */
}

.action-button {
  height: 40px;  /* 统一按钮高度为40px */
  padding: 0 20px;
  font-size: 14px;  /* 统一字体大小 */
  font-weight: 600;
  border-radius: 8px;  /* 统一圆角大小 */
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;  /* 简化过渡效果 */
  width: 100%;
  max-width: 260px;
  letter-spacing: -0.01em;
  display: flex;
  justify-content: center;
  align-items: center;
}

.predict-button {
  background: #0077ED;  /* 统一使用扁平色 */
  color: #ffffff;
}

.predict-button:hover:not(:disabled) {
  background: #0062CC;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 119, 237, 0.25);  /* 减小阴影 */
}

.download-button {
  background: #34C759;  /* 统一使用扁平色 */
  color: #ffffff;
}

.download-button:hover {
  background: #30B753;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(52, 199, 89, 0.25);  /* 减小阴影 */
}

.log-section {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 30px;
  padding: 40px;
  margin-top: 30px;
  max-width: 1440px;
  margin: 0 auto;
}

/* 响应式设计 */
@media (max-width: 1400px) {
  .main-content {
    flex-direction: column;
  }

  .right-panel {
    width: 100%;
    flex-direction: row;
  }

  .status-card, .action-card {
    flex: 1;
  }
}

@media (max-width: 1200px) {
  .upload-section {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .power-predict-container {
    padding: 20px;
  }

  .power-predict-container h1 {
    font-size: 32px;
  }

  .right-panel {
    flex-direction: column;
  }

  .upload-card, .status-card, .action-card {
    padding: 20px;
  }
}

.empty-action-panel, .empty-log-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
  min-height: 120px; /* 确保有足够的高度 */
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

.log-section h3 {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 24px 0;
  letter-spacing: -0.003em;
}

/* 上传按钮的特定样式 */
.el-upload .el-button,
.el-button.el-button--success,
.el-button--success:hover,
.el-button--success:focus,
.el-button--success:active {
  background-color: #34C759 !important;
  border-color: transparent !important;
  border: 0 !important;
  color: white !important;
  outline: none !important;
}

/* 覆盖Element Plus的默认样式 */
:deep(.el-button) {
  border: 0 !important;
  outline: none !important;
}

:deep(.el-button--success) {
  --el-button-border-color: transparent !important;
  --el-button-bg-color: #34C759 !important;
  border: none !important;
}

:deep(.el-upload) {
  .el-button {
    border: 0 !important;
    background-color: #34C759 !important;
  }
}

/* 删除按钮样式 */
.el-button--danger {
  background-color: #ff3b30 !important;
  border: none !important;
  color: white !important;
}
</style>

