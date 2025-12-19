import api from './api';

export interface FrontendConfig {
  project_name: string;
  version: string;
  environment: string;
  grafana_url: string;
  api_base_url: string;
  monitoring_enabled: boolean;
  monitoring_interval: number;
  vendor_name: string;
  vendor_url: string;
}

export const configService = {
  // 获取前端配置信息
  getFrontendConfig: async (): Promise<FrontendConfig> => {
    console.debug('[前端配置] 开始获取前端配置信息');
    const startTime = Date.now();
    try {
      const response = await api.get<FrontendConfig>('/config');
      const endTime = Date.now();
      console.debug(`[前端配置] 获取前端配置信息完成，耗时: ${endTime - startTime}ms`, response.data);
      
      // 验证返回的数据
      if (!response.data) {
        throw new Error('配置API返回空数据');
      }
      
      if (!response.data.grafana_url) {
        console.warn('[前端配置] 返回的配置中缺少grafana_url字段');
      }
      
      return response.data;
    } catch (error) {
      console.error('[前端配置] 获取前端配置信息失败:', error);
      throw error;
    }
  },
};