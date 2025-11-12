import React from 'react';
import { Descriptions, Tag, Divider, Empty, Alert } from 'antd';
import dayjs from 'dayjs';
import { AuditLog } from '../../types';
import './AuditLogDetail.css';

interface AuditLogDetailProps {
  log: AuditLog;
}

const AuditLogDetail: React.FC<AuditLogDetailProps> = ({ log }) => {
  const statusColor = {
    success: 'green',
    failed: 'red',
    partial: 'orange',
  };

  const statusText = {
    success: '成功',
    failed: '失败',
    partial: '部分成功',
  };

  let actionDetails = null;
  let result = null;

  try {
    if (log.action_details) {
      actionDetails = JSON.parse(log.action_details);
    }
  } catch (e) {
    // 忽略JSON解析错误
  }

  try {
    if (log.result) {
      result = JSON.parse(log.result);
    }
  } catch (e) {
    // 忽略JSON解析错误
  }

  return (
    <div className="audit-log-detail">
      {log.status === 'failed' && log.error_message && (
        <Alert
          message="操作失败"
          description={log.error_message}
          type="error"
          style={{ marginBottom: '16px' }}
          showIcon
        />
      )}

      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="日志ID">{log.id}</Descriptions.Item>
        <Descriptions.Item label="操作类型">
          <Tag color="blue">{log.action}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="操作状态">
          <Tag color={statusColor[log.status]}>
            {statusText[log.status]}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="操作者">
          {log.operator_username || '-'}
          {log.operator_id && ` (ID: ${log.operator_id})`}
        </Descriptions.Item>
        <Descriptions.Item label="资源类型">
          {log.resource_type || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="资源ID">
          {log.resource_id || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="资源名称">
          {log.resource_name || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="操作时间">
          {new Date(log.created_at + 'Z').toLocaleString('zh-CN')}
        </Descriptions.Item>
        <Descriptions.Item label="客户端IP">
          {log.ip_address || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="User Agent">
          <div className="user-agent-text">
            {log.user_agent || '-'}
          </div>
        </Descriptions.Item>
      </Descriptions>

      {actionDetails && (
        <>
          <Divider>操作详情</Divider>
          <pre className="json-display">
            {JSON.stringify(actionDetails, null, 2)}
          </pre>
        </>
      )}

      {result && (
        <>
          <Divider>操作结果</Divider>
          <pre className="json-display">
            {JSON.stringify(result, null, 2)}
          </pre>
        </>
      )}

      {!actionDetails && !result && (
        <>
          <Divider>详情</Divider>
          <Empty description="无额外详情信息" />
        </>
      )}
    </div>
  );
};

export default AuditLogDetail;
