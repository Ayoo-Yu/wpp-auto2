// src/services/apiService.js
import axios from 'axios';

const backendBaseUrl = 'http://127.0.0.1:5000';

export const uploadFile = (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  return axios.post(`${backendBaseUrl}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
};

export const predict = (fileId, model) => {
  return axios.post(`${backendBaseUrl}/predict`, { file_id: fileId, model });
};
