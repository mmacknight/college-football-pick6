import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import ProfessionalHeader from './ProfessionalHeader';
import './LeagueSettingsView.css';

const LeagueSettingsView = ({ league, user, onBack, onLeagueUpdated, onUserUpdate, onLogout }) => {
  const [leagueData, setLeagueData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: '', maxTeamsPerUser: 6 });
  const [actionLoading, setActionLoading] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [editingPlayer, setEditingPlayer] = useState(null);
  const [editingTeams, setEditingTeams] = useState([]);
  const [availableSchools, setAvailableSchools] = useState([]);
  const [schoolSearchTerm, setSchoolSearchTerm] = useState('');

  // Check if current user is the league creator
  const isCreator = user && league && user.id === league.createdBy;

  useEffect(() => {
    if (isCreator) {
      loadLeagueSettings();
      loadAvailableSchools();
    } else {
      setError('Only the league creator can access settings');
      setIsLoading(false);
    }
  }, [league.id, isCreator]);

  const loadAvailableSchools = async () => {
    try {
      const schools = await apiService.fetchAvailableTeams();
      setAvailableSchools(schools);
    } catch (err) {
      console.error('Failed to load schools:', err);
    }
  };

  const loadLeagueSettings = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiService.fetchLeagueSettings(league.id);
      setLeagueData(data);
      setEditForm({
        name: data.league.name,
        maxTeamsPerUser: data.league.maxTeamsPerUser
      });
    } catch (err) {
      console.error('Failed to load league settings:', err);
      setError(err.message || 'Failed to load league settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateSettings = async (e) => {
    e.preventDefault();
    setActionLoading('update');
    setError(null);
    setSuccessMessage('');

    try {
      const response = await apiService.updateLeagueSettings(league.id, editForm);
      
      // Update local state
      setLeagueData(prev => ({
        ...prev,
        league: { ...prev.league, ...response }
      }));
      
      setIsEditing(false);
      setSuccessMessage('League settings updated successfully!');
      
      // Notify parent component
      if (onLeagueUpdated) {
        onLeagueUpdated(response);
      }
      
    } catch (err) {
      console.error('Failed to update league settings:', err);
      setError(err.message || 'Failed to update league settings');
    } finally {
      setActionLoading('');
    }
  };

  const handleRemovePlayer = async (playerId, playerName) => {
    if (!confirm(`Are you sure you want to remove ${playerName} from the league? This will delete all their draft picks.`)) {
      return;
    }

    setActionLoading(`remove-${playerId}`);
    setError(null);
    setSuccessMessage('');

    try {
      await apiService.removePlayerFromLeague(league.id, playerId);
      
      // Reload settings to get updated member list
      await loadLeagueSettings();
      setSuccessMessage(`${playerName} has been removed from the league`);
      
    } catch (err) {
      console.error('Failed to remove player:', err);
      setError(err.message || 'Failed to remove player');
    } finally {
      setActionLoading('');
    }
  };

  const handleResetDraft = async () => {
    if (!confirm('Are you sure you want to reset the draft? This will delete ALL draft picks and return the league to pre-draft status.')) {
      return;
    }

    setActionLoading('reset');
    setError(null);
    setSuccessMessage('');

    try {
      const response = await apiService.resetLeagueDraft(league.id);
      
      // Reload settings to get updated state
      await loadLeagueSettings();
      setSuccessMessage(`Draft reset successfully - ${response.picksRemoved} picks removed`);
      
    } catch (err) {
      console.error('Failed to reset draft:', err);
      setError(err.message || 'Failed to reset draft');
    } finally {
      setActionLoading('');
    }
  };

  const handleStartDraft = async () => {
    if (!confirm('Are you sure you want to start the draft? Once started, league settings cannot be modified and players will begin drafting teams.')) {
      return;
    }

    setActionLoading('start-draft');
    setError(null);
    setSuccessMessage('');

    try {
      await apiService.startLeagueDraft(league.id);
      
      // Reload settings to get updated league status
      await loadLeagueSettings();
      setSuccessMessage('Draft started successfully! Players can now begin drafting teams.');
      
    } catch (err) {
      console.error('Failed to start draft:', err);
      setError(err.message || 'Failed to start draft');
    } finally {
      setActionLoading('');
    }
  };

  const handleEditPlayerTeams = async (player) => {
    setEditingPlayer(player);
    // Initialize with current teams or empty array
    setEditingTeams(player.teams || []);
  };

  const handleSavePlayerTeams = async () => {
    if (!editingPlayer) return;

    setActionLoading(`save-teams-${editingPlayer.userId}`);
    setError(null);
    setSuccessMessage('');

    try {
      const teamAssignments = editingTeams.map((team, index) => ({
        schoolId: team.id,
        draftRound: index + 1
      }));

      await apiService.updatePlayerTeams(league.id, editingPlayer.userId, teamAssignments);
      
      // Reload settings to get updated data
      await loadLeagueSettings();
      setEditingPlayer(null);
      setEditingTeams([]);
      setSuccessMessage(`Updated ${editingPlayer.displayName}'s teams successfully!`);
      
    } catch (err) {
      console.error('Failed to update player teams:', err);
      setError(err.message || 'Failed to update player teams');
    } finally {
      setActionLoading('');
    }
  };

  const handleCancelEditTeams = () => {
    setEditingPlayer(null);
    setEditingTeams([]);
  };

  const handleAddTeam = (school) => {
    if (editingTeams.length >= leagueData?.league?.maxTeamsPerUser) {
      setError(`Cannot add more than ${leagueData.league.maxTeamsPerUser} teams`);
      return;
    }
    
    if (editingTeams.find(team => team.id === school.id)) {
      setError('Team already selected');
      return;
    }
    
    setEditingTeams([...editingTeams, school]);
    setError(null);
  };

  const handleRemoveTeam = (schoolId) => {
    setEditingTeams(editingTeams.filter(team => team.id !== schoolId));
  };

  if (!isCreator) {
    return (
      <div className="league-settings-container">
        <ProfessionalHeader
          user={user}
          currentPage="settings"
          leagueName={league?.name}
          onNavigate={() => onBack()}
          onUserUpdate={onUserUpdate}
          onLogout={onLogout}
        />
        <div className="league-settings-content">
          <div className="error-message">
            Only the league creator can access settings
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="league-settings-container">
        <ProfessionalHeader
          user={user}
          currentPage="settings"
          leagueName={league?.name}
          onNavigate={() => onBack()}
          onUserUpdate={onUserUpdate}
          onLogout={onLogout}
        />
        <div className="league-settings-content">
          <div className="loading-message">Loading league settings...</div>
        </div>
      </div>
    );
  }

  if (error && !leagueData) {
    return (
      <div className="league-settings-container">
        <ProfessionalHeader
          user={user}
          currentPage="settings"
          leagueName={league?.name}
          onNavigate={() => onBack()}
          onUserUpdate={onUserUpdate}
          onLogout={onLogout}
        />
        <div className="league-settings-content">
          <div className="error-message">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="league-settings-container">
      <ProfessionalHeader
        user={user}
        currentPage="settings"
        leagueName={leagueData?.league?.name}
        onNavigate={() => onBack()}
        onLogout={onLogout}
      />

      <div className="league-settings-content">
        {successMessage && (
        <div className="success-message">
          ✅ {successMessage}
        </div>
      )}

      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}

      {/* League Information */}
      <div className="settings-section">
        <h3>League Information</h3>
        {!isEditing ? (
          <div className="league-info">
            <div className="info-row">
              <label>League Name:</label>
              <span>{leagueData?.league?.name}</span>
            </div>
            <div className="info-row">
              <label>Season:</label>
              <span>{leagueData?.league?.season}</span>
            </div>
            <div className="info-row">
              <label>Status:</label>
              <span className={`status ${leagueData?.league?.status}`}>
                {leagueData?.league?.status}
              </span>
            </div>
            <div className="info-row">
              <label>Join Code:</label>
              <span className="join-code">{leagueData?.league?.joinCode}</span>
            </div>
            <div className="info-row">
              <label>Max Teams per Player:</label>
              <span>{leagueData?.league?.maxTeamsPerUser}</span>
            </div>
            
            {leagueData?.league?.status === 'pre_draft' && (
              <button 
                className="edit-button"
                onClick={() => setIsEditing(true)}
              >
                Edit Settings
              </button>
            )}
          </div>
        ) : (
          <form onSubmit={handleUpdateSettings} className="edit-form">
            <div className="form-group">
              <label>League Name:</label>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                required
                maxLength={100}
              />
            </div>
            <div className="form-group">
              <label>Max Teams per Player:</label>
              <input
                type="number"
                value={editForm.maxTeamsPerUser}
                onChange={(e) => setEditForm(prev => ({ ...prev, maxTeamsPerUser: parseInt(e.target.value) }))}
                min={1}
                max={10}
                required
              />
            </div>
            <div className="form-actions">
              <button 
                type="submit" 
                className="save-button"
                disabled={actionLoading === 'update'}
              >
                {actionLoading === 'update' ? 'Saving...' : 'Save Changes'}
              </button>
              <button 
                type="button" 
                className="cancel-button"
                onClick={() => {
                  setIsEditing(false);
                  setEditForm({
                    name: leagueData.league.name,
                    maxTeamsPerUser: leagueData.league.maxTeamsPerUser
                  });
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Draft Management */}
      {leagueData?.league?.status === 'pre_draft' && (
        <div className="settings-section">
          <h3>Draft Management</h3>
          <div className="draft-management">
            <div className="draft-info">
              <h4>Ready to Start Draft?</h4>
              <p>Once you start the draft, players will be able to begin selecting their teams. League settings will be locked during the draft.</p>
              <p><strong>Current Members:</strong> {leagueData?.stats?.totalMembers || 0} players</p>
            </div>
            <button
              className="start-draft-button"
              onClick={handleStartDraft}
              disabled={actionLoading === 'start-draft' || (leagueData?.stats?.totalMembers || 0) < 2}
            >
              {actionLoading === 'start-draft' ? 'Starting Draft...' : 'Start Draft'}
            </button>
            {(leagueData?.stats?.totalMembers || 0) < 2 && (
              <p className="draft-requirement">Need at least 2 players to start the draft</p>
            )}
          </div>
        </div>
      )}

      {/* League Statistics */}
      <div className="settings-section">
        <h3>League Statistics</h3>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-label">Members:</span>
            <span className="stat-value">{leagueData?.stats?.totalMembers || 0}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Total Picks:</span>
            <span className="stat-value">{leagueData?.stats?.totalPicks || 0}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Max Possible:</span>
            <span className="stat-value">{leagueData?.stats?.maxPossiblePicks || 0}</span>
          </div>
        </div>
      </div>

      {/* Member Management */}
      <div className="settings-section">
        <h3>Member Management</h3>
        <div className="members-list">
          {leagueData?.members?.map(member => (
            <div key={member.userId} className="member-item">
              <div className="member-info">
                <div className="member-name">
                  {member.displayName}
                  {member.isCreator && <span className="creator-badge">Creator</span>}
                </div>
                <div className="member-details">
                  Team: {member.teamName || 'No team name'} • 
                  Picks: {member.pickCount}/{leagueData.league.maxTeamsPerUser}
                  {member.draftPosition && ` • Draft Position: ${member.draftPosition}`}
                </div>
                {member.teams && member.teams.length > 0 && (
                  <div className="member-teams">
                    <strong>Drafted Teams:</strong>
                    <div className="teams-list-compact">
                      {member.teams.map((team, index) => (
                        <span key={team.id} className="team-chip">
                          {team.name}
                          {index < member.teams.length - 1 && ', '}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="member-actions">
                <button
                  className="edit-teams-button"
                  onClick={() => handleEditPlayerTeams(member)}
                  disabled={actionLoading.startsWith('save-teams')}
                >
                  Edit Teams
                </button>
                {!member.isCreator && (
                  <button
                    className="remove-button"
                    onClick={() => handleRemovePlayer(member.userId, member.displayName)}
                    disabled={actionLoading === `remove-${member.userId}`}
                  >
                    {actionLoading === `remove-${member.userId}` ? 'Removing...' : 'Remove'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Danger Zone */}
      {leagueData?.league?.status !== 'pre_draft' && (
        <div className="settings-section danger-zone">
          <h3>Danger Zone</h3>
          <div className="danger-actions">
            <div className="danger-item">
              <div className="danger-info">
                <h4>Reset Draft</h4>
                <p>Remove all draft picks and return league to pre-draft status. This cannot be undone.</p>
              </div>
              <button
                className="danger-button"
                onClick={handleResetDraft}
                disabled={actionLoading === 'reset'}
              >
                {actionLoading === 'reset' ? 'Resetting...' : 'Reset Draft'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Team Editing Modal */}
      {editingPlayer && (
        <div className="modal-overlay">
          <div className="modal-content team-edit-modal">
            <div className="modal-header">
              <h3>Edit Teams for {editingPlayer.displayName}</h3>
              <button className="modal-close" onClick={handleCancelEditTeams}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="current-teams">
                <h4>Current Teams ({editingTeams.length}/{leagueData?.league?.maxTeamsPerUser})</h4>
                <div className="teams-list">
                  {editingTeams.map((team, index) => (
                    <div key={team.id} className="team-item">
                      <span className="team-info">
                        <strong>{team.name}</strong> ({team.conference})
                      </span>
                      <button 
                        className="remove-team-button"
                        onClick={() => handleRemoveTeam(team.id)}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  {editingTeams.length === 0 && (
                    <p className="no-teams">No teams selected</p>
                  )}
                </div>
              </div>

              <div className="available-teams">
                <h4>Available Teams</h4>
                <div className="search-container">
                  <input
                    type="text"
                    placeholder="Search schools..."
                    value={schoolSearchTerm}
                    onChange={(e) => setSchoolSearchTerm(e.target.value)}
                    className="school-search"
                  />
                </div>
                <div className="teams-grid">
                  {availableSchools
                    .filter(school => !editingTeams.find(team => team.id === school.id))
                    .filter(school => 
                      !schoolSearchTerm || 
                      school.name.toLowerCase().includes(schoolSearchTerm.toLowerCase()) ||
                      school.conference.toLowerCase().includes(schoolSearchTerm.toLowerCase())
                    )
                    .map(school => (
                    <button
                      key={school.id}
                      className="school-button"
                      onClick={() => handleAddTeam(school)}
                      disabled={editingTeams.length >= leagueData?.league?.maxTeamsPerUser}
                    >
                      <div className="school-name">{school.name}</div>
                      <div className="school-conference">{school.conference}</div>
                    </button>
                  ))}
                </div>
                {availableSchools
                  .filter(school => !editingTeams.find(team => team.id === school.id))
                  .filter(school => 
                    !schoolSearchTerm || 
                    school.name.toLowerCase().includes(schoolSearchTerm.toLowerCase()) ||
                    school.conference.toLowerCase().includes(schoolSearchTerm.toLowerCase())
                  ).length === 0 && schoolSearchTerm && (
                  <p className="no-results">No schools found matching "{schoolSearchTerm}"</p>
                )}
              </div>
            </div>

            <div className="modal-footer">
              <button 
                className="save-button"
                onClick={handleSavePlayerTeams}
                disabled={actionLoading === `save-teams-${editingPlayer.userId}`}
              >
                {actionLoading === `save-teams-${editingPlayer.userId}` ? 'Saving...' : 'Save Teams'}
              </button>
              <button 
                className="cancel-button"
                onClick={handleCancelEditTeams}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

export default LeagueSettingsView;
