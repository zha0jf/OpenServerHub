import React from 'react';
import LogoIcon from './LogoIcon';

interface LogoProps {
  collapsed?: boolean;
}

const Logo: React.FC<LogoProps> = ({ collapsed = false }) => {
  const logoStyle = {
    height: '64px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: collapsed ? '80px' : '200px', // 根据Sider的宽度设置
    overflow: 'hidden'
  };
  
  const iconContainerStyle = {
    width: collapsed ? '32px' : '100%',
    height: collapsed ? '32px' : '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  };
  
  return (
    <div className="logo" style={logoStyle}>
      <div style={iconContainerStyle}>
        <LogoIcon size={collapsed ? 32 : 48} type={collapsed ? 'small' : 'full'} />
      </div>
    </div>
  );
};

export default Logo;