// 用户相关类型
export interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'operator' | 'user' | 'readonly';
  is_active: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
  role: 'admin' | 'operator' | 'user' | 'readonly';
  is_active: boolean;
}

export interface UpdateUserRequest {
  username?: string;
  email?: string;
  password?: string;
  role?: 'admin' | 'operator' | 'user' | 'readonly';
  is_active?: boolean;
}

// 认证相关类型
export interface LoginRequest {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// 服务器相关类型
export interface Server {
  id: number;
  name: string;
  ipmi_ip: string;
  ipmi_username: string;
  ipmi_port: number;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  status: 'online' | 'offline' | 'unknown' | 'error';
  power_state: 'on' | 'off' | 'unknown';
  last_seen?: string;
  description?: string;
  tags?: string;
  group_id?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateServerRequest {
  name: string;
  ipmi_ip: string;
  ipmi_username: string;
  ipmi_password: string;
  ipmi_port?: number;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  description?: string;
  tags?: string;
  group_id?: number;
}

export interface UpdateServerRequest {
  name?: string;
  ipmi_ip?: string;
  ipmi_username?: string;
  ipmi_password?: string;
  ipmi_port?: number;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  description?: string;
  tags?: string;
  group_id?: number;
}

// 服务器分组类型
export interface ServerGroup {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateServerGroupRequest {
  name: string;
  description?: string;
}

// 监控相关类型
export interface MonitoringRecord {
  id: number;
  server_id: number;
  metric_type: string;
  metric_name: string;
  value: number;
  unit?: string;
  status?: string;
  threshold_min?: number;
  threshold_max?: number;
  timestamp: string;
}

// API响应类型
export interface ApiResponse<T> {
  data?: T;
  message?: string;
  error?: string;
}

// 分页类型
export interface PaginationParams {
  skip?: number;
  limit?: number;
}

// 电源控制类型
export type PowerAction = 'on' | 'off' | 'restart' | 'force_off';

export interface PowerControlResponse {
  action: PowerAction;
  result: string;
  message: string;
}