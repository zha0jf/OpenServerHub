import React, { useState, useEffect } from 'react';
import { Card, Skeleton } from 'antd';

interface GrafanaPanelProps {
  dashboardUid: string;
  panelId?: string;
  title: string;
  height?: number;
  queryParams?: Record<string, string>; // 新增：支持传递额外的查询参数
}

const GrafanaPanel: React.FC<GrafanaPanelProps> = ({
  dashboardUid,
  panelId,
  title,
  height = 400,
  queryParams = {} // 默认为空对象
}) => {
  const [embedUrl, setEmbedUrl] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  
  // 从环境变量获取Grafana URL，如果没有则使用默认值
  const grafanaUrl = process.env.REACT_APP_GRAFANA_URL || 'http://localhost:3001';

  useEffect(() => {
    // 构建基础参数
    const baseParams = new URLSearchParams({
      orgId: '1',
      refresh: '30s',
      kiosk: 'true'  // 使用kiosk=true而不是kiosk=tv
    });
    
    // 添加额外的查询参数
    Object.entries(queryParams).forEach(([key, value]) => {
      baseParams.append(key, value);
    });
    
    // 根据是否有panelId构建不同的URL
    if (panelId) {
      // 使用d-solo路径显示单独的面板
      setEmbedUrl(`${grafanaUrl}/d-solo/${dashboardUid}?panelId=${panelId}&${baseParams}`);
    } else {
      // 如果没有指定特定面板，显示整个仪表板但使用kiosk模式
      setEmbedUrl(`${grafanaUrl}/d/${dashboardUid}?${baseParams}`);
    }
    
    // 简单模拟加载完成
    setTimeout(() => {
      setLoading(false);
    }, 1000);
  }, [dashboardUid, panelId, grafanaUrl, queryParams]);

  if (loading) {
    return (
      <Card title={title} style={{ height: '100%' }}>
        <Skeleton active />
      </Card>
    );
  }

  return (
    <Card title={title} style={{ height: '100%' }}>
      <iframe
        src={embedUrl}
        width="100%"
        height="100%"
        frameBorder="0"
        style={{ minHeight: `${height}px` }}
        title={`${title} - Grafana Panel`}
        onLoad={() => setLoading(false)}
      />
    </Card>
  );
};

export default GrafanaPanel;