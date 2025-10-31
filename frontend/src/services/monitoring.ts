import api from './api';

export interface DashboardInfo {
  dashboard_uid: string;
  dashboard_url: string;
  server_id: number;
  server_name: string;
  server_status?: 'online' | 'offline' | 'unknown' | 'error';  // 添加服务器状态信息
  server_power_state?: 'on' | 'off' | 'unknown';  // 添加服务器电源状态信息
}

export interface MonitoringRecord {
  id: number;
  server_id: number;
  metric_type: string;
  metric_name: string;
  value: number;
  unit: string | null;
  status: string | null;
  threshold_min: number | null;
  threshold_max: number | null;
  timestamp: string;
}

export const monitoringService = {
  // 获取服务器Grafana仪表板信息
  getServerDashboard: async (serverId: number): Promise<DashboardInfo> => {
    const response = await api.get<DashboardInfo>(`/monitoring/servers/${serverId}/dashboard`);
    return response.data;
  },

  // 获取服务器监控指标
  getServerMetrics: async (serverId: number, metricType?: string, hours: number = 24): Promise<MonitoringRecord[]> => {
    const params = new URLSearchParams();
    if (metricType) params.append('metric_type', metricType);
    params.append('hours', hours.toString());
    
    const response = await api.get<MonitoringRecord[]>(`/monitoring/servers/${serverId}/metrics?${params}`);
    return response.data;
  },

  // 手动采集服务器指标
  collectServerMetrics: async (serverId: number): Promise<any> => {
    const response = await api.post(`/monitoring/servers/${serverId}/collect`);
    return response.data;
  },

  // 手动采集所有服务器指标
  collectAllServersMetrics: async (): Promise<any> => {
    const response = await api.post(`/monitoring/collect-all`);
    return response.data;
  },

  // 查询Prometheus数据
  queryPrometheus: async (query: string, time?: string): Promise<any> => {
    const params = new URLSearchParams({ query });
    if (time) params.append('time', time);
    
    const response = await api.get(`/monitoring/prometheus/query?${params}`);
    return response.data;
  },

  // 查询Prometheus范围数据
  queryPrometheusRange: async (query: string, start: string, end: string, step: string = '60s'): Promise<any> => {
    const params = new URLSearchParams({
      query,
      start,
      end,
      step
    });
    
    const response = await api.get(`/monitoring/prometheus/query_range?${params}`);
    return response.data;
  }
};