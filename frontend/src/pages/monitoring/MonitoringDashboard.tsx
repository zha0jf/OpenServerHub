import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Table, 
  Typography, 
  Space, 
  Select, 
  Button, 
  message, 
  Alert,
  Tabs,
  Tag,
  Row,
  Col,
  Descriptions
} from 'antd';
import { 
  ReloadOutlined, 
  LineChartOutlined,
  BarChartOutlined,
  EyeOutlined,
  EyeInvisibleOutlined
} from '@ant-design/icons';
import { serverService } from '../../services/server';
import { monitoringService } from '../../services/monitoring';
import { Server } from '../../types';
import GrafanaPanel from '../../components/monitoring/GrafanaPanel';
import type { ColumnsType } from 'antd/es/table';
import type { MonitoringRecord } from '../../types';

const { Title } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

const MonitoringDashboard: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedServerId, setSelectedServerId] = useState<number | undefined>(undefined);
  const [metrics, setMetrics] = useState<MonitoringRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [serversLoading, setServersLoading] = useState(true);
  const [dashboardInfo, setDashboardInfo] = useState<any>(null); // 修改：存储完整的仪表板信息

  useEffect(() => {
    loadServers();
  }, []);

  useEffect(() => {
    if (selectedServerId) {
      loadMetrics();
    }
  }, [selectedServerId]);

  const loadServers = async () => {
    try {
      setServersLoading(true);
      const data = await serverService.getServers();
      setServers(data);
      if (data.length > 0 && !selectedServerId) {
        setSelectedServerId(data[0].id);
      }
    } catch (error) {
      message.error('加载服务器列表失败');
    } finally {
      setServersLoading(false);
    }
  };

  const loadMetrics = async () => {
    if (!selectedServerId) return;

    try {
      setLoading(true);
      const data = await monitoringService.getServerMetrics(selectedServerId);
      setMetrics(data);
      
      // 从后端获取Grafana仪表板信息，包括服务器状态
      try {
        const dashboardInfo = await monitoringService.getServerDashboard(selectedServerId);
        setDashboardInfo(dashboardInfo);
      } catch (dashboardError) {
        console.warn('获取Grafana仪表板信息失败:', dashboardError);
      }
    } catch (error) {
      message.error('加载监控数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 仅加载监控指标数据，不加载Grafana仪表板信息
  const loadMetricsOnly = async () => {
    if (!selectedServerId) return;

    try {
      setLoading(true);
      const data = await monitoringService.getServerMetrics(selectedServerId);
      setMetrics(data);
    } catch (error) {
      message.error('加载监控数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCollectMetrics = async () => {
    if (!selectedServerId) return;

    try {
      setLoading(true);
      await monitoringService.collectServerMetrics(selectedServerId);
      message.success('监控数据采集成功');
      // 只重新加载监控指标数据，不加载Grafana仪表板信息
      await loadMetricsOnly();
    } catch (error) {
      message.error('监控数据采集失败');
    } finally {
      setLoading(false);
    }
  };

  // 启用监控
  const handleEnableMonitoring = async () => {
    if (!selectedServerId) return;
    
    try {
      setLoading(true);
      const selectedServer = servers.find(s => s.id === selectedServerId);
      if (!selectedServer) return;
      
      await serverService.batchUpdateMonitoring({
        server_ids: [selectedServerId],
        monitoring_enabled: true
      });
      
      message.success('监控已启用');
      // 重新加载服务器列表以更新状态
      await loadServers();
      // 重新加载当前指标
      await loadMetrics();
    } catch (error) {
      message.error('启用监控失败');
    } finally {
      setLoading(false);
    }
  };

  // 禁用监控
  const handleDisableMonitoring = async () => {
    if (!selectedServerId) return;
    
    try {
      setLoading(true);
      const selectedServer = servers.find(s => s.id === selectedServerId);
      if (!selectedServer) return;
      
      await serverService.batchUpdateMonitoring({
        server_ids: [selectedServerId],
        monitoring_enabled: false
      });
      
      message.success('监控已禁用');
      // 重新加载服务器列表以更新状态
      await loadServers();
      // 重新加载当前指标
      await loadMetrics();
    } catch (error) {
      message.error('禁用监控失败');
    } finally {
      setLoading(false);
    }
  };

  const getMetricTypeDisplay = (type: string) => {
    const typeMap = {
      temperature: '温度',
      voltage: '电压',
      fan_speed: '风扇转速',
    };
    return typeMap[type as keyof typeof typeMap] || type;
  };

  const getStatusTag = (status?: string) => {
    if (!status) return '-';
    
    const statusMap = {
      ok: { color: 'green', text: '正常' },
      warning: { color: 'orange', text: '警告' },
      critical: { color: 'red', text: '严重' },
    };
    const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
    return <span style={{ color: config.color }}>{config.text}</span>;
  };

  const getPowerStateTag = (powerState: string) => {
    const stateMap = {
      on: { color: 'green', text: '开机' },
      off: { color: 'default', text: '关机' },
      unknown: { color: 'orange', text: '未知' },
    };
    const config = stateMap[powerState as keyof typeof stateMap] || { color: 'default', text: powerState };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getStatusTagDisplay = (status: string) => {
    const statusMap = {
      online: { color: 'green', text: '在线' },
      offline: { color: 'red', text: '离线' },
      unknown: { color: 'orange', text: '未知' },
      error: { color: 'red', text: '错误' },
    };
    const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getMonitoringTag = (enabled: boolean) => {
    return enabled ? 
      <Tag color="blue">已启用</Tag> : 
      <Tag color="default">未启用</Tag>;
  };

  const columns: ColumnsType<MonitoringRecord> = [
    {
      title: '指标类型',
      dataIndex: 'metric_type',
      key: 'metric_type',
      render: (type: string) => getMetricTypeDisplay(type),
    },
    {
      title: '指标名称',
      dataIndex: 'metric_name',
      key: 'metric_name',
    },
    {
      title: '当前值',
      dataIndex: 'value',
      key: 'value',
      render: (value: number, record: MonitoringRecord) => 
        `${value} ${record.unit || ''}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '采集时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (time: string) => new Date(time).toLocaleString(),
    },
  ];

  // 按类型分组数据
  const groupedMetrics = metrics.reduce((acc, metric) => {
    if (!acc[metric.metric_type]) {
      acc[metric.metric_type] = [];
    }
    acc[metric.metric_type].push(metric);
    return acc;
  }, {} as Record<string, MonitoringRecord[]>);

  const selectedServer = servers.find(s => s.id === selectedServerId);

  // 检查服务器是否离线
  const isServerOffline = dashboardInfo?.server_status === 'offline' || 
                         selectedServer?.status === 'offline';

  return (
    <div>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2} style={{ margin: 0 }}>监控仪表板</Title>
          <Space>
            <Select
              placeholder="选择服务器"
              style={{ width: 200 }}
              value={selectedServerId}
              onChange={setSelectedServerId}
              loading={serversLoading}
            >
              {servers.map(server => (
                <Option key={server.id} value={server.id}>
                  {server.name} ({server.ipmi_ip})
                </Option>
              ))}
            </Select>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={loadMetrics}
              loading={loading}
            >
              刷新数据
            </Button>
            <Button
              type="primary"
              icon={<LineChartOutlined />}
              onClick={handleCollectMetrics}
              loading={loading}
              disabled={!selectedServerId}
            >
              采集数据
            </Button>
          </Space>
        </div>

        {selectedServer && (
          <Card style={{ marginBottom: 24 }} size="small">
            <Descriptions 
              title={`服务器信息: ${selectedServer.name}`} 
              column={{ xs: 1, sm: 2, md: 3, lg: 4, xl: 4, xxl: 4 }}
              bordered
              size="small"
            >
              <Descriptions.Item label="IPMI地址">{selectedServer.ipmi_ip}</Descriptions.Item>
              <Descriptions.Item label="BMC状态">{getStatusTagDisplay(selectedServer.status)}</Descriptions.Item>
              <Descriptions.Item label="电源状态">{getPowerStateTag(selectedServer.power_state)}</Descriptions.Item>
              <Descriptions.Item label="监控状态">
                <Space>
                  {getMonitoringTag(selectedServer.monitoring_enabled)}
                  {selectedServer.monitoring_enabled ? (
                    <Button 
                      icon={<EyeInvisibleOutlined />} 
                      onClick={handleDisableMonitoring}
                      loading={loading}
                      size="small"
                      danger
                    >
                      禁用监控
                    </Button>
                  ) : (
                    <Button 
                      icon={<EyeOutlined />} 
                      onClick={handleEnableMonitoring}
                      loading={loading}
                      size="small"
                      type="primary"
                    >
                      启用监控
                    </Button>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="厂商">{selectedServer.manufacturer || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="型号">{selectedServer.model || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="序列号">{selectedServer.serial_number || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="分组">
                {selectedServer.group_id ? 
                  (servers.find(s => s.id === selectedServer.group_id)?.name || '未知分组') : 
                  '未分组'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        )}

        <Tabs defaultActiveKey="1">
          <TabPane
            tab={
              <span>
                <BarChartOutlined />
                数据表格
              </span>
            }
            key="1"
          >
            {Object.keys(groupedMetrics).length === 0 && !loading && (
              <Alert
                message="暂无监控数据"
                description="请选择服务器并点击采集数据按钮开始采集监控数据"
                type="warning"
                style={{ marginBottom: 16 }}
              />
            )}

            {Object.entries(groupedMetrics).map(([type, typeMetrics]) => (
              <Card
                key={type}
                title={getMetricTypeDisplay(type)}
                style={{ marginBottom: 16 }}
                size="small"
              >
                <Table
                  columns={columns}
                  dataSource={typeMetrics}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              </Card>
            ))}

            {Object.keys(groupedMetrics).length > 0 && (
              <Alert
                message="监控数据说明"
                description="以上数据为最近24小时的监控记录。"
                type="info"
              />
            )}
          </TabPane>
          
          <TabPane
            tab={
              <span>
                <LineChartOutlined />
                图表视图
              </span>
            }
            key="2"
          >
            {/* 修改部分：检查服务器是否存在且启用了监控 */}
            {selectedServer && selectedServer.monitoring_enabled ? (
              <div>
                {/* 添加服务器离线状态检查 */}
                {isServerOffline && (
                  <Alert
                    message="服务器离线"
                    description={`服务器 "${selectedServer.name}" 当前处于离线状态，无法获取监控数据。请检查服务器网络连接或IPMI配置。`}
                    type="warning"
                    style={{ marginBottom: 16 }}
                    showIcon
                  />
                )}
                
                {/* 使用完整IPMI仪表板显示指定的图表，并传递服务器IP作为instance参数 */}
                <div style={{ marginBottom: 16 }}>
                  <GrafanaPanel 
                    dashboardUid="UKjaSZf7z"
                    panelId="4"
                    title="风扇转速"
                    height={300}
                    queryParams={{ "var-instance": selectedServer.ipmi_ip }}
                  />
                </div>
                <div style={{ marginBottom: 16 }}>
                  <GrafanaPanel 
                    dashboardUid="UKjaSZf7z"
                    panelId="8"
                    title="功耗"
                    height={300}
                    queryParams={{ "var-instance": selectedServer.ipmi_ip }}
                  />
                </div>
                <div style={{ marginBottom: 16 }}>
                  <GrafanaPanel 
                    dashboardUid="UKjaSZf7z"
                    panelId="12"
                    title="电耗功耗"
                    height={300}
                    queryParams={{ "var-instance": selectedServer.ipmi_ip }}
                  />
                </div>
                <div style={{ marginBottom: 16 }}>
                  <GrafanaPanel 
                    dashboardUid="UKjaSZf7z"
                    panelId="19"
                    title="电压"
                    height={300}
                    queryParams={{ "var-instance": selectedServer.ipmi_ip }}
                  />
                </div>
                <div style={{ marginBottom: 16 }}>
                  <GrafanaPanel 
                    dashboardUid="UKjaSZf7z"
                    panelId="16"
                    title="温度"
                    height={300}
                    queryParams={{ "var-instance": selectedServer.ipmi_ip }}
                  />
                </div>
                <div style={{ marginBottom: 16 }}>
                  <GrafanaPanel 
                    dashboardUid="UKjaSZf7z"
                    panelId="14"
                    title="传感器状态"
                    height={300}
                    queryParams={{ "var-instance": selectedServer.ipmi_ip }}
                  />
                </div>
              </div>
            ) : (
              // 对于未启用监控的服务器显示提示信息
              <Alert
                message="监控未启用"
                description={selectedServer 
                  ? `服务器 "${selectedServer.name}" 未启用监控功能。请先在服务器管理页面启用该服务器的监控功能。` 
                  : "请选择一个已启用监控的服务器以查看监控图表。"}
                type="warning"
                showIcon
              />
            )}
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default MonitoringDashboard;