import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import ProfessionalHeader from './ProfessionalHeader';
import './LeagueListView.css';

const LeagueListView = ({ user, onSelectLeague, onUserUpdate, onLogout }) => {
  const [leagues, setLeagues] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadUserLeagues();
  }, []);

  const loadUserLeagues = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const userLeagues = await apiService.fetchUserLeagues();
      setLeagues(userLeagues);
    } catch (err) {
      setError('Failed to load your leagues');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoinLeague = async (joinCode, teamName) => {
    try {
      await apiService.joinLeague(joinCode, teamName);
      await loadUserLeagues(); // Refresh the full list from server
      setShowJoinModal(false);
    } catch (err) {
      throw new Error('Invalid join code or league is full');
    }
  };

  const handleCreateLeague = async (leagueData) => {
    try {
      await apiService.createLeague(leagueData.name, leagueData.season, leagueData.teamName);
      await loadUserLeagues(); // Refresh the full list from server
      setShowCreateModal(false);
    } catch (err) {
      throw new Error('Failed to create league');
    }
  };

  if (isLoading && leagues.length === 0) {
    return <LoadingView />;
  }

  const handleNavigation = (page) => {
    if (page === 'dashboard') {
      // Already on dashboard, could scroll to top or refresh
      window.scrollTo(0, 0);
    }
    // Add more navigation handling as needed
  };

  return (
    <div className="league-list-container">
      <ProfessionalHeader
        user={user}
        currentPage="dashboard"
        onNavigate={handleNavigation}
        onUserUpdate={onUserUpdate}
        onLogout={onLogout}
      />

      <main className="league-list-content">
        {/* Welcome Section */}
        <div className="welcome-section">
          <div className="welcome-content">
            <h1 className="welcome-title">Welcome back, {user.displayName}!</h1>
            <p className="welcome-subtitle">
              Ready to dominate your fantasy college football leagues? Create a new league or join an existing one to get started.
            </p>
          </div>
        </div>

        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        <div className="action-buttons">
          <button 
            className="action-btn primary"
            onClick={() => setShowCreateModal(true)}
          >
            <PlusIcon />
            Create League
          </button>
          <button 
            className="action-btn secondary"
            onClick={() => setShowJoinModal(true)}
          >
            <JoinIcon />
            Join League
          </button>
        </div>

        {leagues.length === 0 ? (
          <EmptyState 
            onCreateLeague={() => setShowCreateModal(true)}
            onJoinLeague={() => setShowJoinModal(true)}
          />
        ) : (
          <LeagueGrid 
            leagues={leagues} 
            onSelectLeague={onSelectLeague}
            currentUser={user.displayName}
          />
        )}
      </main>

      {showJoinModal && (
        <JoinLeagueModal 
          onJoin={handleJoinLeague}
          onClose={() => setShowJoinModal(false)}
          user={user}
        />
      )}

      {showCreateModal && (
        <CreateLeagueModal 
          onCreate={handleCreateLeague}
          onClose={() => setShowCreateModal(false)}
          user={user}
        />
      )}
    </div>
  );
};

const LoadingView = () => (
  <div className="center-content">
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p className="loading-text">Loading your leagues...</p>
    </div>
  </div>
);

const EmptyState = ({ onCreateLeague, onJoinLeague }) => (
  <div className="empty-state">
    <div className="empty-icon">🏈</div>
    <h2 className="empty-title">No leagues yet!</h2>
    <p className="empty-description">
      Create your first league or join one with a friend's invite code
    </p>
    <div className="empty-actions">
      <button className="action-btn primary" onClick={onCreateLeague}>
        Create Your First League
      </button>
      <button className="action-btn secondary" onClick={onJoinLeague}>
        Join a League
      </button>
    </div>
  </div>
);

const LeagueGrid = ({ leagues, onSelectLeague, currentUser }) => (
  <div className="leagues-grid">
    {leagues.map(league => (
      <LeagueCard 
        key={league.id}
        league={league}
        onSelect={() => onSelectLeague(league)}
        currentUser={currentUser}
      />
    ))}
  </div>
);

const LeagueCard = ({ league, onSelect, currentUser }) => {
  return (
    <div className="league-card" onClick={onSelect}>
      <div className="league-card-header">
        <h3 className="league-name">{league.name}</h3>
        <span className={`league-status status-${league.status}`}>
          {league.status}
        </span>
      </div>
      
      <div className="league-stats">
        <div className="stat">
          <span className="stat-value">{league.memberCount || 0}</span>
          <span className="stat-label">Players</span>
        </div>
        <div className="stat">
          <span className="stat-value">{league.season}</span>
          <span className="stat-label">Season</span>
        </div>
        {league.userTeamCount > 0 && (
          <div className="stat">
            <span className="stat-value">{league.userTeamCount}</span>
            <span className="stat-label">Your Teams</span>
          </div>
        )}
      </div>

      {league.joinCode && (
        <div className="user-preview">
          <span className="join-code">Code: {league.joinCode}</span>
          {league.isCreator && <span className="creator-badge">Creator</span>}
        </div>
      )}

      <div className="league-card-footer">
        <span className="enter-hint">Tap to enter</span>
        <ChevronIcon />
      </div>
    </div>
  );
};

const JoinLeagueModal = ({ onJoin, onClose, user }) => {
  const [joinCode, setJoinCode] = useState('');
  const [teamName, setTeamName] = useState(user ? `${user.displayName}'s Team` : '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!joinCode.trim() || !teamName.trim()) return;

    setIsLoading(true);
    setError('');

    try {
      await onJoin(joinCode.trim().toUpperCase(), teamName.trim());
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Join League</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="joinCode">League Join Code</label>
            <input
              type="text"
              id="joinCode"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              placeholder="Enter 8-character code"
              maxLength="8"
              className="join-code-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="teamName">Your Team Name</label>
            <input
              type="text"
              id="teamName"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              placeholder="Enter your team name"
              maxLength="50"
              className="form-input"
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn secondary" onClick={onClose}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn primary"
              disabled={isLoading || !joinCode.trim() || !teamName.trim()}
            >
              {isLoading ? 'Joining...' : 'Join League'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const CreateLeagueModal = ({ onCreate, onClose, user }) => {
  const [formData, setFormData] = useState({
    name: '',
    season: '2025',
    teamName: user ? `${user.displayName}'s Team` : ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.teamName.trim()) return;

    setIsLoading(true);
    setError('');

    try {
      await onCreate(formData);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create League</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="leagueName">League Name</label>
            <input
              type="text"
              id="leagueName"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g., Championship Chase 2024"
            />
          </div>

          <div className="form-group">
            <label htmlFor="season">Season</label>
            <select
              id="season"
              value={formData.season}
              onChange={(e) => setFormData(prev => ({ ...prev, season: e.target.value }))}
              disabled
            >
              <option value="2025">2025</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="teamName">Your Team Name</label>
            <input
              type="text"
              id="teamName"
              value={formData.teamName}
              onChange={(e) => setFormData(prev => ({ ...prev, teamName: e.target.value }))}
              placeholder="Enter your team name"
              maxLength="50"
              className="form-input"
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn secondary" onClick={onClose}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn primary"
              disabled={isLoading || !formData.name.trim() || !formData.teamName.trim()}
            >
              {isLoading ? 'Creating...' : 'Create League'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Icons

const PlusIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
  </svg>
);

const JoinIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
  </svg>
);

const ChevronIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="9 18 15 12 9 6"></polyline>
  </svg>
);

export default LeagueListView; 