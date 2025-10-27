import api from './api';
import { MonitoringRecord } from '../types';

export const monitoringService = {
  // 获取服务器监控指标
  async getServerMetrics(
    serverId: number,
    metricType?: string,
    hours = 24
  ): Promise<MonitoringRecord[]> {
    const response = await api.get<MonitoringRecord[]>(`/monitoring/servers/${serverId}/metrics`, {
      params: { metric_type: metricType, hours },
    });
    return response.data;
  },

  // 手动采集服务器指标
  async collectServerMetrics(serverId: number): Promise<any> {
    const response = await api.post(`/monitoring/servers/${serverId}/collect`);
    return response.data;
  },
};

// 添加获取服务器仪表板信息的函数
export const getServerDashboard = async (serverId: number): Promise<any> => {
  try {
    const response = await api.get(`/monitoring/servers/${serverId}/dashboard`);
    return response.data;
  } catch (error) {
    console.error(`获取服务器 ${serverId} 的仪表板信息失败:`, error);
    throw error;
  }
};
