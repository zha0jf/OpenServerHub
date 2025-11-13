import api from './api';

export interface BackupFile {
  filename: string;
  size: number;
  created_at: string;
  file_path: string;
}

export interface BackupListResponse {
  backups: BackupFile[];
}

export interface BackupVerifyResponse {
  filename: string;
  is_valid: boolean;
  message: string;
}

class BackupService {
  /**
   * 创建数据库备份
   */
  async createBackup(): Promise<BackupFile> {
    const response = await api.post<BackupFile>('/backup/create');
    return response.data;
  }

  /**
   * 获取备份列表
   */
  async listBackups(): Promise<BackupFile[]> {
    const response = await api.get<BackupListResponse>('/backup/list');
    return response.data.backups;
  }

  /**
   * 删除备份
   */
  async deleteBackup(filename: string): Promise<boolean> {
    const response = await api.delete<boolean>('/backup/delete', {
      data: { filename }
    });
    return response.data;
  }

  /**
   * 恢复备份
   */
  async restoreBackup(filename: string): Promise<boolean> {
    const response = await api.post<boolean>('/backup/restore', {
      filename
    });
    return response.data;
  }

  /**
   * 验证备份
   */
  async verifyBackup(filename: string): Promise<BackupVerifyResponse> {
    const response = await api.post<BackupVerifyResponse>('/backup/verify', {
      filename
    });
    return response.data;
  }
}

export const backupService = new BackupService();
