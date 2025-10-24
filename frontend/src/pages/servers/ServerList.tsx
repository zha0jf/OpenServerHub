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
  Menu
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
  DownOutlined
} from '@ant-design/icons';
import { serverService } from '../../services/server';
import { Server, CreateServerRequest, UpdateServerRequest, ServerGroup, PowerAction } from '../../types';
import { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Option } = Select;

const ServerList: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [groups, setGroups] = useState<ServerGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [form] = Form.useForm();
  const [batchActionVisible, setBatchActionVisible] = useState(false);
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
      setBatchActionVisible(false);
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
      render: (groupId: number) => {
        if (!groupId) return '-';
        const group = groups.find(g => g.id === groupId);
        return group ? group.name : '-';
      },
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
          <Popconfirm
            title="确定删除此服务器吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button 
                icon={<DeleteOutlined />} 
                danger
                size="small"
              />
            </Tooltip>
          </Popconfirm>
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
            </Space>
          </Col>
        </Row>

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
            rules={[{ required: true, message: '请输入服务器名称' }]}
          >
            <Input placeholder="请输入服务器名称" />
          </Form.Item>

          <Form.Item
            name="ipmi_ip"
            label="IPMI IP地址"
            rules={[{ required: true, message: '请输入IPMI IP地址' }]}
          >
            <Input placeholder="请输入IPMI IP地址" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="ipmi_username"
                label="IPMI用户名"
                rules={[{ required: true, message: '请输入IPMI用户名' }]}
              >
                <Input placeholder="请输入IPMI用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="ipmi_password"
                label="IPMI密码"
                rules={[{ required: true, message: '请输入IPMI密码' }]}
              >
                <Input.Password placeholder="请输入IPMI密码" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="ipmi_port"
                label="IPMI端口"
                rules={[{ required: true, message: '请输入IPMI端口' }]}
              >
                <InputNumber 
                  min={1} 
                  max={65535} 
                  placeholder="请输入IPMI端口" 
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="monitoring_enabled"
                label="启用监控"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="group_id"
            label="分组"
          >
            <Select 
              placeholder="请选择分组" 
              allowClear
              showSearch
              optionFilterProp="children"
            >
              {groups.map(group => (
                <Option key={group.id} value={group.id}>
                  {group.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea placeholder="请输入描述信息" rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ServerList;