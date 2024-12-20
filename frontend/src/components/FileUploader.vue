<!-- src/components/FileUploader.vue -->
<template>
  <el-upload
    ref="upload"
    class="upload-demo"
    drag
    action=""
    :before-upload="beforeUpload"
  >
    <div class="el-upload__text">将训练集CSV文件拖到此处，或<em>点击上传</em></div>
    <template #tip>
      <div class="el-upload__tip">只能上传CSV文件，且不超过200MB</div>
    </template>
  </el-upload>
</template>

<script>
export default {
  name: 'FileUploader',
  methods: {
    beforeUpload(file) {
      const isCSV = file.type === 'csv' || file.name.endsWith('.csv');
      const isLt200M = file.size / 1024 / 1024 < 200;

      if (!isCSV) {
        this.$message.error('只能上传CSV文件！');
      }
      if (!isLt200M) {
        this.$message.error('文件大小不能超过200MB！');
      }
      if (isCSV && isLt200M) {
        this.$emit('file-selected', file);
        return false; // 阻止自动上传
      }
      return false;
    }
  }
};
</script>

<style scoped>
</style>
