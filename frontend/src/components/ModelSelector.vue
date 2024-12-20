<!-- src/components/ModelSelector.vue -->
<template>
  <el-select 
    v-if="fileId && !processing && !predictionstate" 
    v-model="selectedModelLocal" 
    placeholder="请选择模型" 
    style="margin-top: 20px; width: 200px;"
    @change="onModelChange"
  >
    <el-option label="LGBM-GBDT" value="GBDT"></el-option>
    <el-option label="LGBM-DART" value="DART"></el-option>
    <el-option label="LGBM-GOSS" value="GOSS"></el-option>
  </el-select>
</template>

<script>
export default {
  name: 'ModelSelector',
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
    predictionstate:{
      type:Boolean,
    }
  },
  data() {
    return {
      selectedModelLocal: this.selectedModel
    };
  },
  methods: {
    onModelChange(value) {
      this.$emit('model-selected', value);
    }
  },
  watch: {
    selectedModel(val) {
      this.selectedModelLocal = val;
    }
  }
};
</script>

<style scoped>
</style>
