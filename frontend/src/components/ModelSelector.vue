<template>
  <div class="model-selector">
    <!-- 未上传文件时的提示 -->
    <div v-if="!fileId" class="empty-model-selector">
      <el-icon class="empty-icon"><InfoFilled /></el-icon>
      <p class="empty-text">请先上传训练数据集文件</p>
    </div>
    
    <div v-else>
      <!-- 模型选择 -->
      <el-select 
        v-model="selectedModelLocal" 
        placeholder="请选择模型" 
        style="margin-top: 20px; width: 200px;"
        @change="onModelChange"
      >
        <el-option label="LGBM-GBDT" value="GBDT"></el-option>
        <el-option label="LGBM-DART" value="DART"></el-option>
        <el-option label="LGBM-GOSS" value="GOSS"></el-option>
      </el-select>
      
      <!-- 风电场装机容量输入框及提示文字 -->
      <div v-if="selectedModelLocal" style="margin-top: 20px;">
        <label for="wfCapacity" style="margin-right: 10px;color: #909399">整场装机容量 (MW)：</label>
        <el-input
          id="wfCapacity"
          v-model="wfCapacityLocal"
          placeholder="请输入风电场总装机容量（MW）"
          style="width: 400px;"
          @change="onWindFarmCapacityChange"
          :input-style="{ color: '#909399' }"
        ></el-input>
      </div>
    </div>
  </div>
</template>

<script>
import { InfoFilled } from '@element-plus/icons-vue'

export default {
  name: 'ModelSelector',
  components: {
    InfoFilled
  },
  props: {
    fileId: {
      type: [String, Number],
      required: true
    },
    processing: {
      type: Boolean,
      default: false
    },
    selectedModel: {
      type: String,
      default: null
    },
    predictionstate: {
      type: Boolean,
    },
    wfCapacity: {
      type: Number,
      default: 453.5,
    }
  },
  data() {
    return {
      selectedModelLocal: this.selectedModel,
      wfCapacityLocal: this.wfCapacity
    };
  },
  methods: {
    onModelChange(value) {
      this.$emit('model-selected', value);
    },
    onWindFarmCapacityChange(value) {
      if (value <= 0) {
        this.$message.error('请输入正确的数值！');
      }
      this.$emit('model_wf_capacity', value);
    },
  },
  watch: {
    selectedModel(val) {
      this.selectedModelLocal = val;
    },
    wfCapacity(val) {
      this.wfCapacityLocal = val;
    },
  }
};
</script>

<style scoped>
.model-selector {
  width: 100%;
}

.empty-model-selector {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
}

.empty-icon {
  font-size: 24px;
  color: #909399;
  margin-bottom: 12px;
}

.empty-text {
  color: #909399;
  font-size: 14px;
  text-align: center;
  margin: 0;
}

/* 新增placeholder样式 */
:deep(.el-input__inner::placeholder) {
  color: #909399;
  opacity: 1;
}
</style>
