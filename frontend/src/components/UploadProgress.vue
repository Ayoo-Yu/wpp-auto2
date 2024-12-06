<!-- src/components/UploadProgress.vue -->
<template>
  <div v-if="visible" class="upload-progress">
    <el-progress :percentage="percentage" :status="status"></el-progress>
    <span>{{ percentage }}%</span>
  </div>
</template>

<script>
export default {
  name: 'UploadProgress',
  props: {
    visible: {
      type: Boolean,
      required: true
    },
    percentage: {
      type: Number,
      required: true
    },
    status: {
      type: String,
      default: 'active' // 'active', 'success', 'exception'
    }
  }
};
</script>

<style scoped>
.upload-progress {
  margin-top: 10px;
  display: flex;
  align-items: center;
}
.upload-progress span {
  margin-left: 10px;
}
</style>
