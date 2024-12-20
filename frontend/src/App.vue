<!-- src/App.vue -->
<template>
  <div id="app">
    <UploadForm />
  </div>
</template>

<script>
import UploadForm from './components/ModelTrain.vue'

export default {
  name: 'App',
  components: {
    UploadForm
  }
}
</script>

<style>
/* 你可以在这里添加全局样式 */
</style>
