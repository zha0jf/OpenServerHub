import React, { useState, useEffect } from 'react';
import { Card, Skeleton, Button, Alert } from 'antd';
import { configService } from '../../services/config';

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
  const [error, setError] = useState<string | null>(null);
  
  // 从后端API获取Grafana URL，如果没有则使用默认值
  const [grafanaUrl, setGrafanaUrl] = useState<string>('');
  
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        console.debug('[GrafanaPanel] 开始获取配置');
        const config = await configService.getFrontendConfig();
        console.debug('[GrafanaPanel] 获取到的配置:', config);
        if (config && config.grafana_url) {
          setGrafanaUrl(config.grafana_url);
          console.debug('[GrafanaPanel] 设置grafanaUrl为:', config.grafana_url);
        } else {
          console.warn('[GrafanaPanel] 配置中没有grafana_url或配置为空，使用默认值');
          setGrafanaUrl('http://localhost:3001');
        }
      } catch (error) {
        console.error('[GrafanaPanel] 获取配置失败，使用默认值:', error);
        setGrafanaUrl('http://localhost:3001');
      }
    };
    
    fetchConfig();
  }, []);

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

  // 处理加载状态
  if (loading) {
    return (
      <Card title={title} style={{ height: '100%' }}>
        <Skeleton active />
      </Card>
    );
  }

  // 处理错误状态 - 提供降级方案
  const handleIframeError = () => {
    setError('无法嵌入Grafana面板，点击下方按钮在新窗口中打开');
  };

  return (
    <Card title={title} style={{ height: '100%' }}>
      {error && (
        <Alert 
          message={error}
          type="warning"
          action={
            <Button size="small" type="primary" onClick={() => window.open(embedUrl, '_blank')}>
              在新窗口打开
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}
      <iframe
        src={embedUrl}
        width="100%"
        height="100%"
        frameBorder="0"
        style={{ minHeight: `${height}px` }}
        title={`${title} - Grafana Panel`}
        onError={handleIframeError}
        onLoad={() => {
          setLoading(false);
          // 检查是否可以访问iframe内容
          try {
            const iframe = document.querySelector<HTMLIFrameElement>(`iframe[title="${title} - Grafana Panel"]`);
            if (iframe) {
              // 尝试访问iframe内容，如果被X-Frame-Options阻止会抛出异常
              iframe.contentDocument;
            }
          } catch (e) {
            // 跨域访问iframe会抛出异常，这可能是由于X-Frame-Options限制
            console.debug('无法访问iframe内容，可能是由于X-Frame-Options限制');
            handleIframeError();
          }
        }}
      />
    </Card>
  );
};

export default GrafanaPanel;