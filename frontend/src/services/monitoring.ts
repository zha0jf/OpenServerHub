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