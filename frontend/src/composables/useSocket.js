// src/composables/useSocket.js
import { io } from 'socket.io-client';

export function useSocket(backendBaseUrl) {
  const socket = io(backendBaseUrl);

  socket.on('connect', () => {
    console.log('Connected to WebSocket server');
  });

  socket.on('log', (data) => {
    // 检查 data 是否存在以及它是否包含我们预期的字段
    if (!data) {
      console.error('Received data is undefined or null');
      return;
    }

    // 打印 data 的内容，方便调试
    console.log('Received log data:', data);

    // 如果 data 中没有 message 字段，则抛出错误
    if (!data.message) {
      console.error('Received log data is missing "message" field', data);
      return;
    }

    // 如果 data 是有效的，则继续处理
    console.log(data.message);
  });

  socket.on('disconnect', () => {
    console.log('Disconnected from WebSocket server');
  });

  return socket;
}
