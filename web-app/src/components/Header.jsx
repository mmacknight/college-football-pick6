import React, { useState, useEffect } from 'react';
import './Header.css';

const Header = ({ 
  title,
  subtitle,
  onBack,
  onLogout,
  actions = [],
  variant = 'default', // 'default', 'auth', 'leagues', 'dashboard', 'detail', 'settings'
  showBackOnDesktop = true // Whether to show back button on desktop
}) => {
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const checkIsDesktop = () => {
      setIsDesktop(window.innerWidth >= 1024);
    };
    
    checkIsDesktop();
    window.addEventListener('resize', checkIsDesktop);
    return () => window.removeEventListener('resize', checkIsDesktop);
  }, []);

  const shouldShowBackButton = onBack && (!isDesktop || showBackOnDesktop);

  return (
    <header className={`unified-header ${variant}`}>
      <div className="header-content">
        <div className="header-left">
          {shouldShowBackButton && (
            <button 
              className="back-button" 
              onClick={onBack} 
              aria-label="Back"
              title="Go back"
            >
              <BackIcon />
              <span className="action-text">Back</span>
            </button>
          )}
          
          <div className="header-text">
            <h1 className="header-title">{title}</h1>
            {subtitle && <p className="header-subtitle">{subtitle}</p>}
          </div>
        </div>
        
        <div className="header-actions">
          {actions.map((action, index) => (
            <button
              key={index}
              className={`action-button ${action.variant || 'default'}`}
              onClick={action.onClick}
              disabled={action.disabled}
              aria-label={action.label}
              title={action.label}
            >
              {action.icon && <span className="action-icon">{action.icon}</span>}
              {action.text && <span className="action-text">{action.text}</span>}
            </button>
          ))}
          
          {onLogout && (
            <button 
              className="logout-button" 
              onClick={onLogout} 
              aria-label="Logout"
              title="Sign out"
            >
              <LogoutIcon />
              <span className="action-text">Sign Out</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

// Icon components
const BackIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="15 18 9 12 15 6"></polyline>
  </svg>
);

const LogoutIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
    <polyline points="16 17 21 12 16 7"></polyline>
    <line x1="21" y1="12" x2="9" y2="12"></line>
  </svg>
);

const ChevronRightIcon = ({ className = "" }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
    <polyline points="9 18 15 12 9 6"></polyline>
  </svg>
);

const RefreshIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="23 4 23 10 17 10"></polyline>
    <polyline points="1 20 1 14 7 14"></polyline>
    <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"></path>
  </svg>
);

export default Header;
export { RefreshIcon }; // Export for use in action configs
