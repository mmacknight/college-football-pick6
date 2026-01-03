import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/apiService';
import { usePolling } from '../hooks/usePolling';
import TeamDetailView from './TeamDetailView';
import GamesView from './GamesView';
import ProfessionalHeader from './ProfessionalHeader';
import './StandingsView.css';

const StandingsView = ({ league: initialLeague, user, onBackToLeagues, onStartDraft, onLeagueSettings, onUserUpdate, onLogout }) => {
  const [league, setLeague] = useState(initialLeague);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const [selectedMember, setSelectedMember] = useState(null);
  const [activeTab, setActiveTab] = useState('standings'); // 'standings' | 'games'


  // Polling for standings updates
  const pollStandings = useCallback(async () => {
    if (!initialLeague?.id) return;
    
    try {
      console.log('🔄 Polling standings for league:', initialLeague.id);
      const fetchedLeague = await apiService.fetchLeagueStandings(initialLeague.id);
      setLeague(fetchedLeague);
    } catch (error) {
      console.error('Failed to poll standings:', error);
      // Don't show error for polling failures to avoid disrupting UX
    }
  }, [initialLeague?.id]);

  // Setup polling with 1-minute intervals (60000ms)
  const { isPolling, error: pollingError, lastUpdate } = usePolling(
    pollStandings,
    60000, // 1 minute
    !!initialLeague?.id // Only poll when we have a league ID
  );

  useEffect(() => {
    if (initialLeague?.id) {
      // Always load full standings data from API, even if we have initial league data
      loadStandings();
    }
  }, [initialLeague]);

  const loadStandings = async () => {
    if (!initialLeague?.id) return;
    
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const fetchedLeague = await apiService.fetchLeagueStandings(initialLeague.id);
      setLeague(fetchedLeague);
    } catch (error) {
      console.error('Failed to load standings:', error);
      setErrorMessage(error.message);
    } finally {
      setIsLoading(false);
    }
  };



  const handleMemberTap = (member) => {
    setSelectedMember(member);
  };

  const handleCloseDetail = () => {
    setSelectedMember(null);
  };

  if (isLoading && !league) {
    return <LoadingView />;
  }

  if (errorMessage && !league) {
    return <ErrorView message={errorMessage} onRetry={loadStandings} />;
  }

  if (!league) {
    return <ErrorView message="No league data available" onRetry={loadStandings} />;
  }





  const headerActions = [];

  const handleNavigation = (page) => {
    if (page === 'dashboard') {
      onBackToLeagues();
    } else if (page === 'league') {
      // Already on league page
      window.scrollTo(0, 0);
    }
  };

  return (
    <div className="standings-container">
      {user ? (
        <ProfessionalHeader
          user={user}
          currentPage="league"
          leagueName={league.name}
          onNavigate={handleNavigation}
          onUserUpdate={onUserUpdate}
          onLogout={onLogout}
          actions={headerActions}
        />
      ) : (
        <PublicHeader leagueName={league.name} />
      )}

      <main className="standings-content">
        <LeagueHeader league={league} user={user} onLeagueSettings={user ? onLeagueSettings : null} />
        
        {/* Mobile: Tab Navigation and Content */}
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
        <div className={`mobile-tab-content ${activeTab === 'standings' ? 'active' : 'hidden'}`}>
          <StandingsList 
            members={league.members || []} 
            currentUser={user?.displayName}
            onMemberTap={handleMemberTap}
          />
        </div>
        <div className={`mobile-tab-content ${activeTab === 'games' ? 'active' : 'hidden'}`}>
          <GamesView 
            leagueId={league.id}
            onError={setErrorMessage}
          />
        </div>
        
        {/* Desktop: Two-column Layout */}
        <div className="desktop-sidebar-left">
          <section className="standings-section">
            <div className="section-header">
              <h2 className="section-title">📊 Standings</h2>
            </div>
            <StandingsList 
              members={league.members || []} 
              currentUser={user?.displayName}
              onMemberTap={handleMemberTap}
            />
          </section>
        </div>

        <div className="desktop-main-column">
          <section className="games-section">
            <div className="section-header">
              <h2 className="section-title">🏈 Games</h2>
            </div>
            <GamesView 
              leagueId={league.id}
              onError={setErrorMessage}
            />
          </section>
        </div>
      </main>

      {selectedMember && (
        <TeamDetailView 
          member={selectedMember} 
          currentUser={user}
          leagueId={league.id}
          onClose={handleCloseDetail}
          onTeamNameUpdate={(newTeamName) => {
            // Update the local state
            setLeague(prev => ({
              ...prev,
              members: prev.members.map(m => 
                m.id === selectedMember.id 
                  ? { ...m, teamName: newTeamName }
                  : m
              )
            }));
            // Update the selected member
            setSelectedMember(prev => ({ ...prev, teamName: newTeamName }));
          }}
        />
      )}
    </div>
  );
};

