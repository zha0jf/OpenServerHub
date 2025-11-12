import React from 'react';
import { Card, Row, Col, Statistic, List, Tag } from 'antd';
import { AuditLogStats as AuditLogStatsType } from '../../types';

interface AuditLogStatsProps {
  stats: AuditLogStatsType;
}

const AuditLogStats: React.FC<AuditLogStatsProps> = ({ stats }) => {
  return (
    <Card title="操作类型分布" size="small">
      <Row gutter={16} style={{ marginBottom: '16px' }}>
        <Col span={12}>
          <div style={{ marginBottom: '8px' }}>
            <strong>各操作类型数量</strong>
          </div>
          <List
            size="small"
            dataSource={stats.actions_breakdown.slice(0, 5)}
            renderItem={(item) => (
              <List.Item>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                  <span>
                    <Tag>{item.action}</Tag>
                  </span>
                  <span>{item.count}</span>
                </div>
              </List.Item>
            )}
          />
        </Col>
        <Col span={12}>
          <div style={{ marginBottom: '8px' }}>
            <strong>活跃用户排行</strong>
          </div>
          <List
            size="small"
            dataSource={stats.top_operators.slice(0, 5)}
            renderItem={(item) => (
              <List.Item>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                  <span>{item.username}</span>
                  <span>{item.count} 次</span>
                </div>
              </List.Item>
            )}
          />
        </Col>
      </Row>
    </Card>
  );
};

export default AuditLogStats;
