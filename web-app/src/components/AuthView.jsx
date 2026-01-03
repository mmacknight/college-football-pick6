import React, { useState } from 'react';
import { apiService } from '../services/apiService';
import './AuthView.css';

const AuthView = ({ onLogin, onViewLeague }) => {
  const [mode, setMode] = useState('login'); // 'login', 'signup', or 'viewCode'
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    displayName: '',
    confirmPassword: '',
    joinCode: ''
  });
  const [errors, setErrors] = useState({});

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
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (mode === 'viewCode') {
      if (!formData.joinCode) {
        newErrors.joinCode = 'Invite code is required';
      } else if (!/^[A-Z0-9]{4,8}$/.test(formData.joinCode.toUpperCase())) {
        newErrors.joinCode = 'Invalid invite code format (4-8 alphanumeric characters)';
      }
    } else {
      if (!formData.email) {
        newErrors.email = 'Email is required';
      } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
        newErrors.email = 'Email is invalid';
      }
      
      if (!formData.password) {
        newErrors.password = 'Password is required';
      } else if (formData.password.length < 6) {
        newErrors.password = 'Password must be at least 6 characters';
      }
      
      if (mode === 'signup') {
        if (!formData.displayName) {
          newErrors.displayName = 'Display name is required';
        }
        if (formData.password !== formData.confirmPassword) {
          newErrors.confirmPassword = 'Passwords do not match';
        }
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsLoading(true);
    setErrors({});
    
    try {
      if (mode === 'viewCode') {
        // View league by invite code
        const data = await apiService.viewLeagueByCode(formData.joinCode.toUpperCase());
        if (onViewLeague && data) {
          onViewLeague(data.leagueId);
        }
      } else {
        // Login or signup
        let userData;
        
        if (mode === 'login') {
          userData = await apiService.login(formData.email, formData.password);
        } else {
          userData = await apiService.signup(
            formData.email, 
            formData.password, 
            formData.displayName
          );
        }
        
        onLogin(userData);
      }
    } catch (error) {
      console.error('Auth error:', error);
      
      if (error.type === 'VALIDATION_ERROR' && error.details) {
        setErrors(error.details);
      } else {
        setErrors({ 
          general: error.message || 'Something went wrong. Please try again.' 
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const switchMode = (newMode) => {
    setMode(newMode);
    setFormData({
      email: '',
      password: '',
      displayName: '',
      confirmPassword: '',
      joinCode: ''
    });
    setErrors({});
  };

  return (
    <div className="auth-container">
      <div className="auth-content">
        <div className="auth-header">
          <div className="app-logo">
            <img 
              src="/assets/logo.png" 
              alt="Pick6 Logo" 
              className="logo-image"
            />
          </div>
          <p className="app-tagline">Draft teams, earn wins, dominate your league</p>
        </div>

        <div className="auth-form-container">
          <div className="auth-toggle">
            <button 
              className={`toggle-btn ${mode === 'login' ? 'active' : ''}`}
              onClick={() => switchMode('login')}
              type="button"
            >
              Sign In
            </button>
            <button 
              className={`toggle-btn ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => switchMode('signup')}
              type="button"
            >
              Sign Up
            </button>
            <button 
              className={`toggle-btn ${mode === 'viewCode' ? 'active' : ''}`}
              onClick={() => switchMode('viewCode')}
              type="button"
            >
              View League
            </button>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            {errors.general && (
              <div className="error-message general-error">
                {errors.general}
              </div>
            )}

            {mode === 'viewCode' ? (
              <>
                <div className="view-code-intro">
                  <p>Enter a league invite code to view standings and scores</p>
                </div>
                <div className="form-group">
                  <label htmlFor="joinCode">League Invite Code</label>
                  <input
                    type="text"
                    id="joinCode"
                    name="joinCode"
                    value={formData.joinCode}
                    onChange={handleInputChange}
                    className={errors.joinCode ? 'error' : ''}
                    placeholder="Enter 4-8 character code"
                    maxLength={8}
                    style={{ textTransform: 'uppercase' }}
                  />
                  {errors.joinCode && (
                    <span className="error-message">{errors.joinCode}</span>
                  )}
                </div>
              </>
            ) : (
              <>
                {mode === 'signup' && (
                  <div className="form-group">
                    <label htmlFor="displayName">Display Name</label>
                    <input
                      type="text"
                      id="displayName"
                      name="displayName"
                      value={formData.displayName}
                      onChange={handleInputChange}
                      className={errors.displayName ? 'error' : ''}
                      placeholder="Your name in the league"
                    />
                    {errors.displayName && (
                      <span className="error-message">{errors.displayName}</span>
                    )}
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="email">Email</label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    className={errors.email ? 'error' : ''}
                    placeholder="your@email.com"
                  />
                  {errors.email && (
                    <span className="error-message">{errors.email}</span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="password">Password</label>
                  <input
                    type="password"
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleInputChange}
                    className={errors.password ? 'error' : ''}
                    placeholder="Min. 6 characters"
                  />
                  {errors.password && (
                    <span className="error-message">{errors.password}</span>
                  )}
                </div>

                {mode === 'signup' && (
                  <div className="form-group">
                    <label htmlFor="confirmPassword">Confirm Password</label>
                    <input
                      type="password"
                      id="confirmPassword"
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleInputChange}
                      className={errors.confirmPassword ? 'error' : ''}
                      placeholder="Confirm your password"
                    />
                    {errors.confirmPassword && (
                      <span className="error-message">{errors.confirmPassword}</span>
                    )}
                  </div>
                )}
              </>
            )}

            <button 
              type="submit" 
              className="submit-btn"
              disabled={isLoading}
            >
              {isLoading ? (
                <LoadingSpinner />
              ) : (
                mode === 'login' ? 'Sign In' : 
                mode === 'signup' ? 'Create Account' : 
                'View League'
              )}
            </button>
          </form>

          {mode !== 'viewCode' && (
            <div className="auth-footer">
              <p>
                {mode === 'login' ? "Don't have an account? " : "Already have an account? "}
                <button 
                  type="button" 
                  className="link-btn" 
                  onClick={() => switchMode(mode === 'login' ? 'signup' : 'login')}
                >
                  {mode === 'login' ? 'Sign up' : 'Sign in'}
                </button>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const FootballIcon = () => (
  <svg width="48" height="48" viewBox="0 0 100 100" fill="none">
    <ellipse cx="50" cy="50" rx="35" ry="20" fill="#8B4513" stroke="#654321" strokeWidth="2"/>
    <path d="M20 50 L80 50" stroke="white" strokeWidth="2"/>
    <path d="M30 45 L30 55" stroke="white" strokeWidth="1.5"/>
    <path d="M40 45 L40 55" stroke="white" strokeWidth="1.5"/>
    <path d="M50 45 L50 55" stroke="white" strokeWidth="1.5"/>
    <path d="M60 45 L60 55" stroke="white" strokeWidth="1.5"/>
    <path d="M70 45 L70 55" stroke="white" strokeWidth="1.5"/>
  </svg>
);

const LoadingSpinner = () => (
  <div className="loading-spinner-inline">
    <div className="spinner"></div>
    <span>Please wait...</span>
  </div>
);

export default AuthView; 