const LoadingView = () => (
  <div className="center-content">
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p className="loading-text">Loading standings...</p>
    </div>
  </div>
);

const ErrorView = ({ message, onRetry }) => (
  <div className="center-content">
    <div className="error-container">
      <div className="error-icon">⚠️</div>
      <h2 className="error-title">Unable to load standings</h2>
      {message && <p className="error-message">{message}</p>}
      <button className="retry-button" onClick={onRetry}>
        Try Again
      </button>
    </div>
  </div>
);

const LeagueHeader = ({ league, user, onLeagueSettings }) => {
  const isCreator = user && league.createdBy === user.id;
  
  return (
    <div className="league-header">
      <div className="league-header-content">
        <h2 className="league-name">{league.name}</h2>
        <div className="league-status-info">
          <div className="status-info">
            <StatusBadge status={league.status} />
            <span className="season-info">Season {league.season}</span>
          </div>
          {isCreator && onLeagueSettings && (
            <button 
              className="league-settings-button"
              onClick={() => onLeagueSettings(league)}
              title="League Settings"
            >
              <span className="settings-icon">⚙️</span>
              <span className="settings-text">Settings</span>
            </button>
          )}
        </div>
        <p className="tap-hint">Tap any player to see their teams</p>
      </div>
    </div>
  );
};

const TabNavigation = ({ activeTab, onTabChange }) => (
  <div className="tab-navigation">
    <button 
      className={`tab-button ${activeTab === 'standings' ? 'active' : ''}`}
      onClick={() => onTabChange('standings')}
    >
      📊 Standings
    </button>
    <button 
      className={`tab-button ${activeTab === 'games' ? 'active' : ''}`}
      onClick={() => onTabChange('games')}
    >
      🏈 Games
    </button>
  </div>
);

const StatusBadge = ({ status }) => {
  if (!status) {
    return (
      <span className="status-badge status-unknown">
        Unknown
      </span>
    );
  }
  
  // Convert status to display text
  const getDisplayText = (status) => {
    switch (status) {
      case 'pre_draft':
        return 'Pre Draft';
      case 'drafting':
        return 'Drafting';
      case 'active':
        return 'Active';
      case 'completed':
        return 'Completed';
      default:
        return status.charAt(0).toUpperCase() + status.slice(1);
    }
  };
  
  return (
    <span className={`status-badge status-${status}`}>
      {getDisplayText(status)}
    </span>
  );
};

const StandingsList = ({ members, currentUser, onMemberTap }) => {
  
  if (!members || members.length === 0) {
    return (
      <div className="standings-list">
        <div className="empty-standings">
          <div className="empty-icon">👥</div>
          <h3>No standings yet</h3>
          <p>League members will appear here once teams are drafted</p>
        </div>
      </div>
    );
  }

  return (
    <div className="standings-list">
      {members.map((member, index) => (
        <StandingRow 
          key={member.id}
          member={member}
          position={index + 1}
          isCurrentUser={member.displayName === currentUser}
          onTap={() => onMemberTap(member)}
        />
      ))}
    </div>
  );
};

const StandingRow = ({ member, position, isCurrentUser, onTap }) => (
  <div 
    className={`standing-row ${isCurrentUser ? 'current-user' : ''} clickable`}
    onClick={onTap}
    role="button"
    tabIndex={0}
    onKeyPress={(e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onTap();
      }
    }}
  >
    <div className="position-container">
      <PositionBadge position={position} />
    </div>
    
    <div className="member-info">
      <div className="member-name-container">
        <span className="member-name">{member.displayName}</span>
        {isCurrentUser && <span className="you-label">(You)</span>}
      </div>
      <div className="team-name">{member.teamName || `${member.displayName}'s Team`}</div>
      <span className="team-count">{member.teams?.length || 0} teams</span>
    </div>
    
    <div className="wins-container">
      <span className="wins-number">{member.wins || 0}</span>
      <span className="wins-label">wins</span>
      <div className="record-display">
        <span className="record-text">{member.wins || 0}-{member.losses || 0}</span>
      </div>
      <ChevronIcon />
    </div>
  </div>
);

const PositionBadge = ({ position }) => (
  <div className={`position-badge position-${position}`}>
    {position}
  </div>
);

const ChevronIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="chevron-icon">
    <polyline points="9 18 15 12 9 6"></polyline>
  </svg>
);

const PublicHeader = ({ leagueName }) => (
  <header className="public-header">
    <div className="public-header-container">
      <div className="brand-section">
        <img 
          src="/assets/logo.png" 
          alt="Pick6 Logo" 
          className="logo"
        />
        <div className="brand-text">
          <h1 className="brand-name">Pick6</h1>
          <span className="brand-tagline">College Football Fantasy</span>
        </div>
      </div>
      
      <div className="public-header-right">
        <div className="league-info">
          <h2 className="league-name">{leagueName}</h2>
        </div>
        <span className="public-badge">Public View</span>
      </div>
    </div>
  </header>
);

export default StandingsView; 