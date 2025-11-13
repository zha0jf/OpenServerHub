import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Select,
  Row,
  Col,
  Modal,
  Statistic,
  Tag,
  message,
  Tooltip,
  Spin,
  Drawer,
  DatePicker,
  Input,
} from 'antd';
import {
  DownloadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { auditLogService } from '../../services/auditLog';
import { AuditLog, AuditLogStats, SelectOption } from '../../types';
import AuditLogDetail from './AuditLogDetail';
import AuditLogStatsComponent from './AuditLogStats';

const { RangePicker } = DatePicker;

interface QueryParams {
  skip: number;
  limit: number;
  action?: string;
  operator_username?: string;
  resource_type?: string;
  resource_id?: number;
  start_date?: string;
  end_date?: string;
}

const AuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<AuditLogStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const [queryParams, setQueryParams] = useState<QueryParams>({
    skip: 0,
    limit: 20,
  });

  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  
  // 操作类型选项
  const [actionTypeOptions, setActionTypeOptions] = useState<SelectOption[]>([]);
  // 资源类型选项
  const [resourceTypeOptions, setResourceTypeOptions] = useState<SelectOption[]>([]);
  
  // 加载操作类型和资源类型选项
  const loadAuditTypes = async () => {
    try {
      const { actionTypes, resourceTypes } = await auditLogService.getAuditTypes();
      setActionTypeOptions(actionTypes);
      setResourceTypeOptions(resourceTypes);
    } catch (error) {
      console.error('加载审计类型失败:', error);
      // 失败时使用默认选项
      setActionTypeOptions([
        // 用户认证相关
        { label: 'login', value: 'login' },
        { label: 'logout', value: 'logout' },
        { label: 'login_failed', value: 'login_failed' },
        // 用户管理相关
        { label: 'user_create', value: 'user_create' },
        { label: 'user_update', value: 'user_update' },
        { label: 'user_delete', value: 'user_delete' },
        { label: 'user_role_change', value: 'user_role_change' },
        // 服务器管理相关
        { label: 'server_create', value: 'server_create' },
        { label: 'server_update', value: 'server_update' },
        { label: 'server_delete', value: 'server_delete' },
        { label: 'server_import', value: 'server_import' },
        // 电源控制相关
        { label: 'power_on', value: 'power_on' },
        { label: 'power_off', value: 'power_off' },
        { label: 'power_restart', value: 'power_restart' },
        { label: 'power_force_off', value: 'power_force_off' },
        { label: 'power_force_restart', value: 'power_force_restart' },
        // LED/定位灯控制
        { label: 'led_on', value: 'led_on' },
        { label: 'led_off', value: 'led_off' },
        // 批量操作
        { label: 'batch_power_control', value: 'batch_power_control' },
        { label: 'batch_group_change', value: 'batch_group_change' },
        // 监控相关
        { label: 'monitoring_enable', value: 'monitoring_enable' },
        { label: 'monitoring_disable', value: 'monitoring_disable' },
        // 服务器发现相关
        { label: 'discovery_start', value: 'discovery_start' },
        { label: 'discovery_complete', value: 'discovery_complete' },
        // 组管理相关
        { label: 'group_create', value: 'group_create' },
        { label: 'group_update', value: 'group_update' },
        { label: 'group_delete', value: 'group_delete' },
        // 审计日志相关
        { label: 'audit_log_export', value: 'audit_log_export' },
        { label: 'audit_log_cleanup', value: 'audit_log_cleanup' },
        { label: 'audit_log_view', value: 'audit_log_view' },
      ]);
      setResourceTypeOptions([
        { label: 'user', value: 'user' },
        { label: 'server', value: 'server' },
        { label: 'group', value: 'group' },
        { label: 'discovery', value: 'discovery' },
        { label: 'audit_log', value: 'audit_log' },
        { label: 'monitoring', value: 'monitoring' },
      ]);
    }
  };

  // 获取审计日志列表
  const fetchAuditLogs = async (params: QueryParams) => {
    setLoading(true);
    try {
      const response = await auditLogService.getAuditLogs({
        skip: params.skip,
        limit: params.limit,
        action: params.action,
        resource_type: params.resource_type,
        resource_id: params.resource_id,
        start_date: params.start_date,
        end_date: params.end_date,
      });
      setLogs(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('加载审计日志失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取统计数据
  const fetchStats = async () => {
    setStatsLoading(true);
    try {
      const response = await auditLogService.getAuditLogStats(7);
      setStats(response);
    } catch (error) {
      console.error('加载统计数据失败:', error);
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs(queryParams);
    fetchStats();
    loadAuditTypes();
  }, []);

  // 处理日期范围变化
  const handleDateRangeChange = (dates: any) => {
    if (dates) {
      const params = {
        ...queryParams,
        skip: 0,
        start_date: dates[0].format('YYYY-MM-DD'),
        end_date: dates[1].format('YYYY-MM-DD'),
      };
      setQueryParams(params);
      fetchAuditLogs(params);
    }
  };

  // 处理操作类型过滤
  const handleActionChange = (value: string) => {
    const params = {
      ...queryParams,
      skip: 0,
      action: value || undefined,
    };
    setQueryParams(params);
    fetchAuditLogs(params);
  };

  // 处理资源类型过滤
  const handleResourceTypeChange = (value: string) => {
    const params = {
      ...queryParams,
      skip: 0,
      resource_type: value || undefined,
    };
    setQueryParams(params);
    fetchAuditLogs(params);
  };

  // 刷新数据
  const handleRefresh = () => {
    fetchAuditLogs(queryParams);
    fetchStats();
    loadAuditTypes();
    message.success('已刷新');
  };

  // 清理过期日志
  const handleCleanup = () => {
    let inputDays = '';

    Modal.confirm({
      title: '清理过期日志',
      content: (
        <div>
          <p>请输入要清理的日志天数（删除超过指定天数的日志）</p>
          <Input
            placeholder="例如：30"
            type="number"
            min="1"
            onChange={(e) => {
              inputDays = e.target.value;
            }}
          />
        </div>
      ),
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk() {
        const days = parseInt(inputDays);
        if (isNaN(days) || days < 1) {
          message.error('请输入有效的天数');
          return Promise.reject();
        }

        return auditLogService
          .cleanupOldLogs(days)
          .then((response) => {
            message.success(`已删除 ${response.deleted_count} 条过期日志`);
            handleRefresh();
          })
          .catch((error) => {
            message.error('清理日志失败');
            return Promise.reject(error);
          });
      },
    });
  };

  // 导出为CSV
  const handleExportCSV = async () => {
    try {
      message.loading('正在导出...');
      const blob = await auditLogService.exportAuditLogsAsCSV(queryParams);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `审计日志_${dayjs().format('YYYY-MM-DD_HH-mm-ss')}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    }
  };

  // 导出为Excel
  const handleExportExcel = async () => {
    try {
      message.loading('正在导出...');
      const blob = await auditLogService.exportAuditLogsAsExcel(queryParams);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `审计日志_${dayjs().format('YYYY-MM-DD_HH-mm-ss')}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    }
  };

  // 查看详情
  const handleViewDetail = (log: AuditLog) => {
    setSelectedLog(log);
    setDrawerVisible(true);
  };

  // 表格列定义
  const columns = [
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (text: string) => <Tag>{text}</Tag>,
    },
    {
      title: '操作者',
      dataIndex: 'operator_username',
      key: 'operator_username',
      width: 100,
    },
    {
      title: '资源',
      key: 'resource',
      width: 150,
      render: (_: any, record: AuditLog) => (
        <span>
          {record.resource_type}: {record.resource_name || record.resource_id}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Tag color={status === 'success' ? 'green' : status === 'failed' ? 'red' : 'orange'}>
          {status === 'success' ? '成功' : status === 'failed' ? '失败' : '部分成功'}
        </Tag>
      ),
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => new Date(text + 'Z').toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'operation',
      width: 100,
      render: (_: any, record: AuditLog) => (
        <Tooltip title="查看详情">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <div style={{ padding: '0 24px' }}>
      {/* 统计卡片 */}
      <Spin spinning={statsLoading}>
        {stats && (
          <Row gutter={16} style={{ marginBottom: '24px' }}>
            <Col xs={12} sm={8} lg={4}>
              <Card>
                <Statistic
                  title="总操作数"
                  value={stats.total_operations}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <Card>
                <Statistic
                  title="失败操作"
                  value={stats.failed_operations}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} lg={4}>
              <Card>
                <Statistic
                  title="成功率"
                  value={stats.success_rate.toFixed(2)}
                  suffix="%"
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} lg={12}>
              {stats && <AuditLogStatsComponent stats={stats} />}
            </Col>
          </Row>
        )}
      </Spin>

      {/* 查询和操作栏 */}
      <Card style={{ marginBottom: '24px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Row gutter={16}>
            <Col xs={24} sm={12} lg={6}>
              <RangePicker
                style={{ width: '100%' }}
                placeholder={['开始日期', '结束日期']}
                onChange={handleDateRangeChange}
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Select
                placeholder="选择操作类型"
                style={{ width: '100%' }}
                onChange={handleActionChange}
                allowClear
                options={actionTypeOptions}
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Select
                placeholder="选择资源类型"
                style={{ width: '100%' }}
                onChange={handleResourceTypeChange}
                allowClear
                options={resourceTypeOptions}
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Button
                type="primary"
                block
                onClick={handleRefresh}
                icon={<ReloadOutlined />}
              >
                刷新
              </Button>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col xs={24} sm={12} lg={6}>
              <Button
                block
                onClick={handleExportCSV}
                icon={<DownloadOutlined />}
              >
                导出CSV
              </Button>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Button
                block
                onClick={handleExportExcel}
                icon={<DownloadOutlined />}
              >
                导出Excel
              </Button>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Button
                block
                danger
                onClick={handleCleanup}
                icon={<DeleteOutlined />}
              >
                清理过期日志
              </Button>
            </Col>
            <Col xs={24} sm={12} lg={6} />
          </Row>
        </Space>
      </Card>

      {/* 日志表格 */}
      <Card loading={loading}>
        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          pagination={{
            current: Math.floor(queryParams.skip / queryParams.limit) + 1,
            pageSize: queryParams.limit,
            total,
            onChange: (page, pageSize) => {
              const params = {
                ...queryParams,
                skip: (page - 1) * pageSize,
                limit: pageSize,
              };
              setQueryParams(params);
              fetchAuditLogs(params);
            },
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title="审计日志详情"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={600}
      >
        {selectedLog && <AuditLogDetail log={selectedLog} />}
      </Drawer>
    </div>
  );
};

export default AuditLogPage;
