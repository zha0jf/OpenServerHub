# 性能优化待办事项

## Dashboard数据刷新优化方案

### 当前实现
当前采用路由切换时刷新机制：
- 每次用户切换到Dashboard页面时自动获取最新统计数据
- 实现简单，维护成本低
- 适用于服务器状态变化不频繁的场景

### 待优化方案（结合事件驱动和路由切换）

#### 方案一：事件驱动 + 路由切换结合方案

**实现思路：**
1. 保留路由切换时的刷新机制作为兜底方案
2. 在关键操作后添加事件触发，提升实时性

**具体实现步骤：**

1. **恢复ServerList中的事件触发代码：**
```typescript
// 在ServerList.tsx的关键操作后添加事件触发
const handleUpdateStatus = async (server: Server) => {
  try {
    setRefreshingStatus(server.id);
    await serverService.updateServerStatus(server.id);
    message.success('状态更新成功');
    loadServers();
    
    // 触发全局事件通知Dashboard更新统计数据
    window.dispatchEvent(new CustomEvent('serverStatusUpdated'));
  } catch (error) {
    message.error('状态更新失败');
  } finally {
    setRefreshingStatus(null);
  }
};
```

2. **在Dashboard中同时保留两种机制：**
```typescript
// Dashboard.tsx中同时监听路由变化和自定义事件
useEffect(() => {
  if (isAuthenticated && location.pathname === '/dashboard') {
    loadDashboardData();
  }
}, [location.pathname, isAuthenticated]);

// 添加事件监听器，监听服务器状态更新事件
useEffect(() => {
  const handleServerStatusUpdate = () => {
    loadDashboardData();
  };

  // 添加事件监听器
  window.addEventListener('serverStatusUpdated', handleServerStatusUpdate);

  // 清理事件监听器
  return () => {
    window.removeEventListener('serverStatusUpdated', handleServerStatusUpdate);
  };
}, []);
```

#### 方案二：防抖优化方案

**实现思路：**
在事件驱动方案的基础上，添加防抖机制，避免频繁请求。

**具体实现：**
```typescript
import { debounce } from 'lodash';

// 防抖函数，500ms内只执行一次
const debouncedLoadDashboardData = debounce(() => {
  loadDashboardData();
}, 500);

// 事件监听器中使用防抖函数
useEffect(() => {
  const handleServerStatusUpdate = () => {
    debouncedLoadDashboardData();
  };

  window.addEventListener('serverStatusUpdated', handleServerStatusUpdate);
  return () => {
    window.removeEventListener('serverStatusUpdated', handleServerStatusUpdate);
    debouncedLoadDashboardData.cancel(); // 清除防抖定时器
  };
}, []);
```

### 性能优化触发条件

当出现以下情况时，可考虑实施上述优化方案：
1. 用户反馈Dashboard数据刷新延迟明显
2. 监控发现Dashboard API请求频率过高
3. 服务器负载因频繁请求而增加
4. 用户需要更高的实时性体验

### 实施建议

1. **优先级排序：**
   - 首先实施防抖优化方案（方案二）
   - 如仍存在问题，再考虑事件驱动与路由切换结合方案

2. **监控指标：**
   - Dashboard API请求频率
   - 用户页面切换频率
   - 服务器响应时间

3. **A/B测试：**
   - 可以考虑为不同用户群体提供不同的刷新策略
   - 收集用户反馈和性能数据进行对比