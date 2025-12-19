import React, { useState, useEffect } from 'react';
import { Modal, Divider, Space, Typography, Row, Col, Tag, Spin, Alert } from 'antd';
import { InfoOutlined } from '@ant-design/icons';
import { VERSION_INFO } from '../../config/version';
import { configService, FrontendConfig } from '../../services/config';

const { Title, Text, Paragraph } = Typography;

interface AboutModalProps {
  visible: boolean;
  onClose: () => void;
}

const AboutModal: React.FC<AboutModalProps> = ({ visible, onClose }) => {
  const [config, setConfig] = useState<FrontendConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true);
        const frontendConfig = await configService.getFrontendConfig();
        setConfig(frontendConfig);
      } catch (err) {
        setError('获取配置信息失败');
        console.error('获取配置信息失败:', err);
      } finally {
        setLoading(false);
      }
    };

    if (visible) {
      fetchConfig();
    }
  }, [visible]);

  if (!visible) return null;

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <InfoOutlined />
          <span>关于 {config?.project_name || 'OpenServerHub'}</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={700}
    >
      <Spin spinning={loading}>
        {error && <Alert message={error} type="error" showIcon />}
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 项目名称和版本 */}
          <div>
            <Title level={3} style={{ margin: 0 }}>
              {config?.project_name || 'OpenServerHub'}
            </Title>
            <div style={{ marginTop: '8px' }}>
              <Text type="secondary">产品版本: </Text>
              <Text code>{config?.version || '未知'}</Text>
              <br />
              <Text type="secondary">项目版本: </Text>
              <Text code>'OpenServerHub'-{VERSION_INFO.version}</Text>
              {VERSION_INFO.buildTime && (
                <div style={{ marginTop: '4px' }}>
                  <Text type="secondary">构建时间: </Text>
                  <Text type="secondary">{VERSION_INFO.buildTime}</Text>
                </div>
              )}
            </div>
          </div>



        <Divider style={{ margin: '8px 0' }} />

        {/* 访问地址 */}
        <div>
          <Text strong>访问地址</Text>
          <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '24px' }}>
            <li>前端：{window.location.origin}</li>
            <li>后端 API：{config?.api_base_url ? `${window.location.origin}${config.api_base_url}` : '未知'}</li>
            <li>API 文档：{window.location.origin}/docs</li>
            <li>Prometheus：{config?.monitoring_enabled ? `http://${window.location.origin}:9090` : '监控未启用'}</li>
            <li>Grafana：<a href={config?.grafana_url} target="_blank" rel="noopener noreferrer">{config?.grafana_url || '监控未启用'}</a></li>
          </ul>
        </div>



        <Divider style={{ margin: '8px 0' }} />

        {/* 厂商信息 */}
        <div>
          <Text strong>问题反馈</Text>
          <div style={{ marginTop: '8px' }}>
            <Text type="secondary">主体: </Text>
            <Text>{config?.vendor_name || '开源项目'}</Text>
            <br />
            <Text type="secondary">网址: </Text>
            <Text>
              <a href={config?.vendor_url} target="_blank" rel="noopener noreferrer">
                {config?.vendor_url || 'https://github.com/zha0jf/OpenServerHub'}
              </a>
            </Text>
          </div>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 版权和许可证信息 */}
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            许可证: MIT License
          </Text>
          <br />
          <Text type="secondary">
            版权所有 © 2025 {config?.vendor_name || 'SkySolidiss'}
          </Text>
          <br />
          <Text type="secondary">
            保留所有权利
          </Text>
        </div>
      </Space>
      </Spin>
    </Modal>
  );
};

export default AboutModal;
