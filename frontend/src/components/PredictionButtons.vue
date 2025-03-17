<!-- src/components/PredictionButtons.vue -->
<template>
  <div class="prediction-buttons">
    <div class="button-group">
      <el-button 
        v-if="!fileId"
        type="primary" 
        @click="confirmAction('upload', '确定要上传数据集吗？')" 
        :disabled="!selectedFile || uploading || processing"
        :loading="uploading"
        class="action-btn"
      >
        上传数据集
      </el-button>
      
      <el-button 
        v-else
        type="success" 
        @click="confirmAction('prediction', '确定要开始模型训练吗？\n训练过程可能需要较长时间，请耐心等待。')" 
        :disabled="processing || !fileId"
        :loading="processing"
        class="action-btn"
      >
        开始模型训练
      </el-button>

      <!-- 新增：手动检查状态按钮 -->
      <el-button 
        v-if="processing"
        type="warning" 
        @click="$emit('check-status')" 
        class="action-btn"
      >
        <el-icon><Refresh /></el-icon>
        检查训练状态
      </el-button>
      
      <el-button 
        v-if="downloadUrl"
        type="primary" 
        @click="$emit('download-file', downloadUrl)" 
        :disabled="processing"
        class="action-btn"
      >
        <el-icon><Download /></el-icon>
        下载预测结果
      </el-button>
      
      <el-button 
        v-if="reportDownloadUrl"
        type="info" 
        @click="$emit('download-file', reportDownloadUrl)" 
        :disabled="processing"
        class="action-btn"
      >
        <el-icon><Document /></el-icon>
        下载评估报告
      </el-button>
      
      <el-button 
        v-if="fileId && !processing && downloadUrl"
        type="primary" 
        @click="confirmAction('chart', '确定要生成评估图表吗？')" 
        class="action-btn"
      >
        <el-icon><DataAnalysis /></el-icon>
        生成评估图表
      </el-button>
    </div>
  </div>
</template>

<script>
import { Refresh, Download, Document, DataAnalysis } from '@element-plus/icons-vue'

export default {
  name: 'PredictionButtons',
  components: {
    Refresh,
    Download,
    Document,
    DataAnalysis
  },
  props: {
    selectedFile: {
      type: Object,
      default: null
    },
    uploading: {
      type: Boolean,
      default: false
    },
    processing: {
      type: Boolean,
      default: false
    },
    fileId: {
      type: String,
      default: ''
    },
    wfCapacity: {
      type: Number,
      default: 453.5
    },
    downloadUrl: {
      type: String,
      default: ''
    },
    reportDownloadUrl: {
      type: String,
      default: ''
    }
  },
  methods: {
    confirmAction(action, message) {
      this.$confirm(message, '操作确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }).then(() => {
        // 用户点击确定后触发相应事件
        if (action === 'upload') {
          this.$emit('start-upload');
        } else if (action === 'prediction') {
          this.$emit('start-prediction');
        } else if (action === 'chart') {
          this.$emit('fetch-daily-metrics');
        }
      }).catch(() => {
        // 用户点击取消，不执行任何操作
        this.$message({
          type: 'info',
          message: '已取消操作'
        });
      });
    }
  }
};
</script>

<style scoped>
.prediction-buttons {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: flex-start;
  align-items: center;
}

/* 统一按钮样式 */
.action-btn {
  width: 146px !important;
  height: 40px !important;
  text-align: center !important;
  line-height: 1 !important;
  padding: 0 12px !important;
  border-radius: 4px !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}

/* 确保按钮内部内容居中 - 增强优先级 */
:deep(.action-btn span) {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  width: 100% !important;
  height: 100% !important;
  text-align: center !important;
}

/* 增强按钮内部文本居中效果 */
:deep(.action-btn .el-button__text) {
  width: 100% !important;
  text-align: center !important;
  display: inline-block !important;
}

/* 按钮图标与文字间距 */
:deep(.el-icon) {
  margin-right: 6px;
}

/* 添加全局样式覆盖 */
:deep(.el-button) {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}

:deep(.el-button span) {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  width: 100% !important;
}

@media (max-width: 768px) {
  .button-group {
    flex-direction: column;
    width: 100%;
  }
  
  .action-btn {
    width: 100% !important;
  }
}
</style>
