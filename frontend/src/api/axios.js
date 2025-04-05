import axios from 'axios';
import { ElMessage } from 'element-plus';

// 确定API基础URL
let API_BASE_URL;

// 如果不是localhost，使用当前域名+端口
if (window.location.hostname !== 'localhost') {
  API_BASE_URL = `http://${window.location.hostname}:5000`; // 明确指定后端端口为5000
} else {
  API_BASE_URL = 'http://localhost:5000'; // 本地开发环境
}

console.log('使用API基础URL:', API_BASE_URL);

// 创建axios实例
const instance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
instance.interceptors.request.use(
  config => {
    console.log('发送请求:', config.method.toUpperCase(), config.url);
    return config;
  },
  error => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
instance.interceptors.response.use(
  response => {
    console.log('收到响应:', response.status, response.config.url);
    return response;
  },
  error => {
    // 详细日志错误信息
    console.error('响应错误:', error.message);
    if (error.response) {
      console.error('状态码:', error.response.status);
      console.error('响应数据:', error.response.data);
    } else if (error.request) {
      console.error('请求已发送但未收到响应');
      console.error('请求详情:', error.request);
    }
    
    // 处理错误情况
    if (error.message === 'Network Error') {
      ElMessage.error('网络错误，请检查您的网络连接或服务器状态');
    } else {
      // 其他错误
      ElMessage.error(error.response?.data?.message || '请求失败');
    }
    
    return Promise.reject(error);
  }
);

export default instance; 