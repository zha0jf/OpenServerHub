import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Button,
  Space,
  Typography,
  Table,
  Alert,
  message,
  Tabs,
} from 'antd';
import {
  ReloadOutlined,
  LineChartOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { serverService } from '../../services/server';
import { monitoringService } from '../../services/monitoring';
import { Server, MonitoringRecord } from '../../types';
import { ColumnsType } from 'antd/es/table';
import GrafanaPanel from '../../components/monitoring/GrafanaPanel';

const { Title } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

const MonitoringDashboard: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedServerId, setSelectedServerId] = useState<number | undefined>();
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

  const handleCollectMetrics = async () => {
    if (!selectedServerId) return;

    try {
      setLoading(true);
      await monitoringService.collectServerMetrics(selectedServerId);
      message.success('监控数据采集成功');
      await loadMetrics();
    } catch (error) {
      message.error('监控数据采集失败');
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
          <Alert
            message={`当前监控服务器: ${selectedServer.name}`}
            description={`IPMI地址: ${selectedServer.ipmi_ip} | 状态: ${selectedServer.status} | 电源状态: ${selectedServer.power_state}`}
            type="info"
            style={{ marginBottom: 16 }}
          />
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