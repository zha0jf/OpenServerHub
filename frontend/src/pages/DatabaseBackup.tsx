import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  message,
  Modal,
  Tag,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  DownloadOutlined,
  DeleteOutlined,
  SafetyOutlined,
  RollbackOutlined,
} from '@ant-design/icons';
import { backupService, BackupFile } from '../services/backup';
import type { ColumnType } from 'antd/es/table';

const DatabaseBackup: React.FC = () => {
  const [backups, setBackups] = useState<BackupFile[]>([]);
  const [loading, setLoading] = useState(false);

  // 加载备份列表
  const fetchBackups = async () => {
    setLoading(true);
    try {
      const data = await backupService.listBackups();
      setBackups(data);
    } catch (error) {
      message.error('加载备份列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBackups();
  }, []);

  // 创建备份
  const handleCreateBackup = async () => {
    try {
      message.loading({ content: '正在创建备份...', key: 'createBackup' });
      await backupService.createBackup();
      message.success({ content: '备份创建成功', key: 'createBackup' });
      fetchBackups();
    } catch (error) {
      message.error({ content: '备份创建失败', key: 'createBackup' });
    }
  };

  // 删除备份
  const handleDelete = (filename: string) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除备份文件 ${filename} 吗？此操作不可撤销。`,
      okText: '确认',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await backupService.deleteBackup(filename);
          message.success('备份删除成功');
          fetchBackups();
        } catch (error) {
          message.error('备份删除失败');
        }
      },
    });
  };

  // 恢复备份
  const handleRestore = (filename: string) => {
    Modal.confirm({
      title: '确认恢复',
      content: (
        <>
          <p>确定要从备份文件 <strong>{filename}</strong> 恢复数据库吗？</p>
          <p style={{ color: '#ff4d4f' }}>
            警告：此操作将覆盖当前数据库的所有数据，且不可撤销！
          </p>
          <p>建议在恢复前先创建当前数据库的备份。</p>
        </>
      ),
      okText: '确认恢复',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          message.loading({ content: '正在恢复备份...', key: 'restoreBackup' });
          await backupService.restoreBackup(filename);
          message.success({ content: '备份恢复成功，建议刷新页面', key: 'restoreBackup' });
          fetchBackups();
        } catch (error) {
          message.error({ content: '备份恢复失败', key: 'restoreBackup' });
        }
      },
    });
  };

  // 验证备份
  const handleVerify = async (filename: string) => {
    try {
      message.loading({ content: '正在验证备份...', key: 'verifyBackup' });
      const result = await backupService.verifyBackup(filename);
      
      if (result.is_valid) {
        message.success({ content: result.message, key: 'verifyBackup' });
      } else {
        message.error({ content: result.message, key: 'verifyBackup' });
      }
    } catch (error) {
      message.error({ content: '备份验证失败', key: 'verifyBackup' });
    }
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  // 表格列定义
  const columns: ColumnType<BackupFile>[] = [
    {
      title: '名称',
      dataIndex: 'filename',
      key: 'filename',
      render: (filename: string) => (
        <span style={{ fontFamily: 'monospace' }}>{filename}</span>
      ),
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => formatFileSize(size),
      width: 120,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (created_at: string) => {
        const date = new Date(created_at);
        return date.toLocaleString('zh-CN');
      },
      width: 200,
    },
    {
      title: '操作',
      key: 'action',
      width: 300,
      render: (_: any, record: BackupFile) => (
        <Space size="small">
          <Tooltip title="下载备份文件">
            <Button
              type="default"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => backupService.downloadBackup(record.filename)}
            >
              下载
            </Button>
          </Tooltip>
          <Tooltip title="验证备份完整性">
            <Button
              type="primary"
              size="small"
              icon={<SafetyOutlined />}
              onClick={() => handleVerify(record.filename)}
            >
              验证完整性
            </Button>
          </Tooltip>
          <Tooltip title="从此备份恢复数据库">
            <Button
              type="default"
              size="small"
              danger
              icon={<RollbackOutlined />}
              onClick={() => handleRestore(record.filename)}
            >
              恢复
            </Button>
          </Tooltip>
          <Tooltip title="删除备份文件">
            <Button
              type="primary"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.filename)}
            >
              删除
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h1>数据库备份</h1>

      {/* 操作按钮栏 */}
      <Card style={{ marginBottom: '24px' }}>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreateBackup}
          >
            创建备份
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchBackups}
          >
            刷新
          </Button>
        </Space>
      </Card>

      {/* 备份列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={backups}
          rowKey="filename"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个备份`,
          }}
        />
      </Card>
    </div>
  );
};

export default DatabaseBackup;
