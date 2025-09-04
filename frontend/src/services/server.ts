import api from './api';
import {
  Server,
  ServerGroup,
  CreateServerRequest,
  UpdateServerRequest,
  CreateServerGroupRequest,
  PowerAction,
  PowerControlResponse,
} from '../types';

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

  // 获取服务器分组列表
  async getServerGroups(): Promise<ServerGroup[]> {
    const response = await api.get<ServerGroup[]>('/servers/groups/');
    return response.data;
  },

  // 创建服务器分组
  async createServerGroup(groupData: CreateServerGroupRequest): Promise<ServerGroup> {
    const response = await api.post<ServerGroup>('/servers/groups/', groupData);
    return response.data;
  },
};