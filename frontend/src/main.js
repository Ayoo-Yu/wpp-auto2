// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 确保路径正确

const app = createApp(App)
app.config.warnHandler = () => {}
app.use(ElementPlus)
app.mount('#app')
