// src/services/apiService.js
import axios from 'axios';

const backendBaseUrl = 'http://127.0.0.1:5000';

export const upload_train_csv = (file, onUploadProgress) => {
  // 检查文件类型是否是 joblib
  const allowedExtensions = ['csv']; // 可支持的文件类型扩展名
  const fileExtension = file.name.split('.').pop().toLowerCase();

  if (!allowedExtensions.includes(fileExtension)) {
    return Promise.reject(new Error(`Unsupported file type: ${fileExtension}. Allowed types are: ${allowedExtensions.join(', ')}`));
  }

  const formData = new FormData();
  formData.append('file', file);

  return axios.post(`${backendBaseUrl}/upload_train_csv`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
};

export const upload_predict_csv = (file, onUploadProgress) => {
  // 检查文件类型是否是 joblib
  const allowedExtensions = ['csv']; // 可支持的文件类型扩展名
  const fileExtension = file.name.split('.').pop().toLowerCase();

  if (!allowedExtensions.includes(fileExtension)) {
    return Promise.reject(new Error(`Unsupported file type: ${fileExtension}. Allowed types are: ${allowedExtensions.join(', ')}`));
  }

  const formData = new FormData();
  formData.append('file', file);

  return axios.post(`${backendBaseUrl}/upload_predict_csv`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
};

export const upload_model = (file, onUploadProgress) => {
  // 检查文件类型是否是 joblib
  const allowedExtensions = ['joblib']; // 可支持的文件类型扩展名
  const fileExtension = file.name.split('.').pop().toLowerCase();

  if (!allowedExtensions.includes(fileExtension)) {
    return Promise.reject(new Error(`Unsupported file type: ${fileExtension}. Allowed types are: ${allowedExtensions.join(', ')}`));
  }

  const formData = new FormData();
  formData.append('file', file);

  return axios.post(`${backendBaseUrl}/upload_model`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
};

export const upload_scaler = (file, onUploadProgress) => {
  // 检查文件类型是否是 joblib
  const allowedExtensions = ['joblib']; // 可支持的文件类型扩展名
  const fileExtension = file.name.split('.').pop().toLowerCase();

  if (!allowedExtensions.includes(fileExtension)) {
    return Promise.reject(new Error(`Unsupported file type: ${fileExtension}. Allowed types are: ${allowedExtensions.join(', ')}`));
  }

  const formData = new FormData();
  formData.append('file', file);

  return axios.post(`${backendBaseUrl}/upload_scaler`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
};

export const modeltrain = (fileId, model, wfcapacity, trainRatio, customParams = null) => {
  const requestData = { file_id: fileId, model, wfcapacity, train_ratio: trainRatio };
  
  // 如果是自定义模型，添加自定义参数
  if (model === 'CUSTOM' && customParams) {
    requestData.custom_params = customParams;
  }
  
  return axios.post(`${backendBaseUrl}/modeltrain`, requestData);
};

export const predict = (csvfileId, modelfileId, scalerfileId) => {
  return axios.post(`${backendBaseUrl}/predict`, { csvfileId: csvfileId, modelfileId:modelfileId, scalerfileId:scalerfileId});
};

export const getActualValues = async (startTime, endTime) => {
  try {
    const response = await axios.post(`${backendBaseUrl}/power-compare/data`, {
      start: startTime,
      end: endTime,
      types: ['实测值']
    });
    return response;
  } catch (error) {
    console.error('获取实测值失败:', error);
    throw error;
  }
};

