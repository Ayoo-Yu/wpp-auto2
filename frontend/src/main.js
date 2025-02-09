// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 确保路径正确
import socket from './utils/socket'

const app = createApp(App)
app.config.warnHandler = () => {}
app.use(router)
app.use(ElementPlus)

app.provide('socket', socket)  // 使用依赖注入替代全局属性

app.mount('#app')
