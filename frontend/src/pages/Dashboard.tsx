import React, { useState, useEffect, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Typography,
  Space,
  Spin,
  Alert,
  Progress,
  Divider,
} from 'antd';
import {
  CloudServerOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  PoweroffOutlined,
  BuildOutlined,
} from '@ant-design/icons';
import { serverService } from '../services/server';
import { useAuth } from '../contexts/AuthContext';
import { ClusterStats } from '../types';
import { useLocation } from 'react-router-dom';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const location = useLocation(); // 获取当前路由位置
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<ClusterStats | null>(null);
  const [error, setError] = useState<string>('');

  const loadDashboardData = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      
      // 使用新的集群统计API
      const clusterStats = await serverService.getClusterStats();
      setStats(clusterStats);
      
    } catch (err: any) {
      console.error('加载仪表板数据失败:', err);
      setError('加载仪表板数据失败');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      loadDashboardData();
    }
  }, [isAuthenticated, loadDashboardData]);

  // 添加路由监听，每次切换到Dashboard页面时刷新数据
  useEffect(() => {
    if (isAuthenticated && location.pathname === '/dashboard') {
      loadDashboardData();
    }
  }, [location.pathname, isAuthenticated, loadDashboardData]);

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
      
      {/* 基础统计 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="服务器总数"
              value={stats?.total_servers || 0}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="在线服务器"
              value={stats?.online_servers || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="离线服务器"
              value={stats?.offline_servers || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="状态未知"
              value={stats?.unknown_servers || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 电源状态统计 */}
      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="开机服务器"
              value={stats?.power_on_servers || 0}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="关机服务器"
              value={stats?.power_off_servers || 0}
              prefix={<PoweroffOutlined />}
              valueStyle={{ color: '#8c8c8c' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 在线率进度条 */}
      {stats && stats.total_servers > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
          <Col span={24}>
            <Card title="服务器在线率">
              <Progress
                percent={Math.round((stats.online_servers / stats.total_servers) * 100)}
                status={stats.online_servers === stats.total_servers ? 'success' : 'active'}
                format={(percent) => `${percent}% (${stats.online_servers}/${stats.total_servers})`}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 分组统计 */}
      {stats && Object.keys(stats.group_stats).length > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
          <Col span={24}>
            <Card title="分组统计">
              <Row gutter={[16, 16]}>
                {Object.entries(stats.group_stats).map(([groupName, groupStats]) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={groupName}>
                    <Card size="small" title={groupName}>
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        <div>总数: {groupStats.total}</div>
                        <div style={{ color: '#52c41a' }}>在线: {groupStats.online}</div>
                        <div style={{ color: '#f5222d' }}>离线: {groupStats.offline}</div>
                        <div style={{ color: '#faad14' }}>未知: {groupStats.unknown}</div>
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>
        </Row>
      )}

      {/* 厂商统计 */}
      {stats && Object.keys(stats.manufacturer_stats).length > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
          <Col span={24}>
            <Card title="厂商分布">
              <Row gutter={[16, 16]}>
                {Object.entries(stats.manufacturer_stats)
                  .sort((a, b) => b[1] - a[1]) // 按数量降序排列
                  .map(([manufacturer, count]) => (
                  <Col xs={12} sm={8} md={6} lg={4} key={manufacturer}>
                    <Card size="small">
                      <Statistic
                        title={manufacturer}
                        value={count}
                        prefix={<BuildOutlined />}
                        valueStyle={{ fontSize: '18px' }}
                      />
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>
        </Row>
      )}

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