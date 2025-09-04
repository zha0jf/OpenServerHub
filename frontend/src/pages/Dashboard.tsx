import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Typography,
  Space,
  Spin,
  Alert,
} from 'antd';
import {
  CloudServerOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { serverService } from '../services/server';
import { useAuth } from '../contexts/AuthContext';

const { Title } = Typography;

interface DashboardStats {
  total: number;
  online: number;
  offline: number;
  unknown: number;
}

const Dashboard: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats>({
    total: 0,
    online: 0,
    offline: 0,
    unknown: 0,
  });
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (isAuthenticated) {
      loadDashboardData();
    }
  }, [isAuthenticated]);

  const loadDashboardData = async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      const servers = await serverService.getServers(0, 1000); // 获取所有服务器
      
      const dashboardStats: DashboardStats = {
        total: servers.length,
        online: servers.filter(s => s.status === 'online').length,
        offline: servers.filter(s => s.status === 'offline').length,
        unknown: servers.filter(s => s.status === 'unknown').length,
      };
      
      setStats(dashboardStats);
    } catch (err: any) {
      console.error('加载仪表板数据失败:', err);
      setError('加载仪表板数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="错误"
        description={error}
        type="error"
        showIcon
        action={
          <button onClick={loadDashboardData}>重试</button>
        }
      />
    );
  }

  return (
    <div>
      <Title level={2}>仪表板</Title>
      
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="服务器总数"
              value={stats.total}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="在线服务器"
              value={stats.online}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="离线服务器"
              value={stats.offline}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="状态未知"
              value={stats.unknown}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col span={24}>
          <Card title="系统概览">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <strong>OpenServerHub 服务器管理平台</strong>
              </div>
              <div>
                版本: 1.0.0
              </div>
              <div>
                功能: 服务器管理、IPMI控制、监控告警
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;