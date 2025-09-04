import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Typography,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Card,
} from 'antd';
import {
  PlusOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { serverService } from '../../services/server';
import { Server, CreateServerRequest, PowerAction } from '../../types';
import { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Option } = Select;

const ServerList: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [refreshingStatus, setRefreshingStatus] = useState<number | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const data = await serverService.getServers();
      setServers(data);
    } catch (error) {
      // 错误已由全局拦截器处理，这里不需要额外显示
      console.error('加载服务器列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePowerControl = async (server: Server, action: PowerAction) => {
    try {
      await serverService.powerControl(server.id, action);
      message.success(`${server.name} 电源${action}操作成功`);
      loadServers(); // 重新加载列表
    } catch (error) {
      // 错误已由全局拦截器处理
      console.error('电源操作失败:', error);
    }
  };

  const handleUpdateStatus = async (server: Server) => {
    try {
      setRefreshingStatus(server.id);
      await serverService.updateServerStatus(server.id);
      message.success('状态更新成功');
      loadServers();
    } catch (error) {
      // 错误已由全局拦截器处理
      console.error('状态更新失败:', error);
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
    form.setFieldsValue(server);
    setModalVisible(true);
  };

  const handleDeleteServer = async (server: Server) => {
    try {
      await serverService.deleteServer(server.id);
      message.success('服务器删除成功');
      loadServers();
    } catch (error) {
      // 错误已由全局拦截器处理
      console.error('删除失败:', error);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      let createdOrUpdatedServer: Server;
      
      if (editingServer) {
        createdOrUpdatedServer = await serverService.updateServer(editingServer.id, values);
        message.success('服务器更新成功');
      } else {
        createdOrUpdatedServer = await serverService.createServer(values as CreateServerRequest);
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
        console.warn('自动刷新服务器状态失败:', statusError);
        // 状态刷新失败时给出友好提示，但不显示具体错误信息
        message.warning('服务器保存成功，但状态刷新失败，请手动刷新状态');
      } finally {
        setRefreshingStatus(null);
      }
    } catch (error) {
      // 错误已由全局拦截器处理，这里只需记录日志
      console.error('服务器操作失败:', error);
    }
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

  const columns: ColumnsType<Server> = [
    {
      title: '服务器名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '主机名',
      dataIndex: 'hostname',
      key: 'hostname',
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
    },
    {
      title: '电源状态',
      dataIndex: 'power_state',
      key: 'power_state',
      render: (powerState: string) => getPowerStateTag(powerState),
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
      title: '操作',
      key: 'actions',
      render: (_, server) => (
        <Space size="middle">
          <Button
            type="primary"
            size="small"
            icon={<PoweroffOutlined />}
            onClick={() => handlePowerControl(server, 'on')}
            disabled={server.power_state === 'on'}
          >
            开机
          </Button>
          <Button
            size="small"
            icon={<PoweroffOutlined />}
            onClick={() => handlePowerControl(server, 'off')}
            disabled={server.power_state === 'off'}
          >
            关机
          </Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={refreshingStatus === server.id}
            onClick={() => handleUpdateStatus(server)}
          >
            {refreshingStatus === server.id ? '刷新中...' : '刷新状态'}
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditServer(server)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这台服务器吗？"
            onConfirm={() => handleDeleteServer(server)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" icon={<DeleteOutlined />} danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
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

        <Table
          columns={columns}
          dataSource={servers}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
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
        >
          <Form.Item
            name="name"
            label="服务器名称"
            rules={[{ required: true, message: '请输入服务器名称' }]}
          >
            <Input placeholder="请输入服务器名称" />
          </Form.Item>

          <Form.Item
            name="hostname"
            label="主机名"
            rules={[{ required: true, message: '请输入主机名' }]}
          >
            <Input placeholder="请输入主机名" />
          </Form.Item>

          <Form.Item
            name="ipmi_ip"
            label="IPMI地址"
            rules={[
              { required: true, message: '请输入IPMI地址' },
              { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: '请输入有效的IP地址' }
            ]}
          >
            <Input placeholder="请输入IPMI地址" />
          </Form.Item>

          <Form.Item
            name="ipmi_username"
            label="IPMI用户名"
            rules={[{ required: true, message: '请输入IPMI用户名' }]}
          >
            <Input placeholder="请输入IPMI用户名" />
          </Form.Item>

          <Form.Item
            name="ipmi_password"
            label="IPMI密码"
            rules={[{ required: true, message: '请输入IPMI密码' }]}
          >
            <Input.Password placeholder="请输入IPMI密码" />
          </Form.Item>

          <Form.Item
            name="ipmi_port"
            label="IPMI端口"
            initialValue={623}
          >
            <Input type="number" placeholder="IPMI端口，默认623" />
          </Form.Item>

          <Form.Item name="manufacturer" label="厂商">
            <Input placeholder="服务器厂商" />
          </Form.Item>

          <Form.Item name="model" label="型号">
            <Input placeholder="服务器型号" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="服务器描述信息" />
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
    </div>
  );
};

export default ServerList;