import React, { useState } from 'react';
import { Modal, Divider, Space, Typography, Row, Col, Tag } from 'antd';
import { InfoOutlined } from '@ant-design/icons';
import { VERSION_INFO } from '../../config/version';

const { Title, Text, Paragraph } = Typography;

interface AboutModalProps {
  visible: boolean;
  onClose: () => void;
}

const AboutModal: React.FC<AboutModalProps> = ({ visible, onClose }) => {
  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <InfoOutlined />
          <span>关于 OpenServerHub</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={700}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 项目名称和版本 */}
        <div>
          <Title level={3} style={{ margin: 0 }}>
            OpenServerHub
          </Title>
          <div style={{ marginTop: '8px' }}>
            <Text type="secondary">版本: </Text>
            <Text code>{VERSION_INFO.version}</Text>
            {VERSION_INFO.buildTime && (
              <div style={{ marginTop: '4px' }}>
                <Text type="secondary">构建时间: </Text>
                <Text type="secondary">{VERSION_INFO.buildTime}</Text>
              </div>
            )}
          </div>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 项目描述 */}
        <div>
          <Text strong>项目描述</Text>
          <Paragraph style={{ marginTop: '8px', marginBottom: 0 }}>
            OpenServerHub 是一个现代化的服务器管理平台，基于 FastAPI + React 技术栈开发，提供服务器
            IPMI 控制、监控告警和集群管理功能。
          </Paragraph>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 核心功能 */}
        <div>
          <Text strong>核心功能</Text>
          <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '24px' }}>
            <li>IPMI 电源控制（开机/关机/重启）</li>
            <li>服务器状态实时监控</li>
            <li>用户权限管理（Admin/Operator/User/ReadOnly）</li>
            <li>服务器分组和集群管理</li>
            <li>批量操作和设备发现</li>
            <li>Prometheus + Grafana 监控系统集成</li>
            <li>告警机制和邮件通知</li>
          </ul>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 技术栈 */}
        <div>
          <Text strong>技术栈</Text>
          <Row gutter={[8, 8]} style={{ marginTop: '8px' }}>
            <Col span={12}>
              <Text type="secondary">后端：</Text>
              <div style={{ marginTop: '4px' }}>
                <Tag color="blue">FastAPI</Tag>
                <Tag color="blue">Python 3.9+</Tag>
                <Tag color="blue">SQLite</Tag>
                <Tag color="blue">JWT</Tag>
              </div>
            </Col>
            <Col span={12}>
              <Text type="secondary">前端：</Text>
              <div style={{ marginTop: '4px' }}>
                <Tag color="cyan">React 18</Tag>
                <Tag color="cyan">TypeScript</Tag>
                <Tag color="cyan">Ant Design</Tag>
              </div>
            </Col>
            <Col span={12}>
              <Text type="secondary">监控：</Text>
              <div style={{ marginTop: '4px' }}>
                <Tag color="magenta">Prometheus</Tag>
                <Tag color="magenta">Grafana</Tag>
                <Tag color="magenta">AlertManager</Tag>
              </div>
            </Col>
          </Row>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 访问地址 */}
        <div>
          <Text strong>访问地址</Text>
          <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '24px' }}>
            <li>前端：http://localhost:3000</li>
            <li>后端 API：http://localhost:8000</li>
            <li>API 文档：http://localhost:8000/docs</li>
            <li>Prometheus：http://localhost:9090</li>
            <li>Grafana：http://localhost:3001</li>
          </ul>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 默认账号 */}
        <div>
          <Text strong>默认账号</Text>
          <div style={{ marginTop: '8px', padding: '8px 12px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
            <div>用户名: <Text code>admin</Text></div>
            <div>密码: <Text code>admin123</Text></div>
          </div>
          <Paragraph type="warning" style={{ marginTop: '8px', marginBottom: 0 }}>
            ⚠️ 生产环境请及时修改默认密码
          </Paragraph>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 许可证和链接 */}
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            许可证: MIT License
          </Text>
          <br />
          <Text type="secondary">
            版权所有 © 2025 SkySolidiss
          </Text>
          <br />
          <Text type="secondary">
            保留所有权利
          </Text>
        </div>
      </Space>
    </Modal>
  );
};

export default AboutModal;
