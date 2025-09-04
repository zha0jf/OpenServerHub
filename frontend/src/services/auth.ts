import api from './api';
import {
  LoginRequest,
  AuthResponse,
  User,
  CreateUserRequest,
  UpdateUserRequest,
} from '../types';

export const authService = {
  // 用户登录
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    console.log('开始登录, 用户名:', credentials.username);
    
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    const response = await api.post<AuthResponse>('/auth/login', formData);
    
    console.log('登录响应:', response.data);
    console.log('Token:', response.data.access_token);
    
    // 保存token和用户信息
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('user', JSON.stringify(response.data.user));
    
    console.log('Token已保存到localStorage');
    console.log('localStorage中的token:', localStorage.getItem('access_token'));
    
    return response.data;
  },

  // 用户登出
  async logout(): Promise<void> {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    await api.post('/auth/logout');
  },

  // 获取当前用户信息
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  // 检查是否已登录
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  },

  // 获取当前用户信息（从localStorage）
  getCurrentUserFromStorage(): User | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },
};

export const userService = {
  // 获取用户列表
  async getUsers(skip = 0, limit = 100): Promise<User[]> {
    const response = await api.get<User[]>('/users/', {
      params: { skip, limit },
    });
    return response.data;
  },

  // 获取单个用户
  async getUser(id: number): Promise<User> {
    const response = await api.get<User>(`/users/${id}`);
    return response.data;
  },

  // 创建用户
  async createUser(userData: CreateUserRequest): Promise<User> {
    const response = await api.post<User>('/users/', userData);
    return response.data;
  },

  // 更新用户
  async updateUser(id: number, userData: UpdateUserRequest): Promise<User> {
    const response = await api.put<User>(`/users/${id}`, userData);
    return response.data;
  },

  // 删除用户
  async deleteUser(id: number): Promise<void> {
    await api.delete(`/users/${id}`);
  },
};