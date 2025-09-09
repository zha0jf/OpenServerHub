import React from 'react';

interface LogoIconProps {
  size?: number;
  type?: 'full' | 'small';
}

const LogoIcon: React.FC<LogoIconProps> = ({ size = 48, type = 'full' }) => {
  const imgStyle = {
    width: '90%',
    height: '80%',
    objectFit: 'contain' as const,
    maxWidth: '100%',
    maxHeight: '100%'
  };
  
  if (type === 'small') {
    return (
      <img 
        src="/logo-small.svg" 
        alt="Logo" 
        width={size} 
        height={size} 
      />
    );
  }
  
  return (
    <img 
      src="/logo.svg" 
      alt="Logo" 
      style={imgStyle}
    />
  );
};

export default LogoIcon;