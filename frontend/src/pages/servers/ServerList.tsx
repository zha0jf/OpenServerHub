import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Select,
  message,
  Space,
  Tag,
  Card,
  Row,
  Col,
  Typography,
  Divider,
  Popconfirm,
  Tooltip,
  Dropdown,
  Menu,
  Alert
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
  PoweroffOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  DownOutlined,
  SwapOutlined
} from '@ant-design/icons';
import { serverService } from '../../services/server';
import { Server, CreateServerRequest, UpdateServerRequest, ServerGroup, PowerAction, BatchPowerRequest, BatchUpdateMonitoringRequest } from '../../types';
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
  const [servers, setServers] = useState<Server[]>([]);
  const [groups, setGroups] = useState<ServerGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [groupModalVisible, setGroupModalVisible] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [changingGroupServer, setChangingGroupServer] = useState<Server | null>(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [form] = Form.useForm();
  const [groupForm] = Form.useForm();
  const [selectedServerIds, setSelectedServerIds] = useState<number[]>([]);

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

  const handleAdd = () => {
    setEditingServer(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (server: Server) => {
    setEditingServer(server);
    form.setFieldsValue({
      ...server,
      ipmi_port: server.ipmi_port || 623,
      monitoring_enabled: server.monitoring_enabled || false
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await serverService.deleteServer(id);
      message.success('服务器删除成功');
      loadServers();
    } catch (error) {
      message.error('服务器删除失败');
    }
  };

  const handleRefreshStatus = async (id: number) => {
    try {
      setLoading(true);
      await serverService.updateServerStatus(id);
      message.success('服务器状态刷新成功');
      loadServers();
    } catch (error) {
      message.error('服务器状态刷新失败');
    } finally {
      setLoading(false);
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
    if (selectedServerIds.length === 0) {
      message.warning('请选择要操作的服务器');
      return;
    }
    
    // 设置为批量模式
    setChangingGroupServer({ id: -1, name: `${selectedServerIds.length}台服务器` } as Server);
    groupForm.resetFields();
    setGroupModalVisible(true);
  };

  const handleBatchGroupSubmit = async (values: { group_id?: number }) => {
    if (selectedServerIds.length === 0) return;
    
    try {
      setBatchLoading(true);
      
      // 批量更新服务器分组
      const updatePromises = selectedServerIds.map(serverId => 
        serverService.updateServer(serverId, {
          group_id: values.group_id || undefined
        })
      );
      
      await Promise.all(updatePromises);
      
      const groupName = values.group_id 
        ? groups.find(g => g.id === values.group_id)?.name || '未知分组'
        : '未分组';
      
      message.success(`${selectedServerIds.length}台服务器已批量移动到 ${groupName}`);
      setGroupModalVisible(false);
      setSelectedServerIds([]);
      loadServers();
    } catch (error) {
      message.error('批量分组切换失败');
    } finally {
      setBatchLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingServer) {
        // 更新服务器
        const updateData: UpdateServerRequest = {
          ...values,
          ipmi_port: values.ipmi_port || 623
        };
        await serverService.updateServer(editingServer.id, updateData);
        message.success('服务器更新成功');
      } else {
        // 创建服务器
        const createData: CreateServerRequest = {
          ...values,
          ipmi_port: values.ipmi_port || 623
        };
        await serverService.createServer(createData);
        message.success('服务器创建成功');
      }
      setModalVisible(false);
      form.resetFields();
      loadServers();
    } catch (error: any) {
      message.error(editingServer ? '服务器更新失败' : '服务器创建失败');
    }
  };

  const handleBatchPower = async (action: PowerAction) => {
    if (selectedServerIds.length === 0) {
      message.warning('请先选择服务器');
      return;
    }

    try {
      setLoading(true);
      const result = await serverService.batchPowerControl({
        server_ids: selectedServerIds,
        action
      });
      
      message.success(`批量${action === 'on' ? '开机' : action === 'off' ? '关机' : '重启'}操作完成`);
      setSelectedServerIds([]);
      loadServers();
    } catch (error) {
      message.error('批量电源操作失败');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchUpdateMonitoring = async (monitoringEnabled: boolean) => {
    if (selectedServerIds.length === 0) {
      message.warning('请先选择服务器');
      return;
    }

    try {
      setLoading(true);
      const result = await serverService.batchUpdateMonitoring({
        server_ids: selectedServerIds,
        monitoring_enabled: monitoringEnabled
      });
      
      message.success(`批量${monitoringEnabled ? '启用' : '禁用'}监控操作完成`);
      setSelectedServerIds([]);
      loadServers();
    } catch (error) {
      message.error(`批量${monitoringEnabled ? '启用' : '禁用'}监控操作失败`);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedServerIds.length === 0) {
      message.warning('请选择要删除的服务器');
      return;
    }

    Modal.confirm({
      title: '确认批量删除?',
      content: `您确定要删除选中的 ${selectedServerIds.length} 台服务器吗？此操作不可恢复。`,
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
          for (const serverId of selectedServerIds) {
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
          setSelectedServerIds([]);
          await loadServers();

        } catch (error) {
          message.error('批量删除操作失败');
        } finally {
          setBatchLoading(false);
        }
      }
    });
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'online':
        return <Tag icon={<CheckCircleOutlined />} color="success">在线</Tag>;
      case 'offline':
        return <Tag icon={<CloseCircleOutlined />} color="error">离线</Tag>;
      case 'error':
        return <Tag icon={<CloseCircleOutlined />} color="error">错误</Tag>;
      default:
        return <Tag icon={<QuestionCircleOutlined />} color="default">未知</Tag>;
    }
  };

  const getPowerStateTag = (powerState: string) => {
    switch (powerState) {
      case 'on':
        return <Tag color="green">开机</Tag>;
      case 'off':
        return <Tag color="red">关机</Tag>;
      default:
        return <Tag color="default">未知</Tag>;
    }
  };

  const getMonitoringTag = (enabled: boolean) => {
    return enabled ? 
      <Tag color="blue">已启用</Tag> : 
      <Tag color="default">未启用</Tag>;
  };

  const getGroupTag = (groupId: number) => {
    if (!groupId) return <Tag color="default">未分组</Tag>;
    const group = groups.find(g => g.id === groupId);
    return group ? <Tag color="blue">{group.name}</Tag> : <Tag color="default">未知分组</Tag>;
  };

  const columns: ColumnsType<Server> = [
    {
      title: '服务器名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'IPMI地址',
      dataIndex: 'ipmi_ip',
      key: 'ipmi_ip',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
      filters: [
        { text: '在线', value: 'online' },
        { text: '离线', value: 'offline' },
        { text: '错误', value: 'error' },
        { text: '未知', value: 'unknown' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: '电源状态',
      dataIndex: 'power_state',
      key: 'power_state',
      render: (powerState: string) => getPowerStateTag(powerState),
      filters: [
        { text: '开机', value: 'on' },
        { text: '关机', value: 'off' },
        { text: '未知', value: 'unknown' },
      ],
      onFilter: (value, record) => record.power_state === value,
    },
    {
      title: '监控状态',
      dataIndex: 'monitoring_enabled',
      key: 'monitoring_enabled',
      render: (enabled: boolean) => getMonitoringTag(enabled),
      filters: [
        { text: '已启用', value: true },
        { text: '未启用', value: false },
      ],
      onFilter: (value, record) => record.monitoring_enabled === value,
    },
    {
      title: '分组',
      dataIndex: 'group_id',
      key: 'group_id',
      render: (groupId: number) => getGroupTag(groupId),
      filters: groups.map(group => ({ text: group.name, value: group.id })),
      onFilter: (value, record) => record.group_id === value,
    },
    {
      title: '最后更新',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date: string) => new Date(date).toLocaleString(),
      sorter: (a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 200,
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="刷新状态">
            <Button 
              icon={<SyncOutlined />} 
              onClick={() => handleRefreshStatus(record.id)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button 
              icon={<EditOutlined />} 
              onClick={() => handleEdit(record)}
              size="small"
            />
          </Tooltip>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'change_group',
                  label: '切换分组',
                  icon: <SwapOutlined />,
                  onClick: () => handleChangeGroup(record),
                },
                {
                  key: 'delete',
                  label: '删除',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: () => {
                    Modal.confirm({
                      title: '确定要删除这台服务器吗？',
                      content: `您确定要删除服务器 "${record.name}" 吗？此操作不可恢复。`,
                      okText: '确定',
                      cancelText: '取消',
                      onOk: () => handleDelete(record.id),
                    });
                  },
                },
              ]
            }}
            trigger={['click']}
          >
            <Button size="small">更多</Button>
          </Dropdown>
        </Space>
      ),
    },
  ];

  const batchMonitoringMenu = (
    <Menu>
      <Menu.Item key="enable" onClick={() => handleBatchUpdateMonitoring(true)}>
        启用监控
      </Menu.Item>
      <Menu.Item key="disable" onClick={() => handleBatchUpdateMonitoring(false)}>
        禁用监控
      </Menu.Item>
    </Menu>
  );

  const batchPowerMenu = (
    <Menu>
      <Menu.Item key="on" onClick={() => handleBatchPower('on')}>
        批量开机
      </Menu.Item>
      <Menu.Item key="off" onClick={() => handleBatchPower('off')}>
        批量关机
      </Menu.Item>
      <Menu.Item key="restart" onClick={() => handleBatchPower('restart')}>
        批量重启
      </Menu.Item>
    </Menu>
  );

  return (
    <div>
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Title level={2} style={{ margin: 0 }}>服务器管理</Title>
          </Col>
          <Col>
            <Space>
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={handleAdd}
              >
                添加服务器
              </Button>
              <Dropdown overlay={batchPowerMenu} disabled={selectedServerIds.length === 0}>
                <Button 
                  icon={<PoweroffOutlined />} 
                >
                  批量电源操作 <DownOutlined />
                </Button>
              </Dropdown>
              <Dropdown overlay={batchMonitoringMenu} disabled={selectedServerIds.length === 0}>
                <Button 
                  icon={<EyeOutlined />} 
                >
                  批量监控操作 <DownOutlined />
                </Button>
              </Dropdown>
              <Button
                icon={<SwapOutlined />}
                onClick={handleBatchChangeGroup}
                disabled={selectedServerIds.length === 0}
              >
                批量切换分组
              </Button>
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
                disabled={selectedServerIds.length === 0}
              >
                批量删除
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 批量操作栏 */}
        {selectedServerIds.length > 0 && (
          <div style={{ marginBottom: 16, padding: 16, backgroundColor: '#f5f5f5', borderRadius: 6 }}>
            <Space>
              <span>已选中 {selectedServerIds.length} 台服务器</span>
              <Button onClick={() => setSelectedServerIds([])}>
                取消选择
              </Button>
            </Space>
          </div>
        )}

        <Table
          columns={columns}
          dataSource={servers}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1200 }}
          rowSelection={{
            selectedRowKeys: selectedServerIds,
            onChange: (selectedRowKeys) => {
              setSelectedServerIds(selectedRowKeys as number[]);
            },
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
          }}
        />
      </Card>

      <Modal
        title={editingServer ? "编辑服务器" : "添加服务器"}
        visible={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
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
              { required: true, message: '请输入IPMI地址' },
              {
                pattern: VALIDATION_RULES.ipmiIp.pattern,
                message: '请输入有效的IP地址',
              },
            ]}
            hasFeedback
          >
            <Input placeholder="请输入IPMI地址（格式：192.168.1.100）" />
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
        visible={groupModalVisible}
        onCancel={() => setGroupModalVisible(false)}
        onOk={() => groupForm.submit()}
        confirmLoading={batchLoading}
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
        </Form>
      </Modal>
    </div>
  );
};

export default ServerList;