import config from '../config/config.js';

const API_BASE_URL = config.API_BASE_URL;

class APIService {
  constructor() {
    this.token = localStorage.getItem('pick6_token');
  }

  // Refresh token from localStorage (useful when user logs in/out)
  refreshToken() {
    this.token = localStorage.getItem('pick6_token');
  }

  // Helper method to make authenticated requests
  async makeRequest(endpoint, options = {}) {
    // Refresh token from localStorage to handle login state changes
    this.token = localStorage.getItem('pick6_token');
    
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const config = {
      ...options,
      headers
    };

    console.log(`📡 API Request: ${options.method || 'GET'} ${endpoint}`);

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        const errorData = data.error || {};
        const apiError = new APIError(
          errorData.message || `HTTP ${response.status}`,
          this.getErrorType(response.status)
        );
        
        // Add validation details if available
        if (errorData.details) {
          apiError.details = errorData.details;
        }
        
        throw apiError;
      }

      return data.data; // Extract data from the success response wrapper
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      console.error('API Request failed:', error);
      throw new APIError('Network error - please check your connection', 'NETWORK_ERROR');
    }
  }

  getErrorType(status) {
    switch (status) {
      case 401: return 'UNAUTHORIZED';
      case 404: return 'NOT_FOUND';
      case 422: return 'VALIDATION_ERROR';
      default: return 'UNKNOWN_ERROR';
    }
  }

  // Authentication
  async login(email, password) {
    const response = await this.makeRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    this.token = response.token;
    localStorage.setItem('pick6_token', this.token);
    return response.user;
  }

  async signup(email, password, displayName) {
    const response = await this.makeRequest('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, displayName })
    });

    this.token = response.token;
    localStorage.setItem('pick6_token', this.token);
    return response.user;
  }

  async updateProfile(profileData) {
    return await this.makeRequest('/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData)
    });
  }

  logout() {
    this.token = null;
    localStorage.removeItem('pick6_token');
  }

  // Leagues
  async fetchUserLeagues() {
    return await this.makeRequest('/leagues');
  }

  async createLeague(name, season, teamName) {
    return await this.makeRequest('/leagues', {
      method: 'POST',
      body: JSON.stringify({ name, season, teamName })
    });
  }

  async joinLeague(joinCode, teamName) {
    return await this.makeRequest('/leagues/join', {
      method: 'POST',
      body: JSON.stringify({ joinCode, teamName })
    });
  }

  async viewLeagueByCode(joinCode) {
    // Public endpoint - no auth required
    const url = `${API_BASE_URL}/leagues/view/${joinCode}`;
    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok) {
      const errorData = data.error || {};
      throw new APIError(
        errorData.message || `HTTP ${response.status}`,
        this.getErrorType(response.status)
      );
    }

    return data.data;
  }

  // Standings
  async fetchLeagueStandings(leagueId) {
    return await this.makeRequest(`/leagues/${leagueId}/standings`);
  }

  // Games by Week
  async fetchLeagueGamesWeek(leagueId, week = 'current') {
    return await this.makeRequest(`/leagues/${leagueId}/games/week/${week}`);
  }

  // Schools/Teams
  async fetchAvailableTeams(leagueId = null, availableOnly = false) {
    const params = new URLSearchParams();
    if (leagueId) params.append('league_id', leagueId);
    if (availableOnly) params.append('available_only', 'true');
    
    const queryString = params.toString();
    const endpoint = `/schools${queryString ? `?${queryString}` : ''}`;
    
    const response = await this.makeRequest(endpoint);
    // Backend returns { schools: [...], conferences: [...] } but frontend expects just the schools array
    return response.schools || response;
  }

  // Team Selection
  async makeDraftPick(leagueId, schoolId) {
    return await this.makeRequest('/teams/select', {
      method: 'POST',
      body: JSON.stringify({ leagueId, schoolId })
    });
  }

  // Draft APIs
  async fetchMyTeams(leagueId) {
    const response = await this.makeRequest(`/leagues/${leagueId}/my-teams`);
    return response.teams || [];
  }

  async fetchDraftBoard(leagueId) {
    const response = await this.makeRequest(`/leagues/${leagueId}/draft-board`);
    return response.picks || [];
  }

  async fetchDraftStatus(leagueId) {
    const response = await this.makeRequest(`/leagues/${leagueId}/draft-status`);
    return response;
  }

  // League Administration APIs
  async fetchLeagueSettings(leagueId) {
    return await this.makeRequest(`/leagues/${leagueId}/settings`);
  }

  async updateLeagueSettings(leagueId, settings) {
    return await this.makeRequest(`/leagues/${leagueId}/settings`, {
      method: 'PUT',
      body: JSON.stringify(settings)
    });
  }

  async removePlayerFromLeague(leagueId, userId) {
    return await this.makeRequest(`/leagues/${leagueId}/players/${userId}`, {
      method: 'DELETE'
    });
  }

  async resetLeagueDraft(leagueId) {
    return await this.makeRequest(`/leagues/${leagueId}/reset-draft`, {
      method: 'POST'
    });
  }

  async updatePlayerTeams(leagueId, userId, teamAssignments) {
    return await this.makeRequest(`/leagues/${leagueId}/players/${userId}/teams`, {
      method: 'PUT',
      body: JSON.stringify({ teamAssignments })
    });
  }

  async addManualTeam(leagueId, playerName, teamName) {
    return await this.makeRequest(`/leagues/${leagueId}/manual-teams`, {
      method: 'POST',
      body: JSON.stringify({ playerName, teamName })
    });
  }

  async startLeagueDraft(leagueId) {
    return await this.makeRequest(`/leagues/${leagueId}/start-draft`, {
      method: 'POST'
    });
  }

  async skipDraftActivateLeague(leagueId) {
    return await this.makeRequest(`/leagues/${leagueId}/skip-draft`, {
      method: 'POST'
    });
  }

  async fetchLeagueLobby(leagueId) {
    return await this.makeRequest(`/leagues/${leagueId}/lobby`);
  }

  async updateTeamName(leagueId, teamName) {
    return await this.makeRequest(`/leagues/${leagueId}/team-name`, {
      method: 'PUT',
      body: JSON.stringify({ teamName })
    });
  }

  // Legacy method names for backward compatibility
  async updateTeamWins(leagueId, teamId, wins) {
    console.log(`📊 Note: updateTeamWins is not implemented - wins are calculated automatically from game results`);
  }

  async refreshScores(leagueId) {
    console.log(`🔄 Note: Score refresh will be handled by backend game sync process`);
  }
}

// Export singleton instance
export const apiService = new APIService();

// Error types
export class APIError extends Error {
  constructor(message, type = 'NETWORK_ERROR') {
    super(message);
    this.name = 'APIError';
    this.type = type;
  }
}

export const API_ERROR_TYPES = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  INVALID_RESPONSE: 'INVALID_RESPONSE',
  UNAUTHORIZED: 'UNAUTHORIZED',
  NOT_FOUND: 'NOT_FOUND'
}; 