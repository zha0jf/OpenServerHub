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
export type PowerAction = 'on' | 'off' | 'restart' | 'force_off' | 'force_restart';

export interface PowerControlResponse {
  action: PowerAction;
  result: string;
  message: string;
}

// 批量操作类型
export interface BatchPowerRequest {
  server_ids: number[];
  action: PowerAction;
}

export interface BatchOperationResult {
  server_id: number;
  server_name: string;
  success: boolean;
  message: string;
  error?: string;
}

export interface BatchPowerResponse {
  total_count: number;
  success_count: number;
  failed_count: number;
  results: BatchOperationResult[];
}

// 集群统计类型
export interface ClusterStats {
  total_servers: number;
  online_servers: number;
  offline_servers: number;
  unknown_servers: number;
  power_on_servers: number;
  power_off_servers: number;
  group_stats: Record<string, {
    total: number;
    online: number;
    offline: number;
    unknown: number;
    power_on: number;
    power_off: number;
  }>;
  manufacturer_stats: Record<string, number>;
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

export interface UpdateServerGroupRequest {
  name?: string;
  description?: string;
}

// 设备发现相关类型
export interface NetworkScanRequest {
  network: string;
  port?: number;
  timeout?: number;
  max_workers?: number;
}

export interface DiscoveredDevice {
  ip: string;
  port: number;
  username: string;
  password: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  bmc_version: string;
  accessible: boolean;
  auth_required: boolean;
}

export interface NetworkScanResponse {
  total_scanned: number;
  devices_found: number;
  devices: DiscoveredDevice[];
  scan_duration: number;
}

export interface BatchImportRequest {
  devices: any[];
  default_username?: string;
  default_password?: string;
  group_id?: number;
}

export interface BatchImportResponse {
  total_count: number;
  success_count: number;
  failed_count: number;
  failed_details: Array<{
    ip: string;
    error: string;
  }>;
}

export interface CSVImportRequest {
  csv_content: string;
  group_id?: number;
}

export interface CSVImportResponse {
  success_count: number;
  failed_count: number;
  failed_details: Array<{
    row: number;
    name: string;
    ipmi_ip: string;
    error: string;
  }>;
}