import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import { apiService } from './services/apiService';
import AuthView from './components/AuthView';
import LeagueListView from './components/LeagueListView';
import StandingsView from './components/StandingsView';
import TeamDraftView from './components/TeamDraftView';
import LeagueSettingsView from './components/LeagueSettingsView';
import LeagueLobbyView from './components/LeagueLobbyView';

// Global user context
const UserContext = React.createContext();

// Auth wrapper component
function AuthWrapper({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing auth token on app start
  useEffect(() => {
    const token = localStorage.getItem('pick6_token');
    if (token) {
      const savedUser = localStorage.getItem('pick6_user');
      if (savedUser) {
        try {
          setUser(JSON.parse(savedUser));
        } catch (e) {
          localStorage.removeItem('pick6_user');
          localStorage.removeItem('pick6_token');
        }
      }
    }
    setIsLoading(false);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('pick6_user', JSON.stringify(userData));
  };

  const handleUserUpdate = (updatedUserData) => {
    setUser(updatedUserData);
    localStorage.setItem('pick6_user', JSON.stringify(updatedUserData));
  };

  const handleLogout = () => {
    apiService.logout();
    localStorage.removeItem('pick6_user');
    setUser(null);
  };

  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div style={{ 
          width: '40px', 
          height: '40px', 
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #3498db',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
        <p>Loading Pick6...</p>
      </div>
    );
  }

  return (
    <UserContext.Provider value={{ user, handleLogin, handleUserUpdate, handleLogout }}>
      {children}
    </UserContext.Provider>
  );
}

// Route wrapper for protected routes
function ProtectedRoute({ children }) {
  const { user } = React.useContext(UserContext);
  return user ? children : <Navigate to="/auth" replace />;
}

// Auth route component
function AuthRoute() {
  const { user, handleLogin } = React.useContext(UserContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      navigate('/leagues', { replace: true });
    }
  }, [user, navigate]);

  const handleViewLeague = (leagueId) => {
    // Navigate to standings page
    navigate(`/leagues/${leagueId}/standings`);
  };

  return <AuthView onLogin={handleLogin} onViewLeague={handleViewLeague} />;
}

// Leagues route component
function LeaguesRoute() {
  const { user, handleUserUpdate, handleLogout } = React.useContext(UserContext);
  const navigate = useNavigate();

  const handleSelectLeague = async (league) => {
    // Check league status first
    if (league.status === 'pre_draft') {
      navigate(`/leagues/${league.id}/lobby`);
      return;
    }
    
    if (league.status === 'drafting') {
      navigate(`/leagues/${league.id}/draft`);
      return;
    }
    
    // For active/completed leagues, go to standings first
    if (league.status === 'active' || league.status === 'completed') {
      navigate(`/leagues/${league.id}/standings`);
      return;
    }
    
    // For any other status, check if user needs to draft teams
    try {
      const leagueStandings = await apiService.fetchLeagueStandings(league.id);
      const userEntry = leagueStandings.members?.find(member => member.displayName === user.displayName);
      
      const userTeamCount = userEntry?.teams?.length || 0;
      
      if (userTeamCount === 0) {
        // User needs to draft teams
        navigate(`/leagues/${league.id}/draft`);
      } else {
        // User has teams, go to standings
        navigate(`/leagues/${league.id}/standings`);
      }
    } catch (error) {
      // If league has no standings yet, user probably needs to draft
      navigate(`/leagues/${league.id}/draft`);
    }
  };

  return (
    <LeagueListView 
      user={user}
      onSelectLeague={handleSelectLeague}
      onUserUpdate={handleUserUpdate}
      onLogout={handleLogout}
    />
  );
}

// Draft route component
function DraftRoute() {
  const { user, handleUserUpdate, handleLogout } = React.useContext(UserContext);
  const { leagueId } = useParams();
  const navigate = useNavigate();
  const [league, setLeague] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadLeagueData();
  }, [leagueId]);

  const loadLeagueData = async () => {
    try {
      setLoading(true);
      setError(null);
      // Use lobby API to get league status - it's accessible to all members
      const response = await apiService.fetchLeagueLobby(leagueId);
      setLeague(response.league);
    } catch (err) {
      console.error('Failed to load league data:', err);
      setError('Failed to load league information');
    } finally {
      setLoading(false);
    }
  };

  const handleDraftComplete = () => {
    navigate(`/leagues/${leagueId}/standings`);
  };

  const handleBackToLeagues = () => {
    navigate('/leagues');
  };

  const handleGoToLobby = () => {
    navigate(`/leagues/${leagueId}/lobby`);
  };

  const handleViewStandings = () => {
    navigate(`/leagues/${leagueId}/standings`);
  };

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div style={{ 
          width: '40px', 
          height: '40px', 
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #3498db',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
        <p>Loading league...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem',
        padding: '20px',
        textAlign: 'center'
      }}>
        <h2 style={{ color: '#dc3545' }}>Error</h2>
        <p>{error}</p>
        <button 
          onClick={handleBackToLeagues}
          style={{
            background: '#6c757d',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          Back to Leagues
        </button>
      </div>
    );
  }

  // League status guards
  if (league?.status === 'pre_draft') {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '2rem',
        padding: '20px',
        textAlign: 'center',
        background: '#f8f9fa'
      }}>
        <div style={{
          background: 'white',
          padding: '40px',
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          maxWidth: '500px'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>⏳</div>
          <h2 style={{ color: '#2c3e50', marginBottom: '16px' }}>Draft Not Started Yet</h2>
          <p style={{ color: '#6c757d', marginBottom: '24px', lineHeight: '1.5' }}>
            The draft for <strong>{league.name}</strong> hasn't started yet. 
            Wait in the lobby for the league creator to begin the draft.
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button 
              onClick={handleGoToLobby}
              style={{
                background: '#007bff',
                color: 'white',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              Go to Lobby
            </button>
            <button 
              onClick={handleBackToLeagues}
              style={{
                background: '#6c757d',
                color: 'white',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              Back to Leagues
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (league?.status === 'active') {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '2rem',
        padding: '20px',
        textAlign: 'center',
        background: '#f8f9fa'
      }}>
        <div style={{
          background: 'white',
          padding: '40px',
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          maxWidth: '500px'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>🎉</div>
          <h2 style={{ color: '#28a745', marginBottom: '16px' }}>Draft Complete!</h2>
          <p style={{ color: '#6c757d', marginBottom: '24px', lineHeight: '1.5' }}>
            The draft for <strong>{league.name}</strong> has finished. 
            All teams have been selected and the season is now active.
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button 
              onClick={handleViewStandings}
              style={{
                background: '#28a745',
                color: 'white',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              View Standings
            </button>
            <button 
              onClick={handleBackToLeagues}
              style={{
                background: '#6c757d',
                color: 'white',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              Back to Leagues
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!league || league.status !== 'drafting') {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem',
        padding: '20px',
        textAlign: 'center'
      }}>
        <h2 style={{ color: '#dc3545' }}>Invalid League State</h2>
        <p>This league is not currently in a draftable state.</p>
        <button 
          onClick={handleBackToLeagues}
          style={{
            background: '#6c757d',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          Back to Leagues
        </button>
      </div>
    );
  }

  return (
    <TeamDraftView 
      league={league}
      user={user}
      onDraftComplete={handleDraftComplete}
      onBackToLeagues={handleBackToLeagues}
      onUserUpdate={handleUserUpdate}
      onLogout={handleLogout}
    />
  );
}

// Standings route component
function StandingsRoute() {
  const { user, handleUserUpdate, handleLogout } = React.useContext(UserContext);
  const { leagueId } = useParams();
  const navigate = useNavigate();
  const [league, setLeague] = useState(null);

  useEffect(() => {
    // In a real app, you'd fetch league data by ID
    setLeague({ 
      id: leagueId, 
      name: 'League Standings',
      createdBy: user?.id // Mock that current user is creator - remove this when using real API
    });
  }, [leagueId, user]);

  const handleBackToLeagues = () => {
    // If user is not authenticated, redirect to auth page
    if (!user) {
      navigate('/auth');
    } else {
      navigate('/leagues');
    }
  };

  const handleLeagueSettings = (league) => {
    // Only allow settings access for authenticated users
    if (!user) {
      navigate('/auth');
    } else {
      navigate(`/leagues/${league.id}/settings`);
    }
  };

  if (!league) return <div>Loading...</div>;

  return (
    <StandingsView 
      league={league}
      user={user}
      onBackToLeagues={handleBackToLeagues}
      onLeagueSettings={handleLeagueSettings}
      onUserUpdate={handleUserUpdate}
      onLogout={handleLogout}
    />
  );
}

// Settings route component
function SettingsRoute() {
  const { user, handleUserUpdate, handleLogout } = React.useContext(UserContext);
  const { leagueId } = useParams();
  const navigate = useNavigate();
  const [league, setLeague] = useState(null);

  useEffect(() => {
    // In a real app, you'd fetch league data by ID
    setLeague({ 
      id: leagueId, 
      name: 'League Settings',
      createdBy: user?.id // Mock that current user is creator
    });
  }, [leagueId, user]);

  const handleBack = () => {
    navigate(`/leagues/${leagueId}/standings`);
  };

  const handleLeagueUpdated = (updatedLeague) => {
    console.log('League updated:', updatedLeague);
    // Update local state if needed
  };

  if (!league) return <div>Loading...</div>;

  return (
    <LeagueSettingsView 
      league={league}
      user={user}
      onBack={handleBack}
      onLeagueUpdated={handleLeagueUpdated}
      onUserUpdate={handleUserUpdate}
      onLogout={handleLogout}
    />
  );
}

// Lobby route component
function LobbyRoute() {
  const { user, handleUserUpdate, handleLogout } = React.useContext(UserContext);
  const navigate = useNavigate();
  const { leagueId } = useParams();

  const handleBack = () => {
    navigate('/leagues');
  };

  const handleStartDraft = async () => {
    try {
      await apiService.startLeagueDraft(leagueId);
      // Navigate to draft view after starting
      navigate(`/leagues/${leagueId}/draft`);
    } catch (err) {
      console.error('Failed to start draft:', err);
      // Could show error message here
    }
  };

  const handleSkipDraft = async () => {
    try {
      await apiService.skipDraftActivateLeague(leagueId);
      // Navigate to league settings after activation
      navigate(`/leagues/${leagueId}/settings`);
    } catch (err) {
      console.error('Failed to activate league:', err);
      // Could show error message here
    }
  };

  const handleLeagueSettings = () => {
    navigate(`/leagues/${leagueId}/settings`);
  };

  return (
    <LeagueLobbyView 
      leagueId={leagueId}
      user={user}
      onBack={handleBack}
      onStartDraft={handleStartDraft}
      onSkipDraft={handleSkipDraft}
      onLeagueSettings={handleLeagueSettings}
      onUserUpdate={handleUserUpdate}
      onLogout={handleLogout}
    />
  );
}

// Main App component
function App() {
  return (
    <Router>
      <AuthWrapper>
        <Routes>
          <Route path="/auth" element={<AuthRoute />} />
          <Route path="/leagues" element={
            <ProtectedRoute>
              <LeaguesRoute />
            </ProtectedRoute>
          } />
          <Route path="/leagues/:leagueId/draft" element={
            <ProtectedRoute>
              <DraftRoute />
            </ProtectedRoute>
          } />
          <Route path="/leagues/:leagueId/standings" element={<StandingsRoute />} />
          <Route path="/leagues/:leagueId/lobby" element={
            <ProtectedRoute>
              <LobbyRoute />
            </ProtectedRoute>
          } />
          <Route path="/leagues/:leagueId/settings" element={
            <ProtectedRoute>
              <SettingsRoute />
            </ProtectedRoute>
          } />
          <Route path="/" element={<Navigate to="/auth" replace />} />
        </Routes>
      </AuthWrapper>
    </Router>
  );
}

export default App; 