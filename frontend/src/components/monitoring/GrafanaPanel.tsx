import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Card, Skeleton, Button, Alert } from 'antd';
import { configService } from '../../services/config';

const useDeepCompareMemoize = (value: Record<string, any>) => {
  const ref = useRef<string>();
  const signal = useMemo(() => JSON.stringify(value), [value]);
  const currentRef = useRef<Record<string, any>>(value);
  
  if (ref.current !== signal) {
    ref.current = signal;
    currentRef.current = value;
  }
  return currentRef.current;
};

interface GrafanaPanelProps {
  dashboardUid: string;
  panelId?: string;
  title: string;
  height?: number;
  queryParams?: Record<string, string>;
}

const GrafanaPanel: React.FC<GrafanaPanelProps> = ({
  dashboardUid,
  panelId,
  title,
  height = 400,
  queryParams = {}
}) => {
  const [grafanaUrl, setGrafanaUrl] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // 用于解决超时检测中的闭包问题
  const loadingRef = useRef<boolean>(true);
  const queryParamsMemo = useDeepCompareMemoize(queryParams);

  useEffect(() => {
    configService.getFrontendConfig()
      .then(config => setGrafanaUrl(config?.grafana_url || 'http://localhost:3001'))
      .catch(() => setGrafanaUrl('http://localhost:3001'));
  }, []);

  const embedUrl = useMemo(() => {
    if (!grafanaUrl) return '';
    const params = new URLSearchParams({
      orgId: '1',
      refresh: '30s',
      kiosk: 'true',
      ...queryParamsMemo
    });
    
    const path = panelId ? `d-solo/${dashboardUid}` : `d/${dashboardUid}`;
    if (panelId) params.set('panelId', panelId); // 统一使用 params 处理
    
    return `${grafanaUrl}/${path}?${params.toString()}`;
  }, [grafanaUrl, dashboardUid, panelId, queryParamsMemo]);

  useEffect(() => {
    if (!embedUrl) return;
    
    setLoading(true);
    loadingRef.current = true; // 同步更新 Ref
    setError(null);

    const timer = setTimeout(() => {
      // 检查 Ref 而不是 state 变量，解决闭包陷阱问题
      if (loadingRef.current) {
        setError('加载超时，请检查 Grafana 配置或网络连接（也可能是 Grafana 拒绝了嵌入）');
      }
    }, 15000); // 适当延长到 15秒

    return () => clearTimeout(timer);
  }, [embedUrl]);

  const handleIframeLoad = () => {
    setLoading(false);
    loadingRef.current = false; // 同步更新 Ref
    setError(null);
  };

  if (!grafanaUrl) {
    return (
      <Card title={title} styles={{ body: { height, padding: 24 } }}>
        <Skeleton active />
      </Card>
    );
  }

  return (
    <Card 
      title={title} 
      styles={{ body: { padding: 0, height, position: 'relative', overflow: 'hidden' } }}
    >
      {/* 骨架屏遮罩 */}
      {loading && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 2, background: '#fff', padding: 24 }}>
          <Skeleton active vertical />
        </div>
      )}

      {/* 错误遮罩 */}
      {error && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 3, background: '#fff', padding: 16 }}>
          <Alert 
            message="加载提醒"
            description={error}
            type="warning"
            showIcon
            action={
              <Button size="small" type="primary" onClick={() => window.open(embedUrl, '_blank')}>
                在新窗口打开
              </Button>
            }
          />
        </div>
      )}

      <iframe
        src={embedUrl}
        width="100%"
        height="100%"
        frameBorder="0"
        title={`${title} - Grafana Panel`}
        onLoad={handleIframeLoad}
        style={{ 
          border: 'none',
          visibility: loading ? 'hidden' : 'visible' // 保持占位但不可见，直到加载完成
        }}
      />
    </Card>
  );
};

export default GrafanaPanel;