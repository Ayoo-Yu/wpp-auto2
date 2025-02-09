<!-- src/components/PredictionButtons.vue -->
<template>
  <div class="prediction-buttons">
    <el-button 
      v-if="fileId && !processing && !downloadUrl && wfCapacity>0" 
      type="primary" 
      @click="$emit('start-prediction')"
    >
      开始预测
    </el-button>

    <el-button 
      v-if="downloadUrl" 
      type="success" 
      @click="$emit('download-file', downloadUrl)"
    >
      下载预测结果
    </el-button>

    <el-button 
      v-if="reportDownloadUrl" 
      type="success" 
      @click="$emit('download-file', reportDownloadUrl)"
    >
      下载预测结果报告
    </el-button>

    <el-button 
      @click="$emit('fetch-daily-metrics')" 
      v-if="fileId && !processing && downloadUrl" 
      type="success"
    >
      图表展示
    </el-button>
  </div>
</template>

<script>
export default {
  name: 'PredictionButtons',
  props: {
    selectedFile: {
      type: Object,
      default: null
    },
    uploading: {
      type: Boolean,
      default: false
    },
    fileId: {
      type: [String, Number],
      default: null
    },
    processing: {
      type: Boolean,
      default: false
    },
    downloadUrl: {
      type: String,
      default: ''
    },
    wfCapacity: {
      type: Number,
    },
    reportDownloadUrl: {
      type: String,
      default: ''
    }
  }
};
</script>

<style scoped>
.prediction-buttons {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
  padding: 10px 0;
  width: 100%;
}

.prediction-buttons .el-button {
  width: 100%;
  height: 40px;
  font-size: 14px;
  border-radius: 8px;
  margin: 0;  /* 移除默认的按钮边距 */
}

/* 按钮悬停效果 */
.prediction-buttons .el-button:hover {
  transform: translateY(-2px);
  transition: all 0.3s ease;
}

/* 成功类型按钮样式 */
.prediction-buttons .el-button--success {
  background: #34C759;
  border-color: #34C759;
}

.prediction-buttons .el-button--success:hover {
  background: #30B753;
  border-color: #30B753;
}

/* 主要类型按钮样式 */
.prediction-buttons .el-button--primary {
  background: #0077ED;
  border-color: #0077ED;
}

.prediction-buttons .el-button--primary:hover {
  background: #0062CC;
  border-color: #0062CC;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .prediction-buttons {
    padding: 5px 0;
  }
  
  .prediction-buttons .el-button {
    height: 36px;
    font-size: 13px;
  }
}
</style>
