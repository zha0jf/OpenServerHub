import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  message,
  Popconfirm,
  Tag,
  Tabs,
  Statistic,
  Row,
  Col,
  Progress,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CloudServerOutlined,
  PoweroffOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { Server, ServerGroup, CreateServerGroupRequest } from '../../types';
import { serverService } from '../../services/server';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const ClusterManagement: React.FC = () => {
  const [groups, setGroups] = useState<ServerGroup[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState<ServerGroup | null>(null);
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('groups');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [groupsData, serversData] = await Promise.all([
        serverService.getServerGroups(),
        serverService.getServers()
      ]);
      setGroups(groupsData);
      setServers(serversData);
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGroup = () => {
    setEditingGroup(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEditGroup = (group: ServerGroup) => {
    setEditingGroup(group);
    form.setFieldsValue(group);
    setModalVisible(true);
  };

  const handleDeleteGroup = async (group: ServerGroup) => {
    try {
      await serverService.deleteServerGroup(group.id);
      message.success('分组删除成功');
      loadData();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async (values: CreateServerGroupRequest) => {
    try {
      if (editingGroup) {
        await serverService.updateServerGroup(editingGroup.id, values);
        message.success('分组更新成功');
      } else {
        await serverService.createServerGroup(values);
        message.success('分组创建成功');
      }
      setModalVisible(false);
      loadData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const getGroupStats = (groupId: number) => {
    const groupServers = servers.filter(server => server.group_id === groupId);
    const total = groupServers.length;
    const online = groupServers.filter(server => server.status === 'online').length;
    const powered = groupServers.filter(server => server.power_state === 'on').length;
    
    return {
      total,
      online,
      powered,
      onlineRate: total > 0 ? Math.round((online / total) * 100) : 0,
      powerRate: total > 0 ? Math.round((powered / total) * 100) : 0,
    };
  };

  const groupColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '分组名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, group: ServerGroup) => (
        <Space>
          <CloudServerOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => desc || '-',
    },
    {
      title: '服务器统计',
      key: 'stats',
      render: (_: any, group: ServerGroup) => {
        const stats = getGroupStats(group.id);
        return (
          <Space direction="vertical" size={2}>
            <Text>总数: {stats.total}</Text>
            <Text type={stats.online === stats.total ? 'success' : 'warning'}>
              在线: {stats.online}/{stats.total}
            </Text>
            <Text type={stats.powered === stats.total ? 'success' : 'secondary'}>
              开机: {stats.powered}/{stats.total}
            </Text>
          </Space>
        );
      },
    },
    {
      title: '在线率',
      key: 'onlineRate',
      render: (_: any, group: ServerGroup) => {
        const stats = getGroupStats(group.id);
        return (
          <Progress 
            percent={stats.onlineRate}
            size="small"
            status={stats.onlineRate === 100 ? 'success' : stats.onlineRate > 50 ? 'active' : 'exception'}
          />
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time + 'Z').toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, group: ServerGroup) => (
        <Space size="middle">
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditGroup(group)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个分组吗？"
            description="删除分组不会删除其中的服务器，但会移除服务器的分组关联。"
            onConfirm={() => handleDeleteGroup(group)}
            okText="确定"
            cancelText="取消"
          >
            <Button 
              size="small" 
              icon={<DeleteOutlined />} 
              danger
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const serverColumns = [
    {
      title: '服务器名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, server: Server) => (
        <Space>
          <CloudServerOutlined />
          <Text strong>{name}</Text>
        </Space>
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusConfig = {
          online: { color: 'success', icon: <CheckCircleOutlined />, text: '在线' },
          offline: { color: 'error', icon: <ExclamationCircleOutlined />, text: '离线' },
          unknown: { color: 'default', icon: <ExclamationCircleOutlined />, text: '未知' },
          error: { color: 'error', icon: <ExclamationCircleOutlined />, text: '错误' },
        };
        const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.unknown;
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '电源状态',
      dataIndex: 'power_state',
      key: 'power_state',
      render: (powerState: string) => {
        const powerConfig = {
          on: { color: 'success', text: '开机' },
          off: { color: 'default', text: '关机' },
          unknown: { color: 'warning', text: '未知' },
        };
        const config = powerConfig[powerState as keyof typeof powerConfig] || powerConfig.unknown;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
  ];

  const getOverallStats = () => {
    const totalServers = servers.length;
    const groupedServers = servers.filter(server => server.group_id).length;
    const ungroupedServers = totalServers - groupedServers;
    const totalGroups = groups.length;
    
    return {
      totalServers,
      groupedServers,
      ungroupedServers,
      totalGroups,
      groupedRate: totalServers > 0 ? Math.round((groupedServers / totalServers) * 100) : 0,
    };
  };

  const overallStats = getOverallStats();

  return (
    <div>
      <Card>
        <Title level={4}>集群管理</Title>
        
        {/* 总览统计 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Statistic 
              title="总服务器数" 
              value={overallStats.totalServers} 
              prefix={<CloudServerOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="分组数量" 
              value={overallStats.totalGroups} 
              prefix={<CloudServerOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="已分组服务器" 
              value={overallStats.groupedServers} 
              suffix={`/ ${overallStats.totalServers}`}
            />
          </Col>
          <Col span={6}>
            <div>
              <Text type="secondary">分组覆盖率</Text>
              <Progress 
                percent={overallStats.groupedRate} 
                size="small" 
                style={{ marginTop: 8 }}
                status={overallStats.groupedRate === 100 ? 'success' : 'active'}
              />
            </div>
          </Col>
        </Row>

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="分组管理" key="groups">
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateGroup}
              >
                创建分组
              </Button>
            </div>
            
            <Table
              columns={groupColumns}
              dataSource={groups}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 个分组`,
              }}
            />
          </TabPane>
          
          <TabPane tab="服务器分布" key="servers">
            <Table
              columns={serverColumns}
              dataSource={servers}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 台服务器`,
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 创建/编辑分组模态框 */}
      <Modal
        title={editingGroup ? '编辑分组' : '创建分组'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
      >
        <Form
          form={form}
          onFinish={handleSubmit}
          layout="vertical"
        >
          <Form.Item
            name="name"
            label="分组名称"
            rules={[{ required: true, message: '请输入分组名称' }]}
          >
            <Input placeholder="请输入分组名称" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea 
              rows={3}
              placeholder="请输入分组描述（可选）" 
            />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingGroup ? '更新' : '创建'}
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

export default ClusterManagement;