<!-- src/components/PredictionButtons.vue -->
<template>
  <div style="margin-top: 20px;">
    <el-button 
      v-if="selectedFile && !uploading" 
      type="primary" 
      @click="$emit('start-upload')"
      style="margin-right: 10px;"
    >
      开始上传
    </el-button>

    <el-button 
      v-if="fileId && selectedModel && !processing && !downloadUrl" 
      type="primary" 
      @click="$emit('start-prediction')"
      style="margin-right: 10px;"
    >
      开始预测
    </el-button>

    <el-button 
      v-if="downloadUrl" 
      type="success" 
      @click="$emit('download-file',  downloadUrl)"
      style="margin-right: 10px;"
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
    selectedModel: {
      type: String,
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
    reportDownloadUrl: {
      type: String,
      default: ''
    }
  }
};
</script>

<style scoped>
.el-button {
  width: 200px;
}
</style>
