import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  Card,
  Typography,
  Descriptions,
  Button,
  Space,
  Tag,
  Divider,
  Row,
  Col,
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

const Profile: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return (
      <Card>
        <Text>未找到用户信息</Text>
      </Card>
    );
  }

  const roleMap: Record<string, { text: string; color: string }> = {
    admin: { text: '管理员', color: 'red' },
    operator: { text: '操作员', color: 'blue' },
    user: { text: '普通用户', color: 'green' },
    readonly: { text: '只读用户', color: 'orange' },
  };

  const roleInfo = roleMap[user.role] || { text: user.role, color: 'default' };

  return (
    <div>
      <Card>
        <Title level={2}>
          <Space>
            <UserOutlined />
            个人信息
          </Space>
        </Title>
        
        <Divider />
        
        <Descriptions column={1} bordered>
          <Descriptions.Item label="用户名">
            <Text strong>{user.username}</Text>
          </Descriptions.Item>
          
          <Descriptions.Item label="邮箱">
            <Space>
              <MailOutlined />
              <Text>{user.email || '未设置'}</Text>
            </Space>
          </Descriptions.Item>
          
          <Descriptions.Item label="角色">
            <Tag color={roleInfo.color}>{roleInfo.text}</Tag>
          </Descriptions.Item>
          
          <Descriptions.Item label="账户状态">
            <Tag color={user.is_active ? 'green' : 'red'}>
              {user.is_active ? '正常' : '禁用'}
            </Tag>
          </Descriptions.Item>
          
          <Descriptions.Item label="创建时间">
            <Space>
              <CalendarOutlined />
              <Text>
                {new Date(user.created_at + 'Z').toLocaleString('zh-CN')}
              </Text>
            </Space>
          </Descriptions.Item>
          
          {user.last_login_at && (
            <Descriptions.Item label="最后登录">
              <Space>
                <ClockCircleOutlined />
                <Text>
                  {new Date(user.last_login_at + 'Z').toLocaleString('zh-CN')}
                </Text>
              </Space>
            </Descriptions.Item>
          )}
        </Descriptions>
        
        <Divider />
        
        <Row justify="end">
          <Col>
            <Space>
              <Button onClick={() => navigate(-1)}>
                返回
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default Profile;