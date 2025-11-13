import api from './api';
import { AuditLog, AuditLogListResponse, AuditLogStats, CleanupLogsResponse, SelectOption } from '../types';

const BASE_URL = '/audit-logs';

interface QueryParams {
  skip?: number;
  limit?: number;
  action?: string;
  operator_id?: number;
  resource_type?: string;
  resource_id?: number;
  start_date?: string;
  end_date?: string;
}

// 审计类型响应
interface AuditTypesResponse {
  action_types: Array<{ action: string }>;
  resource_types: Array<{ resource_type: string }>;
}

export const auditLogService = {
  /**
   * 获取审计日志列表
   */
  async getAuditLogs(params?: QueryParams): Promise<AuditLogListResponse> {
    try {
      const response = await api.get<AuditLogListResponse>(BASE_URL, { params });
      return response.data;
    } catch (error) {
      console.error('获取审计日志列表失败:', error);
      throw error;
    }
  },

  /**
   * 获取审计日志详情
   */
  async getAuditLogDetail(logId: number): Promise<AuditLog> {
    try {
      const response = await api.get<AuditLog>(`${BASE_URL}/${logId}`);
      return response.data;
    } catch (error) {
      console.error('获取审计日志详情失败:', error);
      throw error;
    }
  },

  /**
   * 获取审计日志统计摘要
   */
  async getAuditLogStats(days: number = 7): Promise<AuditLogStats> {
    try {
      const response = await api.get<AuditLogStats>(`${BASE_URL}/stats/summary`, {
        params: { days },
      });
      return response.data;
    } catch (error) {
      console.error('获取审计日志统计失败:', error);
      throw error;
    }
  },

  /**
   * 清理过期审计日志
   */
  async cleanupOldLogs(days: number): Promise<CleanupLogsResponse> {
    try {
      const response = await api.post<CleanupLogsResponse>(
        `${BASE_URL}/cleanup`,
        { days }
      );
      return response.data;
    } catch (error) {
      console.error('清理审计日志失败:', error);
      throw error;
    }
  },

  /**
   * 导出审计日志为CSV
   */
  async exportAuditLogsAsCSV(params?: QueryParams): Promise<Blob> {
    try {
      const response = await api.get(`${BASE_URL}/export/csv`, {
        params,
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      console.error('导出审计日志失败:', error);
      throw error;
    }
  },

  /**
   * 导出审计日志为Excel
   */
  async exportAuditLogsAsExcel(params?: QueryParams): Promise<Blob> {
    try {
      const response = await api.get(`${BASE_URL}/export/excel`, {
        params,
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      console.error('导出审计日志失败:', error);
      throw error;
    }
  },

  /**
   * 获取操作类型和资源类型列表
   */
  async getAuditTypes(): Promise<{ actionTypes: SelectOption[], resourceTypes: SelectOption[] }> {
    try {
      const response = await api.get<AuditTypesResponse>(`${BASE_URL}/types`);
      const actionTypes = response.data.action_types.map(item => ({
        label: item.action,
        value: item.action
      }));
      const resourceTypes = response.data.resource_types.map(item => ({
        label: item.resource_type,
        value: item.resource_type
      }));
      return { actionTypes, resourceTypes };
    } catch (error) {
      console.error('获取审计类型列表失败:', error);
      throw error;
    }
  },
};