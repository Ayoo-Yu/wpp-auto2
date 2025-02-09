<!-- src/App.vue
<template>
  <div id="app">
    <ModelTrain />
  </div>
</template>

<script>
import ModelTrain from './components/ModelTrain.vue'

export default {
  name: 'App',
  components: {
    ModelTrain
  }
}
</script>

<style>
/* 你可以在这里添加全局样式 */
</style> -->
<!-- src/App.vue -->
<template>
  <div class="app-container">
    <router-view></router-view>
  </div>
</template>

<script setup>
// 此处不再需要背景切换逻辑，由 AppLayout 中统一控制
</script>

<style>
/* 全局样式 */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
  background: var(--background-dark);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 主题色定义 */
:root {
  --background-dark: #0A0A0A;
  --card-dark: #1C1C1E;
  --text-primary: #FFFFFF;
  --text-secondary: rgba(255, 255, 255, 0.7);
  --border-color: rgba(255, 255, 255, 0.1);
  --primary-gradient: linear-gradient(135deg, #34C759 0%, #2ECC71 100%);
  --card-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  --hover-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}

/* 卡片基础样式 */
.el-card {
  background: var(--card-dark);
  border: 1px solid var(--border-color);
  border-radius: 16px;
}

/* 按钮样式 */
.el-button {
  border-radius: 8px;
  height: 40px;
  font-weight: 500;
  letter-spacing: 0.3px;
}

.el-button--primary {
  background: var(--primary-gradient);
  border: none;
}

/* 输入框样式 */
.el-input__inner {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

/* 全局标题样式 - 增加优先级 */
.page-title,
h1.page-title,
.container .page-title {
  font-size: 42px !important;
  font-weight: 600;
  color: #1d1d1f;
  text-align: center;
  margin-bottom: 48px;
  letter-spacing: -0.003em;
}

.app-container {
  min-height: 100vh;
  background: #ffffff;
  transition: background 0.3s ease;
}

/* 确保内容在动画背景上方 */
.main-content {
  position: relative;
  z-index: 1;
}

/* 开关样式优化 */
:deep(.el-switch) {
  margin-left: 8px;
}

:deep(.el-switch__label) {
  color: #1d1d1f;
  font-size: 14px;
}
</style>
