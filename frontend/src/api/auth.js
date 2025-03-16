import axios from './axios';

// 登录API
export const login = async (username, password) => {
  const response = await axios.post('/api/auth/login', { username, password });
  return response.data;
};

// 获取当前用户信息
export const getCurrentUser = async (username) => {
  const response = await axios.get(`/api/auth/me?username=${username}`);
  return response.data;
};

// 修改密码
export const changePassword = async (username, currentPassword, newPassword) => {
  const response = await axios.post('/api/auth/change-password', {
    username,
    current_password: currentPassword,
    new_password: newPassword
  });
  return response.data;
};

// 获取用户列表
export const getUsers = async (username) => {
  const response = await axios.get(`/api/auth/users?username=${username}`);
  return response.data;
};

// 创建用户
export const createUser = async (userData, currentUsername) => {
  const response = await axios.post(`/api/auth/users?username=${currentUsername}`, userData);
  return response.data;
};

// 更新用户
export const updateUser = async (userId, userData, currentUsername) => {
  const response = await axios.put(`/api/auth/users/${userId}?username=${currentUsername}`, userData);
  return response.data;
};

// 删除用户
export const deleteUser = async (userId, currentUsername) => {
  const response = await axios.delete(`/api/auth/users/${userId}?username=${currentUsername}&current_username=${currentUsername}`);
  return response.data;
};

// 重置用户密码
export const resetUserPassword = async (userId, newPassword, currentUsername) => {
  const response = await axios.post(`/api/auth/users/${userId}/reset-password?username=${currentUsername}`, {
    new_password: newPassword
  });
  return response.data;
};

// 获取角色列表
export const getRoles = async (username) => {
  const response = await axios.get(`/api/auth/roles?username=${username}`);
  return response.data;
}; 