import api from './api';

export interface PublicFrontendConfig {
  project_name: string;
  version: string;
  environment: string;
  vendor_name: string;
  vendor_url: string;
}

export const publicConfigService = {
  // 获取公开的前端配置信息（无需认证）
  getPublicFrontendConfig: async (): Promise<PublicFrontendConfig> => {
    console.debug('[公共前端配置] 开始获取公开的前端配置信息');
    const startTime = Date.now();
    try {
      // 创建一个新的axios实例，不使用默认的拦截器
      const publicApi = api;
      
      const response = await publicApi.get<PublicFrontendConfig>('/api/v1/config/public');
      const endTime = Date.now();
      console.debug(`[公共前端配置] 获取公开的前端配置信息完成，耗时: ${endTime - startTime}ms`, response.data);
      
      // 验证返回的数据
      if (!response.data) {
        throw new Error('公共配置API返回空数据');
      }
      
      return response.data;
    } catch (error) {
      console.error('[公共前端配置] 获取公开的前端配置信息失败:', error);
      throw error;
    }
  },
};