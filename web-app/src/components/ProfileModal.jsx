import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import './ProfileModal.css';

const ProfileModal = ({ 
  user, 
  isOpen, 
  onClose, 
  onUserUpdate,
  onLogout 
}) => {
  const [formData, setFormData] = useState({
    displayName: '',
    email: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState('');

  // Initialize form data when modal opens or user changes
  useEffect(() => {
    if (isOpen && user) {
      setFormData({
        displayName: user.displayName || '',
        email: user.email || ''
      });
      setErrors({});
      setSuccessMessage('');
    }
  }, [isOpen, user]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
    
    // Clear success message when editing
    if (successMessage) {
      setSuccessMessage('');
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.displayName.trim()) {
      newErrors.displayName = 'Display name is required';
    } else if (formData.displayName.trim().length < 2) {
      newErrors.displayName = 'Display name must be at least 2 characters';
    } else if (formData.displayName.trim().length > 100) {
      newErrors.displayName = 'Display name must be less than 100 characters';
    }
    
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    // Check if anything actually changed
    const trimmedDisplayName = formData.displayName.trim();
    const trimmedEmail = formData.email.trim().toLowerCase();
    
    if (trimmedDisplayName === user.displayName && trimmedEmail === user.email) {
      setSuccessMessage('No changes were made');
      return;
    }
    
    setIsLoading(true);
    setErrors({});
    setSuccessMessage('');
    
    try {
      const updateData = {};
      
      if (trimmedDisplayName !== user.displayName) {
        updateData.displayName = trimmedDisplayName;
      }
      
      if (trimmedEmail !== user.email) {
        updateData.email = trimmedEmail;
      }
      
      const response = await apiService.updateProfile(updateData);
      
      // Update user data in parent component
      if (onUserUpdate) {
        onUserUpdate(response.user);
      }
      
      setSuccessMessage(response.message || 'Profile updated successfully!');
      
    } catch (error) {
      console.error('Profile update error:', error);
      
      if (error.type === 'VALIDATION_ERROR' && error.details) {
        setErrors(error.details);
      } else {
        setErrors({ 
          general: error.message || 'Failed to update profile. Please try again.' 
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setErrors({});
    setSuccessMessage('');
    onClose();
  };

  const handleLogout = () => {
    onLogout();
    handleClose();
  };

  if (!isOpen) return null;

  return (
    <div className="profile-modal-overlay" onClick={handleClose}>
      <div className="profile-modal" onClick={(e) => e.stopPropagation()}>
        <div className="profile-modal-header">
          <h2>Profile Settings</h2>
          <button 
            className="profile-modal-close"
            onClick={handleClose}
            aria-label="Close"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="profile-modal-content">
          {/* User Avatar Section */}
          <div className="profile-avatar-section">
            <div className="profile-avatar-large">
              {user?.displayName?.charAt(0).toUpperCase() || 'U'}
            </div>
            <p className="profile-joined">
              Member since {new Date(user?.createdAt).toLocaleDateString()}
            </p>
          </div>

          {/* Profile Form */}
          <form onSubmit={handleSubmit} className="profile-form">
            {errors.general && (
              <div className="profile-error-banner">
                {errors.general}
              </div>
            )}

            {successMessage && (
              <div className="profile-success-banner">
                {successMessage}
              </div>
            )}

            <div className="profile-form-group">
              <label htmlFor="displayName" className="profile-form-label">
                Display Name
              </label>
              <input
                id="displayName"
                name="displayName"
                type="text"
                value={formData.displayName}
                onChange={handleInputChange}
                className={`profile-form-input ${errors.displayName ? 'error' : ''}`}
                placeholder="Enter your display name"
                disabled={isLoading}
              />
              {errors.displayName && (
                <span className="profile-form-error">{errors.displayName}</span>
              )}
            </div>

            <div className="profile-form-group">
              <label htmlFor="email" className="profile-form-label">
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleInputChange}
                className={`profile-form-input ${errors.email ? 'error' : ''}`}
                placeholder="Enter your email address"
                disabled={isLoading}
              />
              {errors.email && (
                <span className="profile-form-error">{errors.email}</span>
              )}
            </div>

            <div className="profile-form-actions">
              <button
                type="submit"
                className="profile-btn-primary"
                disabled={isLoading}
              >
                {isLoading ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                type="button"
                className="profile-btn-secondary"
                onClick={handleClose}
                disabled={isLoading}
              >
                Cancel
              </button>
            </div>
          </form>

          {/* Logout Section */}
          <div className="profile-logout-section">
            <hr className="profile-divider" />
            <button
              className="profile-btn-logout"
              onClick={handleLogout}
              disabled={isLoading}
            >
              <LogoutIcon />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Icon components
const CloseIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

const LogoutIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
    <polyline points="16 17 21 12 16 7"></polyline>
    <line x1="21" y1="12" x2="9" y2="12"></line>
  </svg>
);

export default ProfileModal;
