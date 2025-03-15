import axios from 'axios';
import router from '../router';
import { ElMessage } from 'element-plus';

// 创建axios实例
const instance = axios.create({
  baseURL: 'http://localhost:5000',  // 直接使用完整的后端地址，不要使用 /api 前缀
  timeout: 30000,
  withCredentials: false,  // 修改为 false，因为跨域请求时 withCredentials 需要更严格的 CORS 配置
  headers: {
    'Content-Type': 'application/json'
    // 移除 'Access-Control-Allow-Origin'，这是响应头，不应该在请求中设置
  }
});

// 请求拦截器
instance.interceptors.request.use(
  config => {
    // 从localStorage中获取token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
instance.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    // 处理401错误（未授权）
    if (error.response && error.response.status === 401) {
      // 清除本地存储的token
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // 显示错误消息
      ElMessage.error('登录已过期，请重新登录');
      
      // 重定向到登录页
      router.push('/login');
    } else if (error.message === 'Network Error') {
      ElMessage.error('网络错误，请检查您的网络连接或服务器状态');
    } else {
      // 其他错误
      ElMessage.error(error.response?.data?.message || '请求失败');
    }
    
    return Promise.reject(error);
  }
);

export default instance; 