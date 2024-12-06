<!-- src/components/LogViewer.vue -->
<template>
  <el-card class="log-card" style="margin-top: 20px;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <h3>实时日志</h3>
      <el-button type="text" @click="$emit('clear-logs')" style="color: #f56c6c;">
        清空
      </el-button>
    </div>
    <div class="log-content">
      <pre>{{ logs }}</pre>
    </div>
  </el-card>
</template>

<script>
export default {
  name: 'LogViewer',
  props: {
    logs: {
      type: String,
      default: ''
    }
  }
};
</script>

<style scoped>
.log-card {
  border: 1px solid #ebeef5;
  padding: 20px;
  max-height: 300px;
  overflow-y: auto;
}
.log-content {
  background-color: #f5f5f5;
  padding: 10px;
  height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-family: monospace;
}
</style>
