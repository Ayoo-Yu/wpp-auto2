<!-- src/components/LogViewer.vue -->
<template>
  <div class="log-viewer">
    <div class="log-content">
      <pre>{{ logs }}</pre>
    </div>
    <div class="log-actions">
      <el-button type="text" @click="$emit('clear-logs')" class="clear-button">
        清空日志
      </el-button>
    </div>
  </div>
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
.log-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

.log-content {
  flex: 1;
  background: #fafafa;
  border-radius: 12px;
  padding: 16px;
  overflow-y: auto;
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #333;
}

.log-actions {
  display: flex;
  justify-content: flex-end;
}

.clear-button {
  color: #ff3b30;
}

.clear-button:hover {
  color: #ff2d55;
}
</style>
