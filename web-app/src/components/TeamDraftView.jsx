import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/apiService';
import { useWebSocket } from '../hooks/useWebSocket';
import ProfessionalHeader from './ProfessionalHeader';
import './TeamDraftView.css';

const TeamDraftView = ({ league, user, onDraftComplete, onBackToLeagues, onUserUpdate, onLogout }) => {
  // Tab state
  const [activeTab, setActiveTab] = useState('draft');
  
  // Data state
  const [availableTeams, setAvailableTeams] = useState([]);
  const [selectedTeams, setSelectedTeams] = useState([]);
  const [draftBoard, setDraftBoard] = useState([]);
  const [draftStatus, setDraftStatus] = useState(null);
  
  // UI state
  const [isLoading, setIsLoading] = useState(true);
  const [isDrafting, setIsDrafting] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedConference, setSelectedConference] = useState('all');



  useEffect(() => {
    loadInitialData();
  }, [league.id]);

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        loadAvailableTeams(),
        loadMyTeams(),
        loadDraftBoard(),
        loadDraftStatus()
      ]);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAvailableTeams = async () => {
    try {
      const teams = await apiService.fetchAvailableTeams(league.id, true); // availableOnly = true
      setAvailableTeams(teams);
    } catch (err) {
      setError('Failed to load available teams');
      throw err;
    }
  };

  const loadMyTeams = async () => {
    try {
      const myTeams = await apiService.fetchMyTeams(league.id);
      setSelectedTeams(myTeams);
    } catch (err) {
      console.error('Failed to load my teams:', err);
      // Fall back to empty array instead of throwing
      setSelectedTeams([]);
    }
  };

  const loadDraftBoard = async () => {
    try {
      const board = await apiService.fetchDraftBoard(league.id);
      setDraftBoard(board);
    } catch (err) {
      console.error('Failed to load draft board:', err);
      // Fall back to empty array
      setDraftBoard([]);
    }
  };

  const loadDraftStatus = async () => {
    try {
      const status = await apiService.fetchDraftStatus(league.id);
      setDraftStatus(status);
    } catch (err) {
      console.error('Failed to load draft status:', err);
      // Fall back to null
      setDraftStatus(null);
    }
  };

  // Real-time updates via WebSocket
  const handleDraftUpdate = useCallback(async (data) => {
    console.log('📡 Received draft update:', data);
    
    // Refresh all draft-related data when we get an update
    try {
      await Promise.all([
        loadMyTeams(),
        loadDraftBoard(),
        loadDraftStatus(),
        loadAvailableTeams()
      ]);
    } catch (err) {
      console.error('Failed to refresh data after WebSocket update:', err);
    }
  }, []);

  // WebSocket connection for draft updates only
  const { isConnected, send } = useWebSocket([
    ['draft_update', handleDraftUpdate],
    ['league_update', handleDraftUpdate] // League changes also trigger refresh
  ]);

  // Join league room when component mounts
  useEffect(() => {
    if (isConnected && league?.id) {
      console.log(`📋 Joining league ${league.id} for real-time updates`);
      send('join_league', { league_id: league.id });
      
      return () => {
        console.log(`📋 Leaving league ${league.id}`);
        send('leave_league', { league_id: league.id });
      };
    }
  }, [isConnected, league?.id, send]);

  const handleTeamSelect = async (team) => {
    if (selectedTeams.length >= (league.maxTeamsPerUser || 6)) {
      setError(`You can only select up to ${league.maxTeamsPerUser || 6} teams`);
      return;
    }

    // Check if it's the user's turn
    if (draftStatus?.draftStatus === 'active' && !draftStatus?.isUserTurn) {
      setError(`It's ${draftStatus.currentUserName || "someone else"}'s turn to pick`);
      return;
    }

    setIsDrafting(true);
    setError(null);

    try {
      await apiService.makeDraftPick(league.id, team.id);
      
      // Update local state immediately for better UX
      setSelectedTeams(prev => [...prev, team]);
      setAvailableTeams(prev => prev.filter(t => t.id !== team.id));
      
      // Refresh all data to sync with server
      await Promise.all([
        loadMyTeams(),
        loadDraftBoard(),
        loadDraftStatus()
      ]);
      
      // Note: Don't auto-redirect when user completes their draft
      // Let them stay and watch the rest of the draft, or manually navigate back
    } catch (err) {
      setError(err.message || 'Failed to select team');
      // Revert optimistic update on error
      loadInitialData();
    } finally {
      setIsDrafting(false);
    }
  };

  const getConferences = () => {
    const conferences = [...new Set(availableTeams.map(team => team.conference))];
    return conferences.sort();
  };

  const getFilteredTeams = () => {
    return availableTeams.filter(team => {
      const matchesSearch = team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           team.mascot?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesConference = selectedConference === 'all' || team.conference === selectedConference;
      return matchesSearch && matchesConference;
    });
  };

  if (isLoading) {
    return <LoadingView />;
  }

  const getDraftSubtitle = () => {
    if (selectedTeams.length >= (league.maxTeamsPerUser || 6)) {
      return "✅ Your draft is complete! Watching other players...";
    }
    if (draftStatus?.draftStatus === 'active') {
      return draftStatus?.isUserTurn ? "Your turn to pick!" : `${draftStatus.currentUserName || 'Someone'}'s turn to pick`;
    }
    if (draftStatus?.draftStatus === 'waiting') {
      return 'Waiting for draft to start';
    }
    return 'Draft in progress';
  };

  const getDraftProgress = () => {
    if (selectedTeams.length >= (league.maxTeamsPerUser || 6)) {
      return "DRAFT COMPLETE";
    }
    if (draftStatus?.isUserTurn) {
      return "YOUR TURN";
    }
    return `Pick ${draftStatus?.currentPickOverall || 1} of ${draftStatus?.totalPicks || 12}`;
  };

  // STRICT: Only allow picks when draft is active AND it's specifically the user's turn
  const canMakePick = () => {
    // Must not be in the middle of making a pick
    if (isDrafting) return false;
    
    // League must be in drafting status (not active/complete)
    if (league.status !== 'drafting') return false;
    
    // Draft status must be 'active' (not complete or unknown)
    if (draftStatus?.draftStatus !== 'active') return false;
    
    // It must specifically be the current user's turn
    if (!draftStatus?.isUserTurn) return false;
    
    // User must not have completed their draft already
    if (selectedTeams.length >= (league.maxTeamsPerUser || 6)) return false;
    
    return true;
  };

  const headerActions = [
    {
      text: getDraftProgress(),
      variant: selectedTeams.length >= (league.maxTeamsPerUser || 6) ? 'success' : 
               draftStatus?.isUserTurn ? 'warning' : 'default'
    },
    {
      text: isConnected ? '🟢 Live Updates' : '🔴 Offline',
      variant: 'default'
    }
  ];

  const handleNavigation = (page) => {
    if (page === 'dashboard') {
      onBackToLeagues();
    } else if (page === 'league') {
      onBackToLeagues();
    } else if (page === 'draft') {
      // Already on draft page
      window.scrollTo(0, 0);
    }
  };

  return (
    <div className="team-draft-container">
      <ProfessionalHeader
        user={user}
        currentPage="draft"
        leagueName={league.name}
        onNavigate={handleNavigation}
        onUserUpdate={onUserUpdate}
        onLogout={onLogout}
        actions={headerActions}
      />
      
      {/* Sticky Tab Navigation */}
      <nav className="tab-navigation">
        <button 
          className={`tab ${activeTab === 'draft' ? 'active' : ''}`}
          onClick={() => setActiveTab('draft')}
        >
          <span className="tab-icon">🏈</span>
          <span className="tab-text">Available Teams</span>
        </button>
        <button 
          className={`tab ${activeTab === 'board' ? 'active' : ''}`}
          onClick={() => setActiveTab('board')}
        >
          <span className="tab-icon">📋</span>
          <span className="tab-text">Draft Board</span>
        </button>
      </nav>

      <main className="draft-content">
        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Mobile: Tab Content */}
        {activeTab === 'draft' && (
          <div className="mobile-tab-content">
            <DraftTab
              availableTeams={availableTeams}
              selectedTeams={selectedTeams}
              searchTerm={searchTerm}
              selectedConference={selectedConference}
              isDrafting={isDrafting}
              draftStatus={draftStatus}
              onSearchChange={setSearchTerm}
              onConferenceChange={setSelectedConference}
              onTeamSelect={handleTeamSelect}
              getConferences={getConferences}
              getFilteredTeams={getFilteredTeams}
              canMakePick={canMakePick}
            />
          </div>
        )}

        {activeTab === 'board' && (
          <div className="mobile-tab-content">
            <DraftBoardTab
              draftBoard={draftBoard}
              draftStatus={draftStatus}
              league={league}
            />
          </div>
        )}

        {/* Desktop: Two-column Layout */}
        
        {/* LEFT COLUMN (BIG): Available Teams to Draft */}
        <div className="draft-main-column">
          <section className="available-teams-section">
            <div className="section-header">
              <h2 className="section-title">Available Teams</h2>
              <div className="filters">
                <input
                  type="text"
                  className="search-input"
                  placeholder="Search teams..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                <select
                  className="conference-filter"
                  value={selectedConference}
                  onChange={(e) => setSelectedConference(e.target.value)}
                >
                  <option value="all">All Conferences</option>
                  {getConferences().map(conf => (
                    <option key={conf} value={conf}>{conf}</option>
                  ))}
                </select>
              </div>
            </div>
            
            {getFilteredTeams().length === 0 ? (
              <div className="no-teams-message">
                <p>No teams available matching your criteria</p>
              </div>
            ) : (
              <div className="available-teams-grid">
                {getFilteredTeams().map(team => (
                  <AvailableTeamCard
                    key={team.id}
                    team={team}
                    onSelect={() => handleTeamSelect(team)}
                    disabled={!canMakePick()}
                  />
                ))}
              </div>
            )}
          </section>
        </div>

        {/* RIGHT COLUMN (SMALL): Draft Progress & Player Selections */}
        <div className="draft-sidebar-right">
          <section className="draft-status-section">
            <h2 className="section-title">Draft Status</h2>
            <DraftBoardContent 
              draftBoard={draftBoard}
              draftStatus={draftStatus}
              league={league}
            />
          </section>
        </div>
      </main>
    </div>
  );
};

