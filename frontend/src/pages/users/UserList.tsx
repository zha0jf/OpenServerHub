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
  Switch,
  message,
  Popconfirm,
  Card,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { userService } from '../../services/auth';
import { User, CreateUserRequest } from '../../types';
import { ColumnsType } from 'antd/es/table';
import { useAuth } from '../../contexts/AuthContext';

const { Title } = Typography;
const { Option } = Select;

// 验证规则常量，与后端保持一致
const VALIDATION_RULES = {
  username: {
    pattern: /^[a-zA-Z0-9_-]+$/,
    minLength: 3,
    maxLength: 50,
  },
  email: {
    pattern: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
  },
  password: {
    minLength: 6,
    maxLength: 128,
  },
};

const UserList: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();
  const { user: currentUser } = useAuth();

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await userService.getUsers();
      setUsers(data);
    } catch (error) {
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = () => {
    setEditingUser(null);
    form.resetFields();
    // 设置默认值
    form.setFieldsValue({
      role: 'user',
      is_active: true
    });
    setModalVisible(true);
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue({
      ...user,
      password: '', // 不显示密码
    });
    setModalVisible(true);
  };

  const handleDeleteUser = async (user: User) => {
    if (user.id === currentUser?.id) {
      message.error('不能删除当前登录用户');
      return;
    }

    try {
      await userService.deleteUser(user.id);
      message.success('用户删除成功');
      loadUsers();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingUser) {
        const updateData = { ...values };
        if (!updateData.password) {
          delete updateData.password; // 如果密码为空，不更新密码
        }
        await userService.updateUser(editingUser.id, updateData);
        message.success('用户更新成功');
      } else {
        await userService.createUser(values as CreateUserRequest);
        message.success('用户创建成功');
      }
      setModalVisible(false);
      loadUsers();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const getRoleTag = (role: string) => {
    const roleMap = {
      admin: { color: 'red', text: '管理员' },
      operator: { color: 'blue', text: '操作员' },
      user: { color: 'green', text: '普通用户' },
      readonly: { color: 'orange', text: '只读用户' },
    };
    const config = roleMap[role as keyof typeof roleMap] || { color: 'default', text: role };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns: ColumnsType<User> = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => getRoleTag(role),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '正常' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (time: string) => time ? new Date(time).toLocaleString() : '从未登录',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, user) => (
        <Space size="middle">
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditUser(user)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个用户吗？"
            onConfirm={() => handleDeleteUser(user)}
            okText="确定"
            cancelText="取消"
            disabled={user.id === currentUser?.id}
          >
            <Button 
              size="small" 
              icon={<DeleteOutlined />} 
              danger
              disabled={user.id === currentUser?.id}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 检查当前用户是否为管理员
  const isAdmin = currentUser?.role === 'admin';

  if (!isAdmin) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Title level={3}>权限不足</Title>
          <p>只有管理员可以访问用户管理页面</p>
        </div>
      </Card>
    );
  }

  return (
    <div>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2} style={{ margin: 0 }}>用户管理</Title>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadUsers}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateUser}
            >
              添加用户
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={users}
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
        title={editingUser ? '编辑用户' : '添加用户'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          validateTrigger={['onChange', 'onBlur']}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { 
                min: VALIDATION_RULES.username.minLength, 
                max: VALIDATION_RULES.username.maxLength, 
                message: `用户名长度应为${VALIDATION_RULES.username.minLength}-${VALIDATION_RULES.username.maxLength}个字符` 
              },
              {
                pattern: VALIDATION_RULES.username.pattern,
                message: '用户名只能包含字母、数字、下划线和短横线',
              },
            ]}
            hasFeedback
          >
            <Input 
              placeholder="请输入用户名（3-50个字符，只能包含字母、数字、下划线和短横线）"
              showCount
              maxLength={VALIDATION_RULES.username.maxLength}
            />
          </Form.Item>

          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              {
                pattern: VALIDATION_RULES.email.pattern,
                message: '请输入有效的邮箱地址',
              },
            ]}
            hasFeedback
          >
            <Input 
              placeholder="请输入邮箱地址"
              type="email"
            />
          </Form.Item>

          <Form.Item
            name="password"
            label={editingUser ? '密码（留空表示不修改）' : '密码'}
            rules={[
              ...(editingUser ? [] : [{ required: true, message: '请输入密码' }]),
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || value.length === 0) {
                    // 如果是编辑模式且密码为空，允许通过验证
                    if (editingUser) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('请输入密码'));
                  }
                  if (value.length < VALIDATION_RULES.password.minLength) {
                    return Promise.reject(new Error(`密码长度至少${VALIDATION_RULES.password.minLength}个字符`));
                  }
                  if (value.length > VALIDATION_RULES.password.maxLength) {
                    return Promise.reject(new Error(`密码长度不能超过${VALIDATION_RULES.password.maxLength}个字符`));
                  }
                  return Promise.resolve();
                },
              }),
            ]}
            hasFeedback
          >
            <Input.Password 
              placeholder={editingUser ? '留空表示不修改密码' : `请输入密码（至少${VALIDATION_RULES.password.minLength}个字符）`}
              showCount
              maxLength={VALIDATION_RULES.password.maxLength}
            />
          </Form.Item>

          <Form.Item
            name="role"
            label="角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select placeholder="请选择角色">
              <Option value="admin">管理员</Option>
              <Option value="operator">操作员</Option>
              <Option value="user">普通用户</Option>
              <Option value="readonly">只读用户</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="is_active"
            label="状态"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="正常" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingUser ? '更新' : '创建'}
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

export default UserList;