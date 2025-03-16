// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 确保路径正确
import './element-variables.scss'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 设置axios默认配置
axios.defaults.baseURL = process.env.VUE_APP_API_URL || ''  // 使用环境变量中的 API URL，如果没有则不添加前缀
axios.defaults.timeout = 30000
axios.defaults.withCredentials = true  // 允许跨域请求携带凭证

// 添加响应拦截器
axios.interceptors.response.use(
  response => {
    return response
  },
  error => {
    // 显示错误消息
    if (error.response && error.response.data && error.response.data.message) {
      ElMessage.error(error.response.data.message)
    } else {
      ElMessage.error('请求失败，请稍后重试')
    }
    
    return Promise.reject(error)
  }
)

const app = createApp(App)
app.config.warnHandler = () => {}
app.use(router)
app.use(ElementPlus)

app.mount('#app')
