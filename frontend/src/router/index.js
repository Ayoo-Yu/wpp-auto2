// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../components/HomePage.vue' // 主页组件
import ModelTrain from '../components/ModelTrain.vue' // 父组件
import AppLayout from '../components/AppLayout.vue' // 布局组件
import PowerPredict from '../components/PowerPredict.vue' // 预测组件
import AutoPredict  from '../components/AutoPredict.vue'


const routes = [
  {
    path: '/',
    component: AppLayout, // 使用布局组件作为基础
    children: [
      {
        path: '',
        name: 'HomePage',
        component: HomePage
      },
      {
        path: 'modeltrain',
        name: 'ModelTrain',
        component: ModelTrain
      },
      {
        path: 'powerpredict',
        name: 'PowerPredict',
        component: PowerPredict
      },
      {
        path: 'autopredict',
        name: 'AutoPredict',
        component: AutoPredict
      },
      // 更多子路由
    ]
  },
  // 其他独立路由（如果有）
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router
