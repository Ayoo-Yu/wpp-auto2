// src/services/apiService.js
import axios from 'axios';

const backendBaseUrl = 'http://127.0.0.1:5000';

export const uploadFile = (file, onUploadProgress) => {
  // 检查文件类型是否是 joblib
  const allowedExtensions = ['csv', 'joblib']; // 可支持的文件类型扩展名
  const fileExtension = file.name.split('.').pop().toLowerCase();

  if (!allowedExtensions.includes(fileExtension)) {
    return Promise.reject(new Error(`Unsupported file type: ${fileExtension}. Allowed types are: ${allowedExtensions.join(', ')}`));
  }

  const formData = new FormData();
  formData.append('file', file);

  return axios.post(`${backendBaseUrl}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
};


export const modeltrain = (fileId, model, wfcapacity) => {
  return axios.post(`${backendBaseUrl}/modeltrain`, { file_id: fileId, model, wfcapacity});
};

export const predict = (csvfileId, modelfileId, scalerfileId) => {
  return axios.post(`${backendBaseUrl}/predict`, { csvfileId: csvfileId, modelfileId:modelfileId, scalerfileId:scalerfileId});
};

