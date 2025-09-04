import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { message } from 'antd';

// 创建axios实例
const api: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = localStorage.getItem('access_token');
    console.log('请求拦截器 - URL:', config.url, 'Token:', token ? token.substring(0, 20) + '...' : 'null');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('添加Authorization header:', config.headers.Authorization?.substring(0, 30) + '...');
    } else {
      console.log('未找到token, 跳过Authorization header');
    }
    
    return config;
  },
  (error) => {
    console.error('请求拦截器错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    console.error('API请求错误:', error);
    
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          // 业务错误，显示具体错误信息
          if (data && typeof data === 'string') {
            message.error(data);
          } else if (data && data.detail) {
            message.error(data.detail);
          } else {
            message.error('请求参数错误');
          }
          break;
        case 401:
          // 未授权，清除token并跳转到登录页
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
            message.error('登录已过期，请重新登录');
          }
          break;
        case 403:
          message.error('权限不足');
          break;
        case 404:
          message.error('请求的资源不存在');
          break;
        case 500:
          // 服务器内部错误，显示具体错误信息
          if (data && typeof data === 'string') {
            message.error(data);
          } else if (data && data.detail) {
            message.error(data.detail);
          } else {
            message.error('服务器内部错误');
          }
          break;
        default:
          // 其他错误，优先显示服务器返回的错误信息
          if (data && typeof data === 'string') {
            message.error(data);
          } else if (data && data.detail) {
            if (typeof data.detail === 'string') {
              message.error(data.detail);
            } else if (data.detail.message) {
              message.error(data.detail.message);
            } else {
              message.error('请求失败');
            }
          } else {
            message.error('请求失败');
          }
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('网络请求失败:', error.request);
      message.error('网络连接失败，请检查网络连接');
    } else {
      // 设置请求时发生了一些事情，触发了一个错误
      console.error('请求配置错误:', error.message);
      message.error('请求配置错误');
    }
    
    return Promise.reject(error);
  }
);

export default api;