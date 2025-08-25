import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import ProfessionalHeader from './ProfessionalHeader';
import './LeagueLobbyView.css';

const LeagueLobbyView = ({ leagueId, user, onStartDraft, onBack, onLeagueSettings, onUserUpdate, onLogout }) => {
  const [league, setLeague] = useState(null);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copySuccess, setCopySuccess] = useState(false);

  useEffect(() => {
    loadLeagueData();
  }, [leagueId]);

  const loadLeagueData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use the league lobby API (accessible to all members)
      const response = await apiService.fetchLeagueLobby(leagueId);
      setLeague(response.league);
      setMembers(response.members || []);
      
    } catch (err) {
      console.error('Failed to load league data:', err);
      setError('Failed to load league information');
    } finally {
      setLoading(false);
    }
  };

  const copyLeagueCode = async () => {
    try {
      await navigator.clipboard.writeText(league.joinCode);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy league code:', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = league.joinCode;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  const handleStartDraft = () => {
    if (onStartDraft) {
      onStartDraft();
    }
  };

  if (loading) {
    return (
      <div className="lobby-loading">
        <div className="loading-spinner"></div>
        <p>Loading league lobby...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="lobby-error">
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={onBack} className="btn secondary">
          Back to Leagues
        </button>
      </div>
    );
  }

  if (!league) {
    return (
      <div className="lobby-error">
        <h2>League Not Found</h2>
        <p>This league could not be found or you don't have access to it.</p>
        <button onClick={onBack} className="btn secondary">
          Back to Leagues
        </button>
      </div>
    );
  }

  const isCreator = String(league.createdBy) === String(user?.id);
  const canStartDraft = isCreator && members.length >= 2;

  const headerActions = [];

  const handleNavigation = (page) => {
    if (page === 'dashboard') {
      onBack();
    } else if (page === 'league') {
      onBack();
    }
    // Add more navigation handling as needed
  };

  return (
    <div className="lobby-container">
      <ProfessionalHeader
        user={user}
        currentPage="league"
        leagueName={league.name}
        onNavigate={handleNavigation}
        onUserUpdate={onUserUpdate}
        onLogout={onLogout}
        actions={headerActions}
      />

      <main className="lobby-content">
        <div className="league-status-header">
          <div className="status-info">
            <span className="status-badge pre-draft">PRE-DRAFT</span>
            <span className="season-info">Season {league.season}</span>
          </div>
          {isCreator && onLeagueSettings && (
            <button 
              className="league-settings-button"
              onClick={onLeagueSettings}
              title="League Settings"
            >
              <span className="settings-icon">⚙️</span>
              <span className="settings-text">Settings</span>
            </button>
          )}
        </div>

        {/* League Code Section */}
        <div className="lobby-section">
          <h2>Invite Friends</h2>
          <div className="league-code-container">
            <div className="league-code">
              <span className="code-label">League Code:</span>
              <span className="code-value">{league.joinCode}</span>
            </div>
            <button 
              onClick={copyLeagueCode}
              className={`copy-button ${copySuccess ? 'success' : ''}`}
            >
              {copySuccess ? '✓ Copied!' : '📋 Copy Code'}
            </button>
          </div>
          <p className="invite-instructions">
            Share this code with friends so they can join your league!
          </p>
        </div>

        {/* Players Section */}
        <div className="lobby-section">
          <div className="players-header">
            <h2>Players ({members.length})</h2>
            <span className="max-teams-info">
              Up to {league.maxTeamsPerUser || 6} teams per player
            </span>
          </div>
          
          {members.length === 0 ? (
            <div className="no-players">
              <p>No players have joined yet. Share the league code to get started!</p>
            </div>
          ) : (
            <div className="players-list">
              {members.map((member) => (
                <div key={member.userId} className="player-card">
                  <div className="player-info">
                    <div className="player-name">
                      {member.displayName}
                      {member.isCreator && <span className="creator-badge">Creator</span>}
                    </div>
                    <div className="team-name">{member.teamName}</div>
                  </div>
                  <div className="join-time">
                    Joined {new Date(member.joinedAt).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Draft Control Section */}
        {isCreator && (
          <div className="lobby-section draft-control">
            <h2>Draft Control</h2>
            <div className="draft-info">
              <p>
                {members.length < 2 
                  ? `Need at least 2 players to start the draft (currently ${members.length})`
                  : `Ready to start! ${members.length} players have joined.`
                }
              </p>
              {canStartDraft && (
                <p className="draft-ready">
                  🎯 All set! Click "Start Draft" when everyone is ready.
                </p>
              )}
            </div>
            <button 
              onClick={handleStartDraft}
              disabled={!canStartDraft}
              className={`start-draft-btn ${canStartDraft ? 'ready' : 'disabled'}`}
            >
              {canStartDraft ? '🚀 Start Draft' : `Need ${2 - members.length} More Player${2 - members.length === 1 ? '' : 's'}`}
            </button>
          </div>
        )}

        {!isCreator && (
          <div className="lobby-section waiting-info">
            <h2>Waiting for Draft</h2>
            <p>The league creator will start the draft when everyone is ready.</p>
            <div className="waiting-indicator">
              <div className="pulse-dot"></div>
              <span>Waiting for {league.createdByName || 'creator'} to start the draft...</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default LeagueLobbyView;
