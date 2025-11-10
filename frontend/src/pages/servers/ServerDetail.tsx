import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Spin,
  message,
  Row,
  Col,
  Descriptions,
  Divider,
  Badge,
  Table,
  Modal,
  Tooltip,
  BackTop
} from 'antd';
import {
  ArrowLeftOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  SwapOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  ClockCircleOutlined,
  BulbOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { serverService } from '../../services/server';
import { Server, ServerGroup, PowerAction } from '../../types';
import './ServerDetail.css';

const { Title, Text } = Typography;

const ServerDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [server, setServer] = useState<Server | null>(null);
  const [groups, setGroups] = useState<ServerGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [powerLoading, setPowerLoading] = useState(false);
  const [ledStatus, setLedStatus] = useState<{ supported: boolean; led_state: string; error: string | null } | null>(null);
  const [ledLoading, setLedLoading] = useState(false);

  useEffect(() => {
    loadServerDetail();
    loadGroups();
    loadLEDStatus();
  }, [id]);

  const loadServerDetail = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const data = await serverService.getServer(parseInt(id));
      setServer(data);
    } catch (error) {
      message.error('加载服务器详情失败');
      navigate('/servers');
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      const data = await serverService.getServerGroups();
      setGroups(data);
    } catch (error) {
      console.error('加载分组列表失败:', error);
    }
  };

  const loadLEDStatus = async () => {
    if (!id) return;
    try {
      const response = await serverService.getLEDStatus(parseInt(id));
      setLedStatus(response);
    } catch (error) {
      console.error('加载LED状态失败:', error);
    }
  };

  const handleTurnOnLED = async () => {
    if (!server || !id) return;
    try {
      setLedLoading(true);
      await serverService.turnOnLED(parseInt(id));
      message.success('LED已点亮');
      await loadLEDStatus();
    } catch (error) {
      message.error('点亮LED失败');
    } finally {
      setLedLoading(false);
    }
  };

  const handleTurnOffLED = async () => {
    if (!server || !id) return;
    try {
      setLedLoading(true);
      await serverService.turnOffLED(parseInt(id));
      message.success('LED已关闭');
      await loadLEDStatus();
    } catch (error) {
      message.error('关闭LED失败');
    } finally {
      setLedLoading(false);
    }
  };

  const handlePowerControl = async (action: PowerAction) => {
    if (!server) return;

    Modal.confirm({
      title: `确认${getPowerActionName(action)}？`,
      content: `确定要对服务器 ${server.name} 执行 ${getPowerActionName(action)} 操作吗？`,
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: action.includes('force') || action === 'off' },
      onOk: async () => {
        try {
          setPowerLoading(true);
          await serverService.powerControl(server.id, action);
          message.success(`${getPowerActionName(action)}操作成功`);
          // 刷新服务器状态
          await loadServerDetail();
        } catch (error) {
          message.error(`${getPowerActionName(action)}操作失败`);
        } finally {
          setPowerLoading(false);
        }
      },
    });
  };

  const handleUpdateStatus = async () => {
    if (!server) return;
    try {
      setPowerLoading(true);
      await serverService.updateServerStatus(server.id);
      message.success('服务器状态已刷新');
      await loadServerDetail();
    } catch (error) {
      message.error('刷新服务器状态失败');
    } finally {
      setPowerLoading(false);
    }
  };

  const handleDelete = () => {
    if (!server) return;

    Modal.confirm({
      title: '确认删除？',
      content: `确定要删除服务器 ${server.name} 吗？此操作不可恢复。`,
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          setPowerLoading(true);
          await serverService.deleteServer(server.id);
          message.success('服务器已删除');
          navigate('/servers');
        } catch (error) {
          message.error('删除服务器失败');
        } finally {
          setPowerLoading(false);
        }
      },
    });
  };

  const getPowerActionName = (action: PowerAction): string => {
    const actionMap = {
      on: '开机',
      off: '关机',
      restart: '重启',
      force_off: '强制关机',
      force_restart: '强制重启',
    };
    return actionMap[action] || action;
  };

  const getStatusColor = (status: string) => {
    const colorMap = {
      online: 'green',
      offline: 'red',
      unknown: 'orange',
      error: 'red',
    };
    return colorMap[status as keyof typeof colorMap] || 'default';
  };

  const getStatusIcon = (status: string) => {
    const iconMap = {
      online: <CheckCircleOutlined />,
      offline: <CloseCircleOutlined />,
      unknown: <QuestionCircleOutlined />,
      error: <CloseCircleOutlined />,
    };
    return iconMap[status as keyof typeof iconMap];
  };

  const getStatusText = (status: string) => {
    const textMap = {
      online: '在线',
      offline: '离线',
      unknown: '未知',
      error: '错误',
    };
    return textMap[status as keyof typeof textMap] || status;
  };

  const getPowerStateText = (powerState: string) => {
    const stateMap = {
      on: '开机',
      off: '关机',
      unknown: '未知',
    };
    return stateMap[powerState as keyof typeof stateMap] || powerState;
  };

  const getPowerStateColor = (powerState: string) => {
    const colorMap = {
      on: 'green',
      off: 'default',
      unknown: 'orange',
    };
    return colorMap[powerState as keyof typeof colorMap] || 'default';
  };

  const getGroupName = (groupId: number | null) => {
    if (!groupId) return '未分组';
    const group = groups.find(g => g.id === groupId);
    return group ? group.name : '未知分组';
  };

  const getLEDStatusClass = (ledStatus: { supported: boolean; led_state: string; error: string | null } | null) => {
    if (!ledStatus || !ledStatus.supported) return 'led-unknown';
    if (ledStatus.led_state === 'On' || ledStatus.led_state === 'Lit') return 'led-on';
    if (ledStatus.led_state === 'Off') return 'led-off';
    return 'led-unknown';
  };

  const handleLEDLightClick = async () => {
    if (!ledStatus || !ledStatus.supported || !server || server.status !== 'online') return;
    
    try {
      setLedLoading(true);
      if (ledStatus.led_state === 'On' || ledStatus.led_state === 'Lit') {
        await serverService.turnOffLED(server.id);
        message.success('LED已关闭');
      } else {
        await serverService.turnOnLED(server.id);
        message.success('LED已开启');
      }
      await loadLEDStatus();
    } catch (error) {
      message.error(ledStatus.led_state === 'On' || ledStatus.led_state === 'Lit' ? '关闭LED失败' : '开启LED失败');
    } finally {
      setLedLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (!server) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Text type="danger">服务器不存在或加载失败</Text>
        </div>
      </Card>
    );
  }

  return (
    <div className="server-detail-container">
      <BackTop />

      {/* 返回按钮和标题 */}
      <div className="server-detail-header">
        <Space size="large">
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/servers')}
            type="default"
          >
            返回列表
          </Button>
          <div>
            <Title level={2}>
              {server.name}
            </Title>
          </div>
        </Space>
        <Space>
          <Tooltip title="编辑服务器信息">
            <Button icon={<EditOutlined />} onClick={() => navigate(`/servers/${id}/edit`)}>
              编辑
            </Button>
          </Tooltip>
          <Tooltip title="删除服务器">
            <Button icon={<DeleteOutlined />} danger onClick={handleDelete} loading={powerLoading}>
              删除
            </Button>
          </Tooltip>
        </Space>
      </div>

      {/* 主要状态卡片 */}
      <Row gutter={16} className="status-cards-row">
        {/* BMC状态卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              <Badge
                color={getStatusColor(server.status)}
                text={
                  <span className="status-card-text">
                    {getStatusIcon(server.status)} {getStatusText(server.status)}
                  </span>
                }
              />
            </div>
            <Text className="status-card-label">BMC状态</Text>
          </Card>
        </Col>

        {/* 电源状态卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              <PoweroffOutlined className="status-card-icon-inner" />
              <Tag color={getPowerStateColor(server.power_state)}>
                {getPowerStateText(server.power_state)}
              </Tag>
            </div>
            <Text className="status-card-label">电源状态</Text>
          </Card>
        </Col>

        {/* 监控状态卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              <Tag color={server.monitoring_enabled ? 'blue' : 'default'}>
                {server.monitoring_enabled ? '已启用' : '未启用'}
              </Tag>
            </div>
            <Text className="status-card-label">监控状态</Text>
          </Card>
        </Col>

        {/* Redfish状态卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              {server.redfish_supported ? (
                <>
                  <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '20px', marginRight: '8px' }} />
                  <Text className="status-card-version">
                    {server.redfish_version || 'N/A'}
                  </Text>
                </>
              ) : (
                <ExclamationCircleOutlined style={{ color: server.redfish_supported === false ? '#f5222d' : '#faad14', fontSize: '20px' }} />
              )}
            </div>
            <Text className="status-card-label">
              {server.redfish_supported ? 'Redfish支持' : server.redfish_supported === false ? '不支持Redfish' : 'Redfish未知'}
            </Text>
          </Card>
        </Col>

        {/* LED状态卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              <div 
                className={`led-light ${getLEDStatusClass(ledStatus)}`}
                onClick={handleLEDLightClick}
              >
                <BulbOutlined />
              </div>
            </div>
            <Text className="status-card-label">
              {ledStatus ? (
                ledStatus.led_state === 'On' || ledStatus.led_state === 'Lit' ? 'LED已开启' : 
                ledStatus.led_state === 'Off' ? 'LED已关闭' : 'LED未知'
              ) : 'LED状态未知'}
            </Text>
          </Card>
        </Col>

        {/* 分组卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              <Tag color="blue">{getGroupName(server.group_id)}</Tag>
            </div>
            <Text className="status-card-label">服务器分组</Text>
          </Card>
        </Col>
      </Row>

      {/* 详细信息 */}
      <Card title="基本信息" className="detail-card">
        <Descriptions column={{ xxl: 2, xl: 2, lg: 2, md: 1, sm: 1, xs: 1 }} bordered>
          <Descriptions.Item label="服务器名称">
            <Text strong>{server.name}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="IPMI地址">
            <Text copyable>{server.ipmi_ip}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="IPMI端口">
            <Text>{server.ipmi_port}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="IPMI用户名">
            <Text copyable>{server.ipmi_username}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="生产厂商">
            <Text>{server.manufacturer || '-'}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="服务器型号">
            <Text>{server.model || '-'}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="序列号">
            <Text copyable={!!server.serial_number}>{server.serial_number || '-'}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="所属分组">
            <Tag color="blue">{getGroupName(server.group_id)}</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 电源控制 */}
      <Card title="电源控制" className="detail-card">
        <div className="power-control-group">
          <Space wrap>
            <Button
              icon={<PoweroffOutlined />}
              onClick={() => handlePowerControl('on')}
              loading={powerLoading}
              type="primary"
              disabled={server.status !== 'online'}
            >
              开机
            </Button>
            <Button
              icon={<PoweroffOutlined />}
              onClick={() => handlePowerControl('off')}
              loading={powerLoading}
              disabled={server.status !== 'online'}
            >
              关机
            </Button>
            <Button
              icon={<SwapOutlined />}
              onClick={() => handlePowerControl('restart')}
              loading={powerLoading}
              disabled={server.status !== 'online'}
            >
              重启
            </Button>
            <Button
              icon={<PoweroffOutlined />}
              onClick={() => handlePowerControl('force_off')}
              loading={powerLoading}
              danger
              disabled={server.status !== 'online'}
            >
              强制关机
            </Button>
            <Button
              icon={<SwapOutlined />}
              onClick={() => handlePowerControl('force_restart')}
              loading={powerLoading}
              danger
              disabled={server.status !== 'online'}
            >
              强制重启
            </Button>
          </Space>
          <div className="power-control-note">
            <Text type="secondary">
              {server.status !== 'online' ? '服务器离线或错误，无法进行电源控制操作' : '所有操作均可正常执行'}
            </Text>
          </div>
        </div>
      </Card>

      {/* 状态和时间信息 */}
      <Card title="状态信息" className="detail-card">
        <Descriptions column={{ xxl: 2, xl: 2, lg: 2, md: 1, sm: 1, xs: 1 }} bordered>
          <Descriptions.Item label="BMC状态">
            <Badge
              color={getStatusColor(server.status)}
              text={getStatusText(server.status)}
            />
          </Descriptions.Item>
          <Descriptions.Item label="电源状态">
            <Tag color={getPowerStateColor(server.power_state)}>
              {getPowerStateText(server.power_state)}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="监控状态">
            <Tag color={server.monitoring_enabled ? 'blue' : 'default'}>
              {server.monitoring_enabled ? '已启用' : '未启用'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Redfish支持">
            <Tag color={server.redfish_supported ? 'green' : server.redfish_supported === false ? 'red' : 'orange'}>
              {server.redfish_supported ? '支持' : server.redfish_supported === false ? '不支持' : '未知'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Redfish版本">
            <Text>{server.redfish_version || 'N/A'}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="LED状态">
            <Text>
              {ledStatus ? (
                <Tag color={ledStatus.led_state === 'On' || ledStatus.led_state === 'Lit' ? 'green' : ledStatus.led_state === 'Off' ? 'default' : 'orange'}>
                  {ledStatus.led_state}
                </Tag>
              ) : (
                '未知'
              )}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="最后更新">
            <Text>
              <ClockCircleOutlined style={{ marginRight: '4px' }} />
              {server.last_seen
                ? new Date(server.last_seen).toLocaleString('zh-CN')
                : '暂无记录'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            <Text>
              {new Date(server.created_at).toLocaleString('zh-CN')}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            <Text>
              {new Date(server.updated_at).toLocaleString('zh-CN')}
            </Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 描述和标签 */}
      {(server.description || server.tags) && (
        <Card title="附加信息" className="detail-card">
          {server.description && (
            <>
              <div className="additional-info-section">
                <Text strong>描述：</Text>
                <div className="additional-info-content">
                  <Text>{server.description}</Text>
                </div>
              </div>
              <Divider />
            </>
          )}
          {server.tags && (
            <>
              <Text strong>标签：</Text>
              <div className="additional-info-tags">
                <Space wrap>
                  {server.tags.split(',').map((tag, index) => (
                    <Tag key={index} color="blue">
                      {tag.trim()}
                    </Tag>
                  ))}
                </Space>
              </div>
            </>
          )}
        </Card>
      )}

      {/* LED控制 */}
      <Card title="LED控制" className="detail-card">
        <div className="led-control-group">
          <Space>
            <Button
              type="primary"
              onClick={handleTurnOnLED}
              loading={ledLoading}
              disabled={!ledStatus || !ledStatus.supported || server.status !== 'online'}
            >
              点亮LED
            </Button>
            <Button
              onClick={handleTurnOffLED}
              loading={ledLoading}
              disabled={!ledStatus || !ledStatus.supported || server.status !== 'online'}
            >
              关闭LED
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadLEDStatus}
              loading={ledLoading}
            >
              刷新LED状态
            </Button>
          </Space>
          <div className="led-control-status">
            {!ledStatus ? (
              <Text type="secondary">正在加载LED状态...</Text>
            ) : !ledStatus.supported ? (
              <Text type="warning">服务器不支持LED控制或BMC不支持Redfish</Text>
            ) : server.status !== 'online' ? (
              <Text type="warning">服务器离线，无法控制LED</Text>
            ) : (
              <Text type="secondary">
                当前LED状态: {ledStatus.led_state === 'Lit' ? 'On (Lit)' : ledStatus.led_state}
              </Text>
            )}
          </div>
        </div>
      </Card>

      {/* 操作按钮 */}
      <div className="detail-action-footer">
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleUpdateStatus}
            loading={powerLoading}
          >
            刷新状态
          </Button>
          <Button type="primary" onClick={() => navigate(`/servers/${id}/edit`)}>
            编辑信息
          </Button>
          <Button onClick={() => navigate('/servers')}>
            返回列表
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default ServerDetail;