const LoadingView = () => (
  <div className="center-content">
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p className="loading-text">Loading available teams...</p>
    </div>
  </div>
);

const SelectedTeamCard = ({ team }) => (
  <div className="selected-team-card">
    <div 
      className="team-color-stripe" 
      style={{ backgroundColor: team.primaryColor || '#666' }}
    ></div>
    <div className="team-info">
      <h3 className="team-name">{team.name}</h3>
      <p className="team-mascot">{team.mascot}</p>
      <p className="team-conference">{team.conference}</p>
    </div>
    <div className="selected-badge">✓</div>
  </div>
);

const AvailableTeamCard = ({ team, onSelect, disabled }) => (
  <button
    className="available-team-card"
    onClick={onSelect}
    disabled={disabled}
  >
    <div 
      className="team-color-stripe" 
      style={{ backgroundColor: team.primaryColor || '#666' }}
    ></div>
    <div className="team-info">
      <h3 className="team-name">{team.name}</h3>
      <p className="team-mascot">{team.mascot}</p>
      <p className="team-conference">{team.conference}</p>
      {team.currentSeasonWins !== undefined && (
        <p className="team-record">{team.currentSeasonWins}W - {team.currentSeasonLosses || 0}L</p>
      )}
    </div>
    <div className="select-action">
      {disabled ? <LoadingDots /> : 'Select'}
    </div>
  </button>
);

