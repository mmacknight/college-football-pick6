import React, { useState, useEffect } from 'react';
import ProfileModal from './ProfileModal';
import './ProfessionalHeader.css';

const ProfessionalHeader = ({ 
  user,
  currentPage = 'dashboard', // 'dashboard', 'league', 'draft', 'settings'
  leagueName = null,
  onNavigate,
  onLogout,
  onUserUpdate,
  actions = []
}) => {
  const [isDesktop, setIsDesktop] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);

  useEffect(() => {
    const checkIsDesktop = () => {
      setIsDesktop(window.innerWidth >= 1024);
    };
    
    checkIsDesktop();
    window.addEventListener('resize', checkIsDesktop);
    return () => window.removeEventListener('resize', checkIsDesktop);
  }, []);

  const handleNavigation = (page) => {
    if (page === 'profile') {
      setShowProfileModal(true);
      setShowUserMenu(false);
    } else if (onNavigate) {
      onNavigate(page);
    }
  };

  const getNavigationItems = () => {
    const items = [
      { id: 'dashboard', label: 'My Leagues', icon: '🏠' },
    ];

    if (leagueName) {
      items.push(
        { id: 'league', label: leagueName, icon: '🏈' },
      );
      
      if (currentPage === 'draft') {
        items.push({ id: 'draft', label: 'Draft', icon: '📋' });
      }
      
      if (currentPage === 'settings') {
        items.push({ id: 'settings', label: 'Settings', icon: '⚙️' });
      }
    }

    return items;
  };

  const renderDesktopHeader = () => (
    <>
      <header className="professional-header desktop">
        <div className="header-container">
          {/* Logo and brand */}
          <div className="brand-section">
            <img 
              src="/assets/logo.png" 
              alt="Pick6 Logo" 
              className="logo"
              onClick={() => handleNavigation('dashboard')}
            />
            <div className="brand-text">
              <h1 className="brand-name">Pick6</h1>
              <span className="brand-tagline">College Football Fantasy</span>
            </div>
          </div>

          {/* Right section with actions and user */}
          <div className="header-actions">
            {/* Custom actions */}
            {actions.map((action, index) => (
              <button
                key={index}
                className={`action-btn ${action.variant || 'default'}`}
                onClick={action.onClick}
                disabled={action.disabled}
                title={action.label}
              >
                {action.icon && <span className="action-icon">{action.icon}</span>}
                {action.text && <span className="action-text">{action.text}</span>}
              </button>
            ))}

            {/* User menu */}
            <div className="user-menu-container">
              <button 
                className="user-menu-trigger"
                onClick={() => setShowUserMenu(!showUserMenu)}
              >
                <div className="user-avatar">
                  {user?.displayName?.charAt(0).toUpperCase() || 'U'}
                </div>
                <span className="user-name">{user?.displayName}</span>
                <ChevronDownIcon className={`chevron ${showUserMenu ? 'open' : ''}`} />
              </button>

              {showUserMenu && (
                <div className="user-menu-dropdown">
                  <div className="user-info">
                    <div className="user-detail">
                      <strong>{user?.displayName}</strong>
                      <span className="user-email">{user?.email}</span>
                    </div>
                  </div>
                  <hr className="menu-divider" />
                  <button className="menu-item" onClick={() => handleNavigation('profile')}>
                    <UserIcon />
                    Profile
                  </button>
                  <hr className="menu-divider" />
                  <button className="menu-item logout" onClick={onLogout}>
                    <LogoutIcon />
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
      
      {/* Breadcrumb navigation below header */}
      {getNavigationItems().length > 1 && (
        <div className="breadcrumb-bar">
          <div className="breadcrumb-container">
            <nav className="breadcrumb-nav" aria-label="Breadcrumb">
              {getNavigationItems().map((item, index) => (
                <span key={item.id} className="breadcrumb-item">
                  {index > 0 && <ChevronRightIcon className="breadcrumb-separator" />}
                  <button 
                    className={`breadcrumb-link ${currentPage === item.id ? 'active' : ''}`}
                    onClick={() => handleNavigation(item.id)}
                  >
                    <span className="breadcrumb-icon">{item.icon}</span>
                    <span className="breadcrumb-text">{item.label}</span>
                  </button>
                </span>
              ))}
            </nav>
          </div>
        </div>
      )}
    </>
  );

  const renderMobileHeader = () => (
    <header className="professional-header mobile">
      <div className="header-container">
        <div className="mobile-brand">
          <img 
            src="/assets/logo.png" 
            alt="Pick6 Logo" 
            className="logo"
          />
          <h1 className="brand-name">Pick6</h1>
        </div>

        <div className="mobile-actions">
          {actions.map((action, index) => (
            <button
              key={index}
              className={`mobile-action-btn ${action.variant || 'default'}`}
              onClick={action.onClick}
              disabled={action.disabled}
              title={action.label}
            >
              {action.icon}
            </button>
          ))}
          
          <button 
            className="mobile-user-btn"
            onClick={() => setShowProfileModal(true)}
          >
            <div className="user-avatar">
              {user?.displayName?.charAt(0).toUpperCase() || 'U'}
            </div>
          </button>
        </div>
      </div>

      {/* Mobile navigation breadcrumb */}
      {getNavigationItems().length > 1 && (
        <div className="mobile-breadcrumb">
          {getNavigationItems().map((item, index) => (
            <span key={item.id} className="breadcrumb-item">
              {index > 0 && <ChevronRightIcon className="breadcrumb-separator" />}
              <button 
                className={`breadcrumb-link ${currentPage === item.id ? 'active' : ''}`}
                onClick={() => handleNavigation(item.id)}
              >
                {item.label}
              </button>
            </span>
          ))}
        </div>
      )}
    </header>
  );

  // Click outside to close user menu
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showUserMenu && !event.target.closest('.user-menu-container')) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [showUserMenu]);

  return (
    <>
      {isDesktop ? renderDesktopHeader() : renderMobileHeader()}
      
      <ProfileModal
        user={user}
        isOpen={showProfileModal}
        onClose={() => setShowProfileModal(false)}
        onUserUpdate={onUserUpdate}
        onLogout={onLogout}
      />
    </>
  );
};

// Icon components
const ChevronDownIcon = ({ className = "" }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

const ChevronRightIcon = ({ className = "" }) => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
    <polyline points="9 18 15 12 9 6"></polyline>
  </svg>
);

const UserIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
    <circle cx="12" cy="7" r="4"></circle>
  </svg>
);



const LogoutIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
    <polyline points="16 17 21 12 16 7"></polyline>
    <line x1="21" y1="12" x2="9" y2="12"></line>
  </svg>
);

export default ProfessionalHeader;
