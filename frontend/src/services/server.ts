import api from './api';
import {
  Server,
  CreateServerRequest,
  UpdateServerRequest,
  ServerGroup,
  CreateServerGroupRequest,
  UpdateServerGroupRequest,
  PowerAction,
  PowerControlResponse,
  BatchPowerRequest,
  BatchUpdateMonitoringRequest,
  BatchPowerResponse,
  ClusterStats,
  LEDStatusResponse,
  LEDControlResponse,
} from '../types';

// 导出类型以供其他模块使用
export type { ServerGroup } from '../types';

export const serverService = {
  // 获取服务器列表
  async getServers(skip = 0, limit = 100, groupId?: number): Promise<Server[]> {
    const response = await api.get<Server[]>('/servers/', {
      params: { skip, limit, group_id: groupId },
    });
    return response.data;
  },

  // 获取单个服务器
  async getServer(id: number): Promise<Server> {
    const response = await api.get<Server>(`/servers/${id}`);
    return response.data;
  },

  // 创建服务器
  async createServer(serverData: CreateServerRequest): Promise<Server> {
    const response = await api.post<Server>('/servers/', serverData);
    return response.data;
  },

  // 更新服务器
  async updateServer(id: number, serverData: UpdateServerRequest): Promise<Server> {
    const response = await api.put<Server>(`/servers/${id}`, serverData);
    return response.data;
  },

  // 删除服务器
  async deleteServer(id: number): Promise<void> {
    await api.delete(`/servers/${id}`);
  },

  // 电源控制
  async powerControl(id: number, action: PowerAction): Promise<PowerControlResponse> {
    const response = await api.post<PowerControlResponse>(`/servers/${id}/power/${action}`);
    return response.data;
  },

  // 更新服务器状态
  async updateServerStatus(id: number): Promise<any> {
    const response = await api.post(`/servers/${id}/status`);
    return response.data;
  },

  // 批量电源控制
  async batchPowerControl(request: BatchPowerRequest): Promise<BatchPowerResponse> {
    const response = await api.post<BatchPowerResponse>('/servers/batch/power', request);
    return response.data;
  },

  // 批量更新监控状态
  async batchUpdateMonitoring(request: BatchUpdateMonitoringRequest): Promise<BatchPowerResponse> {
    const response = await api.post<BatchPowerResponse>('/servers/batch/monitoring', request);
    return response.data;
  },

  // 获取集群统计信息
  async getClusterStats(groupId?: number): Promise<ClusterStats> {
    const response = await api.get<ClusterStats>('/servers/stats', {
      params: groupId ? { group_id: groupId } : {},
    });
    return response.data;
  },

  // 服务器分组管理
  // 获取分组列表
  async getServerGroups(): Promise<ServerGroup[]> {
    const response = await api.get<ServerGroup[]>('/servers/groups/');
    return response.data;
  },

  // 获取单个分组
  async getServerGroup(id: number): Promise<ServerGroup> {
    const response = await api.get<ServerGroup>(`/servers/groups/${id}`);
    return response.data;
  },

  // 创建分组
  async createServerGroup(data: CreateServerGroupRequest): Promise<ServerGroup> {
    const response = await api.post<ServerGroup>('/servers/groups/', data);
    return response.data;
  },

  // 更新分组
  async updateServerGroup(id: number, data: UpdateServerGroupRequest): Promise<ServerGroup> {
    const response = await api.put<ServerGroup>(`/servers/groups/${id}`, data);
    return response.data;
  },

  // 删除分组
  async deleteServerGroup(id: number): Promise<void> {
    await api.delete(`/servers/groups/${id}`);
  },

  // Redfish相关方法
  // 获取LED状态
  async getLEDStatus(id: number): Promise<LEDStatusResponse> {
    const response = await api.get<LEDStatusResponse>(`/servers/${id}/led-status`);
    return response.data;
  },

  // 点亮LED
  async turnOnLED(id: number): Promise<LEDControlResponse> {
    const response = await api.post<LEDControlResponse>(`/servers/${id}/led-on`);
    return response.data;
  },

  // 关闭LED
  async turnOffLED(id: number): Promise<LEDControlResponse> {
    const response = await api.post<LEDControlResponse>(`/servers/${id}/led-off`);
    return response.data;
  },

  // 调度服务器刷新任务
  async scheduleServerRefresh(id: number): Promise<any> {
    const response = await api.post<any>(`/servers/${id}/schedule-refresh`);
    return response.data;
  },
};