const LoadingDots = () => (
  <div className="loading-dots">
    <span></span>
    <span></span>
    <span></span>
  </div>
);



// Desktop Content Components (reusable between mobile tabs and desktop layout)
const MyTeamsContent = ({ selectedTeams, league, draftStatus }) => {
  if (selectedTeams.length === 0) {
    return (
      <div className="my-teams-list">
        {/* Show all upcoming pick slots when no teams drafted yet */}
        {Array.from({ length: league.maxTeamsPerUser }, (_, i) => (
          <div key={`upcoming-${i}`} className="upcoming-pick-card">
            <div className="pick-number">{i + 1}</div>
            <div className="upcoming-pick-info">
              <h3>Upcoming Pick</h3>
              <p>Round {Math.ceil((i + 1) / 4)} • Pick {i + 1}</p>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="my-teams-list">
      {selectedTeams.map((team, index) => (
        <div key={team.id} className="my-team-card">
          <div 
            className="team-color-stripe" 
            style={{ backgroundColor: team.school?.primaryColor || '#666' }}
          ></div>
          <div className="team-info">
            <h3 className="team-name">{team.school?.name}</h3>
            <p className="team-mascot">{team.school?.mascot}</p>
            <p className="team-conference">{team.school?.conference}</p>
            <span className="pick-details">Round {team.draftRound} • Pick {team.draftPickOverall}</span>
          </div>
          <div className="pick-number">{index + 1}</div>
        </div>
      ))}

      {/* Show upcoming pick slots */}
      {Array.from({ length: league.maxTeamsPerUser - selectedTeams.length }, (_, i) => (
        <div key={`upcoming-${i}`} className="upcoming-pick-card">
          <div className="pick-number">{selectedTeams.length + i + 1}</div>
          <div className="upcoming-pick-info">
            <h3>Upcoming Pick</h3>
            <p>Round {Math.ceil((selectedTeams.length + i + 1) / 4)} • Pick {selectedTeams.length + i + 1}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

const DraftBoardContent = ({ draftBoard, draftStatus, league }) => {
  // If draft hasn't started, show draft order
  if (draftStatus?.draftStatus === 'waiting' || draftStatus?.draftStatus === 'active') {
    const draftOrder = draftStatus?.draftOrder || [];
    
    if (draftOrder.length === 0) {
      return (
        <div className="no-draft-data">
          <div className="empty-state">
            <span className="empty-icon">📋</span>
            <h3>Draft starting soon</h3>
            <p>Draft order will appear here</p>
          </div>
        </div>
      );
    }

    // Helper function to calculate snake draft pattern
    const getSnakeDraftInfo = (currentPickOverall, totalPlayers) => {
      const round = Math.ceil(currentPickOverall / totalPlayers);
      const isReverseRound = round % 2 === 0;
      let pickInRound = ((currentPickOverall - 1) % totalPlayers) + 1;
      
      if (isReverseRound) {
        pickInRound = totalPlayers - pickInRound + 1;
      }
      
      return { round, pickInRound, isReverseRound };
    };

    const totalPlayers = draftOrder.length;
    const currentPick = draftStatus?.currentPickOverall || 1;
    const { round: currentRound, pickInRound: currentPickInRound, isReverseRound } = getSnakeDraftInfo(currentPick, totalPlayers);

    // Group completed picks by player for roster view
    const playerRosters = {};
    draftOrder.forEach(player => {
      playerRosters[player.userId] = draftBoard.filter(pick => pick.userId === player.userId);
    });

    return (
      <>
        {/* Current Pick Status */}
        {draftStatus && (
          <div className="current-pick-status">
            <div className="pick-info">
              <div className="pick-number-display">
                <span className="pick-label">Pick</span>
                <span className="pick-number-large">{currentPick}</span>
                <span className="pick-total">of {draftStatus.totalPicks || 12}</span>
              </div>
              <div className="round-info">
                <div className="round-display">Round {currentRound}</div>
                <div className="direction-indicator">
                  {isReverseRound ? (
                    <span className="draft-direction reverse">⟵ Reverse Order</span>
                  ) : (
                    <span className="draft-direction forward">⟶ Forward Order</span>
                  )}
                </div>
              </div>
            </div>
            <div className="current-picker-info">
              <div className="picker-name">
                {draftStatus.isUserTurn ? "Your turn!" : `${draftStatus.currentUserName || 'Someone'}'s turn`}
              </div>
              <div className="picker-context">
                Pick #{Math.ceil(currentPick / totalPlayers)} for this player
              </div>
            </div>
          </div>
        )}

        {/* Snake Draft Visualization */}
        <div className="snake-draft-section">
          <h3 className="section-title">Draft Order & Teams</h3>
          <div className="snake-draft-grid">
            {draftOrder.map((player, index) => {
              const playerPicks = playerRosters[player.userId] || [];
              const isCurrentPicker = draftStatus?.currentUserId === player.userId;
              const nextPickRound = playerPicks.length + 1;
              
              return (
                <div 
                  key={player.userId} 
                  className={`player-roster-card ${isCurrentPicker ? 'current-picker' : ''}`}
                >
                  <div className="player-header">
                    <div className="player-position">#{player.draftPosition}</div>
                    <div className="player-details">
                      <div className="player-name">{player.displayName}</div>
                      <div className="team-name">{player.teamName}</div>
                    </div>
                    <div className="picks-count">
                      {playerPicks.length}/{league.maxTeamsPerUser || 6}
                    </div>
                  </div>
                  
                  {/* Player's drafted teams */}
                  <div className="player-picks">
                    {playerPicks.map((pick, pickIndex) => (
                      <div key={pick.id} className="pick-item">
                        <div className="pick-round">R{pick.round}</div>
                        <div className="picked-school">
                          <div 
                            className="school-color-dot" 
                            style={{ backgroundColor: pick.school?.primaryColor || '#666' }}
                          ></div>
                          <span className="school-name">{pick.school?.name}</span>
                        </div>
                      </div>
                    ))}
                    
                    {/* Show upcoming pick slots */}
                    {Array.from({ length: (league.maxTeamsPerUser || 6) - playerPicks.length }, (_, i) => (
                      <div key={`upcoming-${i}`} className="pick-item upcoming">
                        <div className="pick-round">R{nextPickRound + i}</div>
                        <div className="upcoming-pick">
                          {isCurrentPicker && i === 0 ? (
                            <span className="current-turn">← Picking now</span>
                          ) : (
                            <span className="upcoming-text">Upcoming</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent Picks Timeline */}
        {draftBoard && draftBoard.length > 0 && (
          <div className="recent-picks-section">
            <h3 className="section-title">Recent Picks</h3>
            <div className="recent-picks-timeline">
              {draftBoard
                .slice(-6) // Show last 6 picks
                .reverse() // Most recent first
                .map(pick => (
                  <div key={pick.id} className="timeline-pick">
                    <div className="pick-header">
                      <span className="pick-number">#{pick.pickNumber}</span>
                      <span className="round-info">R{pick.round}</span>
                    </div>
                    <div className="pick-details">
                      <div className="drafter">{pick.userName}</div>
                      <div className="drafted-school">
                        <div 
                          className="school-color-dot" 
                          style={{ backgroundColor: pick.school?.primaryColor || '#666' }}
                        ></div>
                        <span>{pick.school?.name}</span>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </>
    );
  }

  // Draft complete - show same roster format but with completion message
  const draftOrder = draftStatus?.draftOrder || [];
  
  // Group completed picks by player for roster view
  const playerRosters = {};
  draftOrder.forEach(player => {
    playerRosters[player.userId] = draftBoard.filter(pick => pick.userId === player.userId);
  });

  return (
    <>
      {/* Draft Complete Status */}
      <div className="current-pick-status draft-complete">
        <div className="pick-info">
          <div className="pick-number-display">
            <span className="pick-label">Draft</span>
            <span className="pick-number-large">✅</span>
            <span className="pick-total">Complete!</span>
          </div>
          <div className="round-info">
            <div className="round-display">All {draftStatus?.totalPicks || draftBoard.length} picks made</div>
          </div>
        </div>
        <div className="current-picker-info">
          <div className="picker-name">Draft Complete!</div>
          <div className="picker-context">All teams have been selected</div>
        </div>
      </div>

      {/* Same Snake Draft Visualization but completed */}
      <div className="snake-draft-section">
        <h3 className="section-title">Final Rosters</h3>
        <div className="snake-draft-grid">
          {draftOrder.map((player, index) => {
            const playerPicks = playerRosters[player.userId] || [];
            
            return (
              <div 
                key={player.userId} 
                className="player-roster-card completed"
              >
                <div className="player-header">
                  <div className="player-position">#{player.draftPosition}</div>
                  <div className="player-details">
                    <div className="player-name">{player.displayName}</div>
                    <div className="team-name">{player.teamName}</div>
                  </div>
                  <div className="picks-count">
                    {playerPicks.length}/{league.maxTeamsPerUser || 6}
                  </div>
                </div>
                
                {/* Player's drafted teams */}
                <div className="player-picks">
                  {playerPicks.map((pick, pickIndex) => (
                    <div key={pick.id} className="pick-item">
                      <div className="pick-round">R{pick.round}</div>
                      <div className="picked-school">
                        <div 
                          className="school-color-dot" 
                          style={{ backgroundColor: pick.school?.primaryColor || '#666' }}
                        ></div>
                        <span className="school-name">{pick.school?.name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Picks Timeline - show all picks for completed draft */}
      {draftBoard && draftBoard.length > 0 && (
        <div className="recent-picks-section">
          <h3 className="section-title">All Draft Picks</h3>
          <div className="recent-picks-timeline">
            {draftBoard
              .slice(-10) // Show last 10 picks for completed draft
              .reverse() // Most recent first
              .map(pick => (
                <div key={pick.id} className="timeline-pick">
                  <div className="pick-header">
                    <span className="pick-number">#{pick.pickNumber}</span>
                    <span className="round-info">R{pick.round}</span>
                  </div>
                  <div className="pick-details">
                    <div className="drafter">{pick.userName}</div>
                    <div className="drafted-school">
                      <div 
                        className="school-color-dot" 
                        style={{ backgroundColor: pick.school?.primaryColor || '#666' }}
                      ></div>
                      <span>{pick.school?.name}</span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </>
  );
};

// Tab Components
const DraftTab = ({ 
  availableTeams, 
  selectedTeams, 
  searchTerm, 
  selectedConference, 
  isDrafting,
  draftStatus,
  onSearchChange,
  onConferenceChange,
  onTeamSelect,
  getConferences,
  getFilteredTeams,
  canMakePick
}) => (
  <div className="tab-content">
    <section className="available-teams-section">
      <div className="section-header">
        <h2 className="section-title">Available Teams</h2>
        <div className="filters">
          <input
            type="text"
            placeholder="Search teams..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="search-input"
          />
          <select
            value={selectedConference}
            onChange={(e) => onConferenceChange(e.target.value)}
            className="conference-filter"
          >
            <option value="all">All Conferences</option>
            {getConferences().map(conference => (
              <option key={conference} value={conference}>{conference}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="available-teams-grid">
        {getFilteredTeams().map(team => (
          <AvailableTeamCard
            key={team.id}
            team={team}
            onSelect={() => onTeamSelect(team)}
            disabled={!canMakePick()}
          />
        ))}
      </div>

      {getFilteredTeams().length === 0 && (
        <div className="no-teams-message">
          {searchTerm || selectedConference !== 'all' 
            ? 'No teams match your filters' 
            : 'No teams available'}
        </div>
      )}
    </section>
  </div>
);

const DraftBoardTab = ({ draftBoard, draftStatus, league }) => (
  <div className="tab-content">
    <div className="draft-board-header">
      <h2 className="section-title">Draft</h2>
    </div>
    <DraftBoardContent draftBoard={draftBoard} draftStatus={draftStatus} league={league} />
  </div>
);

export default TeamDraftView;
