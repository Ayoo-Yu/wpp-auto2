<!-- src/components/FileInfo.vue -->
<template>
  <el-card v-if="fileInfo" class="file-info-card" style="margin-top: 20px;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <h3>文件信息</h3>
      <el-button type="link" @click="$emit('remove-file')" style="color: #f56c6c;">
        删除
      </el-button>
    </div>
    <el-descriptions column="1">
      <el-descriptions-item label="文件名称：">{{ fileInfo.name }}</el-descriptions-item>
      <el-descriptions-item label="文件大小：">{{ formattedSize }}</el-descriptions-item>
      <el-descriptions-item label="文件类型：">{{ fileInfo.type }}</el-descriptions-item>
      <el-descriptions-item label="上传时间：">{{ fileInfo.uploadDate }}</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script>
export default {
  name: 'FileInfo',
  props: {
    fileInfo: {
      type: Object,
      required: true
    }
  },
  computed: {
    formattedSize() {
      if (!this.fileInfo) return '';
      const size = this.fileInfo.size;
      if (size < 1024) return `${size} B`;
      else if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
      else if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(2)} MB`;
      else return `${(size / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
  }
};
</script>

<style scoped>
.file-info-card {
  border: 4px solid #ebeef5;
  padding: 20px;
}
.file-info-card h3 {
  margin-bottom: 20px;
}
.file-info-card .el-button {
  padding: 20;
  font-size: 20px;
}
</style>
