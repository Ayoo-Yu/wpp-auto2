// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 确保路径正确
import './element-variables.scss'
import axios from './api/axios'  // 使用我们配置好的axios实例

// 不再需要重复配置axios，因为已经在api/axios.js中配置过了

const app = createApp(App)
app.config.warnHandler = () => {}
app.use(router)
app.use(ElementPlus)

// 全局挂载axios以便于访问
app.config.globalProperties.$axios = axios

app.mount('#app')
