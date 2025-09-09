import api from './api';

// 设备发现相关类型定义
export interface NetworkScanRequest {
  network: string;
  port?: number;
  timeout?: number;
  max_workers?: number;
  calculated_timeout?: number; // 新增计算后的超时时间参数
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
  already_exists: boolean;
  existing_server_id?: number;
  existing_server_name?: string;
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

export interface NetworkExamples {
  cidr_examples: string[];
  range_examples: string[];
  single_ip_examples: string[];
  description: {
    cidr: string;
    range: string;
    single: string;
  };
}

class DiscoveryService {
  
  /**
   * 扫描网络范围内的BMC设备
   */
  async scanNetwork(request: NetworkScanRequest): Promise<NetworkScanResponse> {
    // 使用计算后的超时时间，如果没有则使用默认的2分钟超时
    const apiTimeout = request.calculated_timeout ? request.calculated_timeout * 1000 : 120000;
    const response = await api.post('/discovery/network-scan', request, {
      timeout: apiTimeout
    });
    return response.data;
  }

  /**
   * 批量导入发现的设备
   */
  async batchImportDevices(request: BatchImportRequest): Promise<BatchImportResponse> {
    const response = await api.post('/discovery/batch-import', request);
    return response.data;
  }

  /**
   * 从CSV文件导入服务器
   */
  async importFromCSVFile(file: File, groupId?: number): Promise<CSVImportResponse> {
    const formData = new FormData();
    formData.append('csv_file', file);
    if (groupId) {
      formData.append('group_id', groupId.toString());
    }

    const response = await api.post('/discovery/csv-import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * 从CSV文本内容导入服务器
   */
  async importFromCSVText(request: CSVImportRequest): Promise<CSVImportResponse> {
    const response = await api.post('/discovery/csv-import-text', request);
    return response.data;
  }

  /**
   * 下载CSV导入模板
   */
  async downloadCSVTemplate(): Promise<string> {
    const response = await api.get('/discovery/csv-template', {
      responseType: 'text'
    });
    return response.data;
  }

  /**
   * 获取网络范围格式示例
   */
  async getNetworkExamples(): Promise<NetworkExamples> {
    const response = await api.get('/discovery/network-examples');
    return response.data;
  }

  /**
   * 触发CSV模板下载
   */
  triggerCSVTemplateDownload(): void {
    const link = document.createElement('a');
    link.href = '/api/v1/discovery/csv-template';
    link.download = 'server_import_template.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

export const discoveryService = new DiscoveryService();
export default discoveryService;