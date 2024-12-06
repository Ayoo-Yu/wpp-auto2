<!-- src/components/LoadingIndicator.vue -->
<template>
  <div v-if="visible" class="loading-overlay">
    <el-spinner type="spinner" size="medium"></el-spinner>
    <span>{{ message }}</span>
  </div>
</template>

<script>
export default {
  name: 'LoadingIndicator',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    message: {
      type: String,
      default: '加载中...'
    }
  }
};
</script>

<style scoped>
.loading-overlay {
  display: flex;
  align-items: center;
  margin-top: 20px;
}
.loading-overlay .el-spinner {
  margin-right: 10px;
}
</style>
