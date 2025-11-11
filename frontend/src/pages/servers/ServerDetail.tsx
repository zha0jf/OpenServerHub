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
  SwapOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  BulbOutlined,
  BulbFilled,
  ThunderboltOutlined,
  ApiOutlined,
  DisconnectOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  CloudServerOutlined
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
  const [monitoringLoading, setMonitoringLoading] = useState(false);
  const [groupModalVisible, setGroupModalVisible] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<number | null>(null);

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

  const getPowerStateIcon = (powerState: string) => {
    switch (powerState) {
      case 'on':
        return <PoweroffOutlined style={{ color: '#52c41a', fontSize: '32px' }} />;
      case 'off':
        return <PoweroffOutlined style={{ color: '#bfbfbf', fontSize: '32px' }} />;
      case 'unknown':
        return <QuestionCircleOutlined style={{ color: '#faad14', fontSize: '32px' }} />;
      default:
        return <PoweroffOutlined style={{ fontSize: '32px' }} />;
    }
  };

  const getBMCStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <ApiOutlined style={{ color: '#52c41a', fontSize: '32px' }} />;
      case 'offline':
        return <DisconnectOutlined style={{ color: '#bfbfbf', fontSize: '32px' }} />;
      case 'unknown':
        return <QuestionCircleOutlined style={{ color: '#faad14', fontSize: '32px' }} />;
      default:
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: '32px' }} />;
    }
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
    if (ledStatus.led_state === 'Blinking') return 'led-blinking';
    return 'led-unknown';
  };

  const handleLEDLightClick = async () => {
    if (!ledStatus || !ledStatus.supported || !server || server.status !== 'online') return;
    
    try {
      setLedLoading(true);
      // On、Lit 状态下点击关闭，其他状态（Off、Blinking）下点击开启
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

  const handleToggleMonitoring = async () => {
    if (!server) return;
    try {
      setMonitoringLoading(true);
      await serverService.updateServer(server.id, {
        monitoring_enabled: !server.monitoring_enabled,
      });
      message.success(server.monitoring_enabled ? '已取消监控' : '已启用监控');
      await loadServerDetail();
    } catch (error) {
      message.error('更新监控状态失败');
    } finally {
      setMonitoringLoading(false);
    }
  };

  const handleChangeGroup = async () => {
    if (!server || selectedGroup === null) return;
    try {
      setMonitoringLoading(true);
      await serverService.updateServer(server.id, {
        group_id: selectedGroup === 0 ? undefined : selectedGroup,
      });
      message.success('分组已更新');
      setGroupModalVisible(false);
      await loadServerDetail();
    } catch (error) {
      message.error('更新分组失败');
    } finally {
      setMonitoringLoading(false);
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
              {getBMCStatusIcon(server.status)}
            </div>
            <Text className="status-card-label">BMC状态</Text>
            <Text className="status-card-value">{getStatusText(server.status)}</Text>
            {/* BMC刷新按钮 - 始终显示 */}
            <div className="status-card-actions-section" style={{ marginTop: '16px' }}>
              <Space size="small" style={{ justifyContent: 'center', width: '100%' }}>
                <Tooltip title="刷新BMC状态">
                  <Button
                    className="status-icon-button refresh-button"
                    shape="circle"
                    icon={<ReloadOutlined />}
                    onClick={handleUpdateStatus}
                    loading={powerLoading}
                  />
                </Tooltip>
              </Space>
            </div>
          </Card>
        </Col>

        {/* 电源状态卡片 */}
        <Col xs={24} sm={12} md={6}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              {getPowerStateIcon(server.power_state)}
            </div>
            <Text className="status-card-label">电源状态</Text>
            <Text className="status-card-value">{getPowerStateText(server.power_state)}</Text>
            <div className="status-card-actions-section" style={{ marginTop: '16px' }}>
              <Space style={{ justifyContent: 'center', width: '100%' }} size="small">
                {/* 开机按钮 - 仅在关机且在线时显示 */}
                {server.power_state === 'off' && server.status === 'online' && (
                  <Tooltip title="开机">
                    <Button
                      className="power-icon-button power-button-on"
                      shape="circle"
                      icon={<PoweroffOutlined />}
                      onClick={() => handlePowerControl('on')}
                      loading={powerLoading}
                    />
                  </Tooltip>
                )}
                {/* 关机按钮 - 仅在开机且在线时显示 */}
                {server.power_state === 'on' && server.status === 'online' && (
                  <Tooltip title="关机">
                    <Button
                      className="power-icon-button power-button-off"
                      shape="circle"
                      icon={<PoweroffOutlined />}
                      onClick={() => handlePowerControl('off')}
                      loading={powerLoading}
                    />
                  </Tooltip>
                )}
                {/* 重启按钮 - 仅在开机且在线时显示 */}
                {server.power_state === 'on' && server.status === 'online' && (
                  <Tooltip title="重启">
                    <Button
                      className="power-icon-button power-button-restart"
                      shape="circle"
                      icon={<SwapOutlined />}
                      onClick={() => handlePowerControl('restart')}
                      loading={powerLoading}
                    />
                  </Tooltip>
                )}
                {/* 强制关机按钮 - 仅在在线时显示 */}
                {server.power_state === 'on' && server.status === 'online' && (
                  <Tooltip title="强制关机">
                    <Button
                      className="power-icon-button power-button-force-off"
                      shape="circle"
                      icon={<ThunderboltOutlined />}
                      onClick={() => handlePowerControl('force_off')}
                      loading={powerLoading}
                    />
                  </Tooltip>
                )}
                {/* 强制重启按钮 - 仅在在线时显示 */}
                {server.power_state === 'on' && server.status === 'online' && (
                  <Tooltip title="强制重启">
                    <Button
                      className="power-icon-button power-button-force-restart"
                      shape="circle"
                      icon={<ThunderboltOutlined />}
                      onClick={() => handlePowerControl('force_restart')}
                      loading={powerLoading}
                    />
                  </Tooltip>
                )}
                {/* 电源状态刷新按钮 - 始终显示 */}
                <Tooltip title="刷新电源状态">
                  <Button
                    className="status-icon-button refresh-button"
                    shape="circle"
                    icon={<ReloadOutlined />}
                    onClick={handleUpdateStatus}
                    loading={powerLoading}
                  />
                </Tooltip>
              </Space>
            </div>
          </Card>
        </Col>

        {/* 监控状态卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              {server.monitoring_enabled ? (
                <EyeOutlined style={{ color: '#52c41a', fontSize: '32px' }} />
              ) : (
                <EyeInvisibleOutlined style={{ color: '#bfbfbf', fontSize: '32px' }} />
              )}
            </div>
            <Text className="status-card-label">监控状态</Text>
            <Text className="status-card-value">{server.monitoring_enabled ? '已启用' : '未启用'}</Text>
            <div className="status-card-actions-section" style={{ marginTop: '16px' }}>
              <Space size="small" style={{ justifyContent: 'center', width: '100%' }}>
                {/* 监控控制按钮 - 始终显示 */}
                <Tooltip title={server.monitoring_enabled ? '取消监控' : '启用监控'}>
                  <Button
                    className={server.monitoring_enabled ? 'status-icon-button status-button-enabled' : 'status-icon-button status-button-disabled'}
                    shape="circle"
                    icon={server.monitoring_enabled ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                    onClick={handleToggleMonitoring}
                    loading={monitoringLoading}
                  />
                </Tooltip>
              </Space>
            </div>
          </Card>
        </Col>

        {/* Redfish状态卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              {server.redfish_supported ? (
                <CloudServerOutlined style={{ color: '#52c41a', fontSize: '32px' }} />
              ) : (
                <CloudServerOutlined style={{ color: server.redfish_supported === false ? '#f5222d' : '#faad14', fontSize: '32px' }} />
              )}
            </div>
            <Text className="status-card-label">
              {server.redfish_supported ? 'Redfish支持' : server.redfish_supported === false ? '不支持Redfish' : 'Redfish未知'}
            </Text>
            {server.redfish_supported && (
              <Text className="status-card-value">{server.redfish_version || 'N/A'}</Text>
            )}
            {/* Redfish状态卡片不包含刷新按钮 */}
          </Card>
        </Col>

        {/* 定位灯状态卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card className="status-card" hoverable>
            <div className="status-card-icon">
              {ledStatus?.supported ? (
                ledStatus.led_state === 'On' || ledStatus.led_state === 'Lit' ? (
                  <BulbFilled style={{ color: '#faad14', fontSize: '32px' }} />
                ) : (
                  <BulbOutlined style={{ color: '#bfbfbf', fontSize: '32px' }} />
                )
              ) : (
                <QuestionCircleOutlined style={{ color: '#faad14', fontSize: '32px' }} />
              )}
            </div>
            <Text className="status-card-label">定位灯</Text>
            <Text className="status-card-value">
              {ledStatus ? (
                ledStatus.led_state === 'On' || ledStatus.led_state === 'Lit' ? '已开启' : 
                ledStatus.led_state === 'Off' ? '已关闭' :
                ledStatus.led_state === 'Blinking' ? '闪烁' : '未知'
              ) : '状态未知'}
            </Text>
            <div className="status-card-actions-section" style={{ marginTop: '16px' }}>
              <Space size="small" style={{ justifyContent: 'center', width: '100%' }}>
                {/* 定位灯控制按钮 - 仅在支持Redfish且在线时显示 */}
                {ledStatus?.supported && server.status === 'online' && (
                  (ledStatus.led_state === 'On' || ledStatus.led_state === 'Lit') ? (
                    <Tooltip title="关闭定位灯">
                      <Button
                        className="status-icon-button led-button-on"
                        shape="circle"
                        icon={<BulbFilled />}
                        onClick={() => handleTurnOffLED()}
                        loading={ledLoading}
                      />
                    </Tooltip>
                  ) : (
                    <Tooltip title="开启定位灯">
                      <Button
                        className="status-icon-button led-button-off"
                        shape="circle"
                        icon={<BulbOutlined />}
                        onClick={() => handleTurnOnLED()}
                        loading={ledLoading}
                      />
                    </Tooltip>
                  )
                )}
                {/* 刷新按钮 - 仅在支持Redfish时显示 */}
                {ledStatus?.supported && (
                  <Tooltip title="刷新状态">
                    <Button
                      className="status-icon-button"
                      shape="circle"
                      icon={<ReloadOutlined />}
                      onClick={() => loadLEDStatus()}
                      loading={ledLoading}
                    />
                  </Tooltip>
                )}
              </Space>
            </div>
          </Card>
        </Col>

        {/* 分组卡片 */}
        {/* 已删除 */}
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
            <Space>
              <Tag color="blue">{getGroupName(server.group_id)}</Tag>
              <Tooltip title="切换分组">
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => {
                    setSelectedGroup(server.group_id);
                    setGroupModalVisible(true);
                  }}
                  loading={monitoringLoading}
                />
              </Tooltip>
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>



      {/* 时间信息 */}
      <Card title="时间信息" className="detail-card">
        <Descriptions column={{ xxl: 3, xl: 3, lg: 2, md: 1, sm: 1, xs: 1 }} bordered>
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
              {new Date(server.created_at + 'Z').toLocaleString('zh-CN')}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            <Text>
              {new Date(server.updated_at + 'Z').toLocaleString('zh-CN')}
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

      {/* 分组选择模态框 */}
      <Modal
        title="切换分组"
        open={groupModalVisible}
        onOk={handleChangeGroup}
        onCancel={() => setGroupModalVisible(false)}
        okText="确定"
        cancelText="取消"
        confirmLoading={monitoringLoading}
      >
        <div style={{ marginBottom: '16px' }}>
          <Text>选择新的分组：</Text>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <Tag
            color={selectedGroup === 0 ? 'blue' : 'default'}
            onClick={() => setSelectedGroup(0)}
            style={{ cursor: 'pointer', padding: '8px', textAlign: 'center' }}
          >
            未分组
          </Tag>
          {groups.map(group => (
            <Tag
              key={group.id}
              color={selectedGroup === group.id ? 'blue' : 'default'}
              onClick={() => setSelectedGroup(group.id)}
              style={{ cursor: 'pointer', padding: '8px', textAlign: 'center' }}
            >
              {group.name}
            </Tag>
          ))}
        </div>
      </Modal>
    </div>
  );
};

export default ServerDetail;
