import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Space,
  Typography,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Select,
  message,
  Popconfirm,
  Card,
  Dropdown
} from 'antd';
import './ServerList.css';
import {
  PlusOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  SwapOutlined,
  MoreOutlined,
  EyeOutlined
} from '@ant-design/icons';
import { serverService } from '../../services/server';
import { Server, ServerGroup, CreateServerRequest, PowerAction, BatchPowerRequest, UpdateServerRequest } from '../../types';
import { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Option } = Select;

// 验证规则常量，与后端保持一致
const VALIDATION_RULES = {
  name: {
    minLength: 1,
    maxLength: 100,
  },
  ipmiIp: {
    pattern: /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
  },
  ipmiUsername: {
    minLength: 1,
    maxLength: 50,
  },
  ipmiPassword: {
    minLength: 1,
    maxLength: 128,
  },
  ipmiPort: {
    min: 1,
    max: 65535,
  },
  manufacturer: {
    maxLength: 100,
  },
  model: {
    maxLength: 100,
  },
  serialNumber: {
    maxLength: 100,
  },
  description: {
    maxLength: 500,
  },
  tags: {
    maxLength: 200,
  },
};

const ServerList: React.FC = () => {
  const navigate = useNavigate();
  const [servers, setServers] = useState<Server[]>([]);
  const [groups, setGroups] = useState<ServerGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [groupModalVisible, setGroupModalVisible] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [changingGroupServer, setChangingGroupServer] = useState<Server | null>(null);
  const [refreshingStatus, setRefreshingStatus] = useState<number | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);
  const [form] = Form.useForm();
  const [groupForm] = Form.useForm();

  // 处理访问BMC界面
  const handleAccessBMC = (server: Server) => {
    // 创建一个提示，告知用户即将跳转到BMC界面
    Modal.info({
      title: '访问BMC管理界面',
      content: (
        <div>
          <p>即将在新标签页中打开服务器 {server.name} 的BMC管理界面</p>
          <p>IP地址: {server.ipmi_ip}</p>
          <p>
            用户名: 
            <span 
              style={{fontWeight: 'bold', color: '#1890ff', cursor: 'pointer', marginLeft: '5px', padding: '2px 4px', border: '1px dashed #1890ff', borderRadius: '4px'}}
              onClick={() => {
                // 使用更兼容的方法复制文本
                const textToCopy = server.ipmi_username;
                
                // 检查是否支持现代Clipboard API
                if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                  navigator.clipboard.writeText(textToCopy).then(() => {
                    message.success('用户名已复制到剪贴板');
                  }).catch(() => {
                    // 如果现代API失败，回退到传统方法
                    fallbackCopyTextToClipboard(textToCopy);
                  });
                } else {
                  // 使用传统方法
                  fallbackCopyTextToClipboard(textToCopy);
                }
              }}
            >
              {server.ipmi_username}
            </span>
            <span style={{marginLeft: '10px', fontSize: '12px', color: '#888'}}>(点击复制)</span>
          </p>
          <div style={{marginTop: '10px', padding: '10px', backgroundColor: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: '4px'}}>
            <p style={{margin: 0, color: '#52c41a'}}><strong>提示:</strong> 密码需要手动输入</p>
          </div>
        </div>
      ),
      onOk() {
        // 在新标签页中打开BMC界面
        const bmcUrl = `https://${server.ipmi_ip}`;
        const newWindow = window.open(bmcUrl, '_blank');
        
        // 检查是否成功打开新标签页
        if (!newWindow) {
          message.error('无法打开新标签页，请检查浏览器弹窗阻止设置');
        }
      },
    });
  };

  // 传统的文本复制方法，兼容性更好
  const fallbackCopyTextToClipboard = (text: string) => {
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      
      // 避免滚动到底部
      textArea.style.top = "0";
      textArea.style.left = "0";
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);
      
      if (successful) {
        message.success('用户名已复制到剪贴板');
      } else {
        message.error('复制失败，请手动选择复制');
      }
    } catch (err) {
      message.error('复制失败，请手动选择复制');
    }
  };

  useEffect(() => {
    loadServers();
    loadGroups();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const data = await serverService.getServers();
      setServers(data);
    } catch (error) {
      message.error('加载服务器列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      const data = await serverService.getServerGroups();
      setGroups(data);
    } catch (error) {
      message.error('加载分组列表失败');
    }
  };

  const handleUpdateStatus = async (server: Server) => {
    try {
      setRefreshingStatus(server.id);
      await serverService.updateServerStatus(server.id);
      message.success('状态更新成功');
      loadServers();
    } catch (error) {
      message.error('状态更新失败');
    } finally {
      setRefreshingStatus(null);
    }
  };

  const handleCreateServer = () => {
    setEditingServer(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEditServer = (server: Server) => {
    setEditingServer(server);
    form.setFieldsValue({
      ...server,
      ipmi_port: server.ipmi_port || 623,
      monitoring_enabled: server.monitoring_enabled || false
    });
    setModalVisible(true);
  };

  const handleDeleteServer = async (server: Server) => {
    try {
      await serverService.deleteServer(server.id);
      message.success('服务器删除成功');
      loadServers();
    } catch (error) {
      message.error('服务器删除失败');
    }
  };

  // 处理分组切换
  const handleChangeGroup = (server: Server) => {
    setChangingGroupServer(server);
    groupForm.setFieldsValue({ group_id: server.group_id });
    setGroupModalVisible(true);
  };

  const handleGroupSubmit = async (values: { group_id?: number }) => {
    if (!changingGroupServer) return;
    
    try {
      await serverService.updateServer(changingGroupServer.id, {
        group_id: values.group_id || undefined
      });
      
      const groupName = values.group_id 
        ? groups.find(g => g.id === values.group_id)?.name || '未知分组'
        : '未分组';
      
      message.success(`${changingGroupServer.name} 已移动到 ${groupName}`);
      setGroupModalVisible(false);
      loadServers();
    } catch (error) {
      message.error('分组切换失败');
    }
  };

  // 批量切换分组
  const handleBatchChangeGroup = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要操作的服务器');
      return;
    }
    
    // 设置为批量模式
    setChangingGroupServer({ id: -1, name: `${selectedRowKeys.length}台服务器` } as Server);
    groupForm.resetFields();
    setGroupModalVisible(true);
  };

  const handleBatchGroupSubmit = async (values: { group_id?: number }) => {
    if (selectedRowKeys.length === 0) return;
    
    try {
      setBatchLoading(true);
      
      // 批量更新服务器分组
      const updatePromises = selectedRowKeys.map(serverId => 
        serverService.updateServer(serverId, {
          group_id: values.group_id || undefined
        })
      );
      
      await Promise.all(updatePromises);
      
      const groupName = values.group_id 
        ? groups.find(g => g.id === values.group_id)?.name || '未知分组'
        : '未分组';
      
      message.success(`${selectedRowKeys.length}台服务器已批量移动到 ${groupName}`);
      setGroupModalVisible(false);
      setSelectedRowKeys([]);
      loadServers();
    } catch (error) {
      message.error('批量分组切换失败');
    } finally {
      setBatchLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      let createdOrUpdatedServer: Server;
      
      if (editingServer) {
        // 更新服务器
        const updateData: UpdateServerRequest = {
          ...values,
          ipmi_port: values.ipmi_port || 623
        };
        createdOrUpdatedServer = await serverService.updateServer(editingServer.id, updateData);
        message.success('服务器更新成功');
      } else {
        // 创建服务器
        const createData: CreateServerRequest = {
          ...values,
          ipmi_port: values.ipmi_port || 623
        };
        createdOrUpdatedServer = await serverService.createServer(createData);
        message.success('服务器创建成功');
      }
      
      setModalVisible(false);
      
      // 重新加载服务器列表
      await loadServers();
      
      // 自动刷新新创建或更新的服务器状态
      try {
        setRefreshingStatus(createdOrUpdatedServer.id);
        message.loading('正在刷新服务器状态...', 0.5);
        
        await serverService.updateServerStatus(createdOrUpdatedServer.id);
        message.success('服务器状态已自动刷新');
        
        // 再次加载服务器列表以获取最新状态
        await loadServers();
      } catch (statusError) {
        // 状态刷新失败时给出友好提示，但不显示具体错误信息
        message.warning('服务器保存成功，但状态刷新失败，请手动刷新状态');
      } finally {
        setRefreshingStatus(null);
      }
    } catch (error) {
      message.error(editingServer ? '服务器更新失败' : '服务器创建失败');
    }
  };

  const handlePowerControl = async (server: Server, action: PowerAction) => {
    try {
      await serverService.powerControl(server.id, action);
      message.success(`${server.name} 电源${action}操作成功`);
      loadServers(); // 重新加载列表
    } catch (error) {
      message.error('电源操作失败');
    }
  };

  // 批量操作相关函数
  const handleBatchPowerControl = async (action: PowerAction) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要操作的服务器');
      return;
    }

    Modal.confirm({
      title: `确认批量${action === 'on' ? '开机' : action === 'off' ? '关机' : action === 'restart' ? '重启' : action === 'force_restart' ? '强制重启' : '强制关机'}?`,
      content: `将对选中的 ${selectedRowKeys.length} 台服务器执行${action === 'on' ? '开机' : action === 'off' ? '关机' : action === 'restart' ? '重启' : action === 'force_restart' ? '强制重启' : '强制关机'}操作`,
      onOk: async () => {
        try {
          setBatchLoading(true);
          const request: BatchPowerRequest = {
            server_ids: selectedRowKeys,
            action
          };
          
          const response = await serverService.batchPowerControl(request);
          
          // 显示结果统计
          message.success(
            `批量操作完成: 成功${response.success_count}台，失败${response.failed_count}台`
          );
          
          // 显示详细结果
          if (response.failed_count > 0) {
            const failedResults = response.results.filter(r => !r.success);
            Modal.warning({
              title: '部分操作失败',
              content: (
                <div>
                  <p>以下服务器操作失败：</p>
                  <ul>
                    {failedResults.map(result => (
                      <li key={result.server_id}>
                        {result.server_name}: {result.error || result.message}
                      </li>
                    ))}
                  </ul>
                </div>
              ),
              width: 600
            });
          }
          
          // 清除选中状态并重新加载数据
          setSelectedRowKeys([]);
          await loadServers();
          
        } catch (error) {
          message.error('批量操作失败');
        } finally {
          setBatchLoading(false);
        }
      }
    });
  };

  // 批量更新监控状态
  const handleBatchUpdateMonitoring = async (monitoringEnabled: boolean) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要操作的服务器');
      return;
    }

    try {
      setBatchLoading(true);
      const result = await serverService.batchUpdateMonitoring({
        server_ids: selectedRowKeys,
        monitoring_enabled: monitoringEnabled
      });
      
      message.success(`批量${monitoringEnabled ? '启用' : '禁用'}监控操作完成`);
      setSelectedRowKeys([]);
      loadServers();
    } catch (error) {
      message.error(`批量${monitoringEnabled ? '启用' : '禁用'}监控操作失败`);
    } finally {
      setBatchLoading(false);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的服务器');
      return;
    }

    Modal.confirm({
      title: '确认批量删除?',
      content: `您确定要删除选中的 ${selectedRowKeys.length} 台服务器吗？此操作不可恢复。`,
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          setBatchLoading(true);
          let successCount = 0;
          let failedCount = 0;
          const failedResults: Array<{server_name: string, error: string}> = [];

          // 逐个删除选中的服务器
          for (const serverId of selectedRowKeys) {
            try {
              const server = servers.find(s => s.id === serverId);
              if (server) {
                await serverService.deleteServer(serverId);
                successCount++;
              }
            } catch (error) {
              failedCount++;
              const server = servers.find(s => s.id === serverId);
              failedResults.push({
                server_name: server?.name || `ID: ${serverId}`,
                error: error instanceof Error ? error.message : '删除失败'
              });
            }
          }

          // 显示结果统计
          if (failedCount === 0) {
            message.success(`批量删除完成: 成功删除 ${successCount} 台服务器`);
          } else {
            message.warning(`批量删除完成: 成功 ${successCount} 台，失败 ${failedCount} 台`);
            
            // 显示详细失败结果
            Modal.warning({
              title: '部分删除失败',
              content: (
                <div>
                  <p>以下服务器删除失败：</p>
                  <ul>
                    {failedResults.map((result, index) => (
                      <li key={index}>
                        {result.server_name}: {result.error}
                      </li>
                    ))}
                  </ul>
                </div>
              ),
              width: 600
            });
          }

          // 清除选中状态并重新加载数据
          setSelectedRowKeys([]);
          await loadServers();

        } catch (error) {
          message.error('批量删除操作失败');
        } finally {
          setBatchLoading(false);
        }
      }
    });
  };

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => {
      setSelectedRowKeys(keys as number[]);
    },
    getCheckboxProps: (record: Server) => ({
      disabled: record.status === 'error', // 错误状态的服务器不能选中
    }),
  };

  const getStatusTag = (status: string) => {
    const statusMap = {
      online: { color: 'green', text: '在线' },
      offline: { color: 'red', text: '离线' },
      unknown: { color: 'orange', text: '未知' },
      error: { color: 'red', text: '错误' },
    };
    const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
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

  const getMonitoringTag = (enabled: boolean) => {
    return enabled ? 
      <Tag color="blue">已启用</Tag> : 
      <Tag color="default">未启用</Tag>;
  };

  const columns: ColumnsType<Server> = [
    {
      title: '服务器名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Server) => (
        <a onClick={() => navigate(`/servers/${record.id}`)} style={{ cursor: 'pointer' }}>
          {text}
        </a>
      ),
    },
    {
      title: 'IPMI地址',
      dataIndex: 'ipmi_ip',
      key: 'ipmi_ip',
    },
    {
      title: '所属分组',
      dataIndex: 'group_id',
      key: 'group_id',
      render: (groupId: number) => {
        const group = groups.find(g => g.id === groupId);
        return group ? (
          <Tag color="blue">{group.name}</Tag>
        ) : (
          <Tag color="default">未分组</Tag>
        );
      },
    },
    {
      title: 'BMC状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '电源状态',
      dataIndex: 'power_state',
      key: 'power_state',
      width: 100,
      render: (powerState: string) => getPowerStateTag(powerState),
    },
    {
      title: '监控状态',
      dataIndex: 'monitoring_enabled',
      key: 'monitoring_enabled',
      width: 100,
      render: (enabled: boolean) => getMonitoringTag(enabled),
    },
    {
      title: '厂商',
      dataIndex: 'manufacturer',
      key: 'manufacturer',
    },
    {
      title: '型号',
      dataIndex: 'model',
      key: 'model',
    },
    {
      title: '电源操作',
      key: 'power_actions',
      render: (_, server) => {
        return (
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
            <Space size="middle">
              {/* 只在服务器在线且电源状态为关机时显示开机按钮 */}
              {server.status === 'online' && server.power_state === 'off' && (
                <Button
                  size="small"
                  type="primary"
                  icon={<PoweroffOutlined />}
                  onClick={() => handlePowerControl(server, 'on')}
                >
                  开机
                </Button>
              )}
              
              {/* 只在服务器在线且电源状态为开机时显示关机按钮 */}
              {server.status === 'online' && server.power_state === 'on' && (
                <Button
                  size="small"
                  icon={<PoweroffOutlined />}
                  onClick={() => handlePowerControl(server, 'off')}
                >
                  关机
                </Button>
              )}
              
              {/* 只在服务器在线且电源状态为开机时显示重启按钮 */}
              {server.status === 'online' && server.power_state === 'on' && (
                <Button
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={() => handlePowerControl(server, 'restart')}
                >
                  重启
                </Button>
              )}
              
              {/* 更多电源操作下拉菜单 */}
              <Dropdown
                menu={{ 
                  items: [
                    // 刷新状态按钮对所有状态的服务器都显示
                    {
                      key: 'refresh_status',
                      label: refreshingStatus === server.id ? '刷新中...' : '刷新状态',
                      icon: <ReloadOutlined />,
                      onClick: () => handleUpdateStatus(server),
                      disabled: refreshingStatus === server.id,
                    },
                    // 只在服务器在线时显示强制关机按钮
                    ...(server.status === 'online' ? [{
                      key: 'force_off',
                      label: '强制关机',
                      icon: <PoweroffOutlined />,
                      danger: true,
                      onClick: () => handlePowerControl(server, 'force_off'),
                    }] : []),
                    // 只在服务器在线且电源状态为开机时显示强制重启按钮
                    ...(server.status === 'online' && server.power_state === 'on' ? [{
                      key: 'force_restart',
                      label: '强制重启',
                      icon: <ThunderboltOutlined />,
                      danger: true,
                      onClick: () => handlePowerControl(server, 'force_restart'),
                    }] : []),
                  ].filter(Boolean)
                }}
                trigger={['click']}
              >
                <Button size="small" icon={<MoreOutlined />} />
              </Dropdown>
            </Space>
          </div>
        );
      },
    },
    {
      title: '管理操作',
      key: 'management_actions',
      render: (_, server) => {
        return (
          <Space size="middle">
            {/* 查看详情按钮对所有状态的服务器都显示 */}
            <Button
              size="small"
              icon={<EyeOutlined />}
              type="primary"
              onClick={() => navigate(`/servers/${server.id}`)}
            >
              查看详情
            </Button>
            
            {/* 编辑按钮对所有状态的服务器都显示 */}
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditServer(server)}
            >
              编辑
            </Button>
            
            {/* 访问BMC按钮 - 只对在线状态的服务器显示 */}
            {server.status === 'online' && (
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => handleAccessBMC(server)}
              >
                访问BMC
              </Button>
            )}
            
            {/* 更多管理操作下拉菜单 */}
            <Dropdown
              menu={{ 
                items: [
                  // 切换分组按钮对所有状态的服务器都显示
                  {
                    key: 'change_group',
                    label: '切换分组',
                    icon: <SwapOutlined />,
                    onClick: () => handleChangeGroup(server),
                  },
                  // 删除按钮添加到下拉菜单中
                  {
                    key: 'delete',
                    label: '删除',
                    icon: <DeleteOutlined />,
                    danger: true,
                    onClick: () => {
                      Modal.confirm({
                        title: '确定要删除这台服务器吗？',
                        content: `您确定要删除服务器 "${server.name}" 吗？此操作不可恢复。`,
                        okText: '确定',
                        cancelText: '取消',
                        onOk: () => handleDeleteServer(server),
                      });
                    },
                  },
                ]
              }}
              trigger={['click']}
            >
              <Button size="small" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2} style={{ margin: 0 }}>服务器管理</Title>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadServers}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateServer}
            >
              添加服务器
            </Button>
          </Space>
        </div>

        {/* 批量操作栏 */}
        {selectedRowKeys.length > 0 && (
          <div style={{ marginBottom: 16, padding: 16, backgroundColor: '#f5f5f5', borderRadius: 6 }}>
            <Space>
              <span>已选中 {selectedRowKeys.length} 台服务器</span>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                loading={batchLoading}
                onClick={() => handleBatchPowerControl('on')}
              >
                批量开机
              </Button>
              <Button
                icon={<PoweroffOutlined />}
                loading={batchLoading}
                onClick={() => handleBatchPowerControl('off')}
              >
                批量关机
              </Button>
              <Button
                icon={<ReloadOutlined />}
                loading={batchLoading}
                onClick={() => handleBatchPowerControl('restart')}
              >
                批量重启
              </Button>
              <Button
                danger
                loading={batchLoading}
                onClick={() => handleBatchPowerControl('force_restart')}
              >
                强制重启
              </Button>
              <Button
                danger
                loading={batchLoading}
                onClick={() => handleBatchPowerControl('force_off')}
              >
                强制关机
              </Button>
              <Button
                icon={<SwapOutlined />}
                onClick={handleBatchChangeGroup}
              >
                批量切换分组
              </Button>
              <Button
                icon={<EyeOutlined />}
                loading={batchLoading}
                onClick={() => handleBatchUpdateMonitoring(true)}
              >
                批量启用监控
              </Button>
              <Button
                icon={<EyeOutlined />}
                loading={batchLoading}
                onClick={() => handleBatchUpdateMonitoring(false)}
              >
                批量禁用监控
              </Button>
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
              >
                批量删除
              </Button>
              <Button onClick={() => setSelectedRowKeys([])}>
                取消选择
              </Button>
            </Space>
          </div>
        )}

        <Table
          columns={columns}
          dataSource={servers}
          rowKey="id"
          rowSelection={rowSelection}
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range?.[0]}-${range?.[1]} 条，共 ${total} 条记录`,
          }}
          style={{
            borderSpacing: '0 4px',
            borderCollapse: 'separate',
          }}
          rowClassName={(record, index) => {
            return index % 2 === 0 ? 'table-row-even' : 'table-row-odd';
          }}
        />
      </Card>

      <Modal
        title={editingServer ? '编辑服务器' : '添加服务器'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          validateTrigger={['onChange', 'onBlur']}
          initialValues={{
            ipmi_port: 623,
            monitoring_enabled: false
          }}
        >
          <Form.Item
            name="name"
            label="服务器名称"
            rules={[
              { required: true, message: '请输入服务器名称' },
              { 
                min: VALIDATION_RULES.name.minLength,
                max: VALIDATION_RULES.name.maxLength,
                message: `服务器名称长度应为${VALIDATION_RULES.name.minLength}-${VALIDATION_RULES.name.maxLength}个字符`
              },
            ]}
            hasFeedback
          >
            <Input 
              placeholder="请输入服务器名称"
              showCount
              maxLength={VALIDATION_RULES.name.maxLength}
            />
          </Form.Item>

          <Form.Item
            name="ipmi_ip"
            label="IPMI IP地址"
            rules={[
              { required: true, message: '请输入IPMI IP地址' },
              {
                pattern: VALIDATION_RULES.ipmiIp.pattern,
                message: '请输入有效的IP地址',
              },
            ]}
            hasFeedback
          >
            <Input placeholder="请输入IPMI IP地址（格式：192.168.1.100）" />
          </Form.Item>

          <Form.Item
            name="ipmi_username"
            label="IPMI用户名"
            rules={[
              { required: true, message: '请输入IPMI用户名' },
              { 
                min: VALIDATION_RULES.ipmiUsername.minLength,
                max: VALIDATION_RULES.ipmiUsername.maxLength,
                message: `IPMI用户名长度应为${VALIDATION_RULES.ipmiUsername.minLength}-${VALIDATION_RULES.ipmiUsername.maxLength}个字符`
              },
            ]}
            hasFeedback
          >
            <Input 
              placeholder="请输入IPMI用户名"
              showCount
              maxLength={VALIDATION_RULES.ipmiUsername.maxLength}
            />
          </Form.Item>

          <Form.Item
            name="ipmi_password"
            label={editingServer ? "IPMI密码（留空表示不修改）" : "IPMI密码"}
            rules={[
              ...(editingServer ? [] : [{ required: true, message: '请输入IPMI密码' }]),
              { 
                min: VALIDATION_RULES.ipmiPassword.minLength,
                max: VALIDATION_RULES.ipmiPassword.maxLength,
                message: `IPMI密码长度应为${VALIDATION_RULES.ipmiPassword.minLength}-${VALIDATION_RULES.ipmiPassword.maxLength}个字符`
              },
            ]}
            hasFeedback
          >
            <Input.Password 
              placeholder={editingServer ? "留空表示不修改密码" : "请输入IPMI密码"}
              showCount
              maxLength={VALIDATION_RULES.ipmiPassword.maxLength}
            />
          </Form.Item>

          <Form.Item
            name="ipmi_port"
            label="IPMI端口"
            initialValue={623}
            rules={[
              {
                type: 'number',
                min: VALIDATION_RULES.ipmiPort.min,
                max: VALIDATION_RULES.ipmiPort.max,
                message: `IPMI端口应为${VALIDATION_RULES.ipmiPort.min}-${VALIDATION_RULES.ipmiPort.max}之间的数字`,
                transform: (value) => Number(value),
              },
            ]}
            hasFeedback
          >
            <Input 
              type="number" 
              placeholder="IPMI端口，默认623"
              min={VALIDATION_RULES.ipmiPort.min}
              max={VALIDATION_RULES.ipmiPort.max}
            />
          </Form.Item>

          <Form.Item 
            name="monitoring_enabled" 
            label="启用监控"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item 
            name="group_id" 
            label="所属分组"
          >
            <Select 
              placeholder="请选择分组（可选）"
              allowClear
              showSearch
              optionFilterProp="children"
            >
              {groups.map(group => (
                <Option key={group.id} value={group.id}>{group.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item 
            name="description" 
            label="描述"
            rules={[
              { 
                max: VALIDATION_RULES.description.maxLength,
                message: `描述不能超过${VALIDATION_RULES.description.maxLength}个字符`
              },
            ]}
          >
            <Input.TextArea 
              placeholder="服务器描述信息"
              showCount
              maxLength={VALIDATION_RULES.description.maxLength}
              rows={3}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingServer ? '更新' : '创建'}
              </Button>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 分组切换模态框 */}
      <Modal
        title={`切换服务器分组 - ${changingGroupServer?.name}`}
        open={groupModalVisible}
        onCancel={() => setGroupModalVisible(false)}
        footer={null}
        width={400}
      >
        <Form
          form={groupForm}
          layout="vertical"
          onFinish={changingGroupServer?.id === -1 ? handleBatchGroupSubmit : handleGroupSubmit}
        >
          <Form.Item 
            name="group_id" 
            label="新分组"
          >
            <Select 
              placeholder="请选择目标分组（可选择空值设为未分组）"
              allowClear
            >
              {groups.map(group => (
                <Option key={group.id} value={group.id}>{group.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button 
                type="primary" 
                htmlType="submit"
                loading={changingGroupServer?.id === -1 ? batchLoading : false}
              >
                {changingGroupServer?.id === -1 ? '批量切换' : '确认切换'}
              </Button>
              <Button onClick={() => setGroupModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ServerList;