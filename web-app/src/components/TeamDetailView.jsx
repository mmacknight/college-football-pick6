import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import GameResult from './GameResult';
import './TeamDetailView.css';



const TeamDetailView = ({ member, currentUser, leagueId, onClose, onTeamNameUpdate }) => {
  const [viewMode, setViewMode] = useState('wins'); // 'wins' or 'games'
  const [isEditingTeamName, setIsEditingTeamName] = useState(false);
  const [editedTeamName, setEditedTeamName] = useState(member.teamName || `${member.displayName}'s Team`);
  const [isUpdating, setIsUpdating] = useState(false);
  const [saveTimeout, setSaveTimeout] = useState(null);
  const [currentWeekGames, setCurrentWeekGames] = useState(null);
  const [gamesLoading, setGamesLoading] = useState(false);
  
  const isCurrentUser = currentUser && member.displayName === currentUser.displayName;

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeout) {
        clearTimeout(saveTimeout);
      }
    };
  }, [saveTimeout]);

  // Fetch current week games when modal opens
  useEffect(() => {
    const fetchCurrentWeekGames = async () => {
      setGamesLoading(true);
      try {
        const gamesData = await apiService.fetchLeagueGamesWeek(leagueId, 'current');
        console.log('Fetched current week games:', gamesData);
        setCurrentWeekGames(gamesData);
      } catch (error) {
        console.error('Failed to fetch current week games:', error);
      } finally {
        setGamesLoading(false);
      }
    };

    fetchCurrentWeekGames();
  }, [leagueId]);

  const autoSaveTeamName = async (newName) => {
    if (!newName.trim() || newName.trim() === member.teamName || isUpdating) {
      return;
    }

    setIsUpdating(true);
    try {
      await apiService.updateTeamName(leagueId, newName.trim());
      onTeamNameUpdate(newName.trim());
    } catch (error) {
      console.error('Failed to update team name:', error);
      // Revert to original name on error
      setEditedTeamName(member.teamName || `${member.displayName}'s Team`);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleTeamNameChange = (e) => {
    const newValue = e.target.value;
    setEditedTeamName(newValue);
    
    // Clear existing timeout
    if (saveTimeout) {
      clearTimeout(saveTimeout);
    }
    
    // Set new timeout to auto-save after 1 second of no typing
    const timeoutId = setTimeout(() => {
      autoSaveTeamName(newValue);
    }, 1000);
    
    setSaveTimeout(timeoutId);
  };

  const handleTeamNameKeyPress = (e) => {
    if (e.key === 'Enter') {
      // Save immediately on Enter
      if (saveTimeout) {
        clearTimeout(saveTimeout);
        setSaveTimeout(null);
      }
      autoSaveTeamName(editedTeamName);
      setIsEditingTeamName(false);
    } else if (e.key === 'Escape') {
      // Cancel editing
      if (saveTimeout) {
        clearTimeout(saveTimeout);
        setSaveTimeout(null);
      }
      setEditedTeamName(member.teamName || `${member.displayName}'s Team`);
      setIsEditingTeamName(false);
    }
  };

  const handleBlur = () => {
    // Save immediately when losing focus
    if (saveTimeout) {
      clearTimeout(saveTimeout);
      setSaveTimeout(null);
    }
    autoSaveTeamName(editedTeamName);
    setIsEditingTeamName(false);
  };

  return (
    <div className="team-detail-overlay" onClick={onClose}>
      <div className="team-detail-container" onClick={(e) => e.stopPropagation()}>
        <header className="team-detail-header">
          <div className="header-info">
            {isCurrentUser && isEditingTeamName ? (
              <div className="team-name-editor">
                <input
                  type="text"
                  value={editedTeamName}
                  onChange={handleTeamNameChange}
                  onKeyDown={handleTeamNameKeyPress}
                  onBlur={handleBlur}
                  className="team-name-input"
                  placeholder="Enter team name"
                  disabled={isUpdating}
                  autoFocus
                />
                {isUpdating && <span className="saving-indicator">Saving...</span>}
              </div>
            ) : (
              <h2 
                className={`player-name ${isCurrentUser ? 'editable' : ''}`}
                onClick={isCurrentUser ? () => setIsEditingTeamName(true) : undefined}
              >
                {member.teamName || `${member.displayName}'s Team`}
                {isCurrentUser && <span className="edit-hint">Click to edit</span>}
              </h2>
            )}
            <p className="total-wins">{member.wins} total wins</p>
          </div>
          <button className="close-button" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </header>

        <div className="view-toggle">
          <button 
            className={`toggle-button ${viewMode === 'wins' ? 'active' : ''}`}
            onClick={() => setViewMode('wins')}
          >
            Team Wins
          </button>
          <button 
            className={`toggle-button ${viewMode === 'games' ? 'active' : ''}`}
            onClick={() => setViewMode('games')}
          >
            Current Games
          </button>
        </div>

        <div className="teams-list">
          {gamesLoading && viewMode === 'games' ? (
            <div className="games-loading">
              <div className="loading-spinner"></div>
              <p>Loading current week games...</p>
            </div>
          ) : viewMode === 'games' && currentWeekGames ? (
            // Find this member's teams in current week games
            (() => {
              const memberGames = currentWeekGames.members?.find(m => m.id === member.id);
              
              if (!memberGames || !memberGames.teams || memberGames.teams.length === 0) {
                return (
                  <div className="no-games">
                    <p>No games this week</p>
                    <p style={{fontSize: '0.8rem', color: '#888'}}>
                      Debug: Member ID: {member.id}, Found: {memberGames ? 'Yes' : 'No'}
                    </p>
                  </div>
                );
              }
              
              return memberGames.teams.map(team => (
                <TeamCard 
                  key={team.id} 
                  team={team} 
                  viewMode={viewMode}
                />
              ));
            })()
          ) : (
            // Use member.teams for wins mode or fallback
            (member.teams || []).map(team => (
              <TeamCard 
                key={team.id} 
                team={team} 
                viewMode={viewMode}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const TeamCard = ({ team, viewMode }) => {
  // Handle both old structure (team.game/team.currentGame) and new structure (team.games array)
  let gameData;
  if (viewMode === 'games') {
    // New structure: team.games is an array, old structure: team.game is a single object
    gameData = team.games || (team.game ? [team.game] : null);
  } else {
    // currentGame is still a single game object
    gameData = team.currentGame ? [team.currentGame] : null;
  }
  
  return (
    <div className="team-card">
      <div className="team-header">
        <div className="team-info">
          <div className="team-name-row">
            <span 
              className="team-dot"
              style={{ color: team.primaryColor || '#6c757d' }}
            >
              ●
            </span>
            <h3 className="team-name">{team.name}</h3>
          </div>
          <span className="team-conference">{team.conference}</span>
        </div>
      </div>

      {viewMode === 'wins' ? (
        <WinsView team={team} />
      ) : gameData && gameData.length > 0 ? (
        <GameResult team={{ ...team, games: gameData }} compact={true} />
      ) : (
        <div className="no-game-data">
          <p>No current game data available</p>
        </div>
      )}
    </div>
  );
};

const WinsView = ({ team }) => {
  const wins = team.wins || team.currentSeasonWins || 0;
  const losses = team.losses || team.currentSeasonLosses || 0;
  const totalGames = wins + losses;
  
  return (
    <div className="wins-view">
      <div className="record-container">
        <div className="record-item">
          <span className="record-number wins">{wins}</span>
          <span className="record-label">Wins</span>
        </div>
        <div className="record-separator">-</div>
        <div className="record-item">
          <span className="record-number losses">{losses}</span>
          <span className="record-label">Losses</span>
        </div>
      </div>
      {totalGames > 0 && (
        <div className="win-percentage">
          {((wins / totalGames) * 100).toFixed(1)}% win rate
        </div>
      )}
    </div>
  );
};



const CloseIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

export default TeamDetailView; 