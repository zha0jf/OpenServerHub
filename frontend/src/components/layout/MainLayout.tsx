import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Space,
  Button,
  Typography,
  theme,
} from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  CloudServerOutlined,
  UserOutlined,
  MonitorOutlined,
  ClusterOutlined,
  LogoutOutlined,
  SearchOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import Logo from '../logo/Logo';
import AboutModal from '../about/About';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [aboutModalVisible, setAboutModalVisible] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表板',
    },
    {
      key: '/servers',
      icon: <CloudServerOutlined />,
      label: '服务器管理',
    },
    {
      key: '/clusters',
      icon: <ClusterOutlined />,
      label: '集群管理',
    },
    {
      key: '/discovery',
      icon: <SearchOutlined />,
      label: '设备发现',
    },
    {
      key: '/monitoring',
      icon: <MonitorOutlined />,
      label: '监控面板',
    },
    {
      key: '/users',
      icon: <UserOutlined />,
      label: '用户管理',
    },
    {
      key: '/audit',
      icon: <FileTextOutlined />,
      label: '审计日志',
    },
  ];

  const handleMenuClick = (key: string) => {
    navigate(key);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleProfile = () => {
    // 导航到个人信息页面
    navigate('/profile');
  };

  const [helpDropdownVisible, setHelpDropdownVisible] = useState(false);

  const helpMenuItems = [
    {
      key: 'product-info',
      label: '产品信息',
      onClick: () => setAboutModalVisible(true),
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
      onClick: handleProfile,
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh', overflow: 'hidden' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        style={{
          position: 'fixed',
          height: '100vh',
          left: 0,
          top: 0,
          bottom: 0,
          overflow: 'auto',
        }}
      >
        <Logo collapsed={collapsed} />
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
        />
      </Sider>
      <Layout 
        style={{
          marginLeft: collapsed ? 80 : 200,
          transition: 'margin-left 0.2s',
          height: '100vh',
          overflow: 'hidden',
        }}
      >
        <Header style={{ padding: 0, background: colorBgContainer }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            height: '100%',
            paddingRight: '24px'
          }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: '16px',
                width: 64,
                height: 64,
              }}
            />
            <Space>
              <Dropdown 
                menu={{ items: helpMenuItems }} 
                placement="bottomRight"
                trigger={['click']}
                onOpenChange={setHelpDropdownVisible}
                open={helpDropdownVisible}
              >
                <Button type="text">
                  帮助
                </Button>
              </Dropdown>
              <span>欢迎, {user?.username}</span>
              <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                <Avatar 
                  style={{ backgroundColor: '#87d068', cursor: 'pointer' }} 
                  icon={<UserOutlined />} 
                />
              </Dropdown>
            </Space>
          </div>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            background: colorBgContainer,
            overflowY: 'auto',
            height: 'calc(100vh - 64px - 48px)', // 减去header高度和margin
          }}
        >
          <Outlet />
        </Content>
      </Layout>
      <AboutModal visible={aboutModalVisible} onClose={() => setAboutModalVisible(false)} />
    </Layout>
  );
};

export default MainLayout;