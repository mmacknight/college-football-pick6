import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/apiService';
import { usePolling } from '../hooks/usePolling';
import GameResult from './GameResult';
import './GamesView.css';

const GamesView = ({ leagueId, onError }) => {
  const [gamesData, setGamesData] = useState(null);
  const [currentWeek, setCurrentWeek] = useState(null);
  const [availableWeeks, setAvailableWeeks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);


  useEffect(() => {
    if (leagueId) {
      loadGamesForWeek('current');
    }
  }, [leagueId]);

  // Polling function for games data
  const pollGamesData = useCallback(async () => {
    if (!leagueId || !currentWeek) return;
    
    try {
      console.log('🔄 Polling games data for league:', leagueId, 'week:', currentWeek);
      const data = await apiService.fetchLeagueGamesWeek(leagueId, currentWeek);
      setGamesData(data);
    } catch (error) {
      console.error('Failed to poll games data:', error);
      // Don't show error for polling failures to avoid disrupting UX
    }
  }, [leagueId, currentWeek]);

  // Setup polling with 1-minute intervals (60000ms) - only when we have data to poll
  const { isPolling } = usePolling(
    pollGamesData,
    60000, // 1 minute
    !!(leagueId && currentWeek && gamesData) // Only poll when we have league ID, current week, and initial data
  );

  const loadGamesForWeek = async (week) => {
    setIsLoading(true);
    try {
      const data = await apiService.fetchLeagueGamesWeek(leagueId, week);
      setGamesData(data);
      setCurrentWeek(data.week.number);
      
      // Generate available weeks (1 to current + 3)
      const maxWeek = Math.min(data.week.number + 3, 17);
      const weeks = Array.from({ length: maxWeek }, (_, i) => i + 1);
      setAvailableWeeks(weeks);
      
    } catch (error) {
      console.error('Failed to load games:', error);
      if (onError) {
        onError(error.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleWeekChange = (newWeek) => {
    if (newWeek >= 1 && newWeek <= 17 && newWeek !== currentWeek) {
      loadGamesForWeek(newWeek);
    }
  };

  if (isLoading && !gamesData) {
    return <LoadingView />;
  }

  if (!gamesData) {
    return <ErrorView message="No games data available" />;
  }

  return (
    <div className="games-view">
      <WeekSelector 
        currentWeek={currentWeek}
        weekInfo={gamesData.week}
        availableWeeks={availableWeeks}
        onWeekChange={handleWeekChange}
        isLoading={isLoading}
      />
      <MemberGamesList 
        members={gamesData.members || []} 
        isLoading={isLoading}
      />
    </div>
  );
};

const WeekSelector = ({ currentWeek, weekInfo, availableWeeks, onWeekChange, isLoading }) => {
  const canGoPrevious = currentWeek > 1;
  const canGoNext = currentWeek < 17 && availableWeeks.includes(currentWeek + 1);

  return (
    <div className="week-selector">
      <button 
        className="week-nav-btn" 
        onClick={() => onWeekChange(currentWeek - 1)}
        disabled={!canGoPrevious || isLoading}
        aria-label="Previous week"
      >
        ←
      </button>
      
      <div className="week-info">
        <span className="week-label">{weekInfo.label}</span>
        <span className="week-dates">{weekInfo.dateRange}</span>
        {weekInfo.isCurrent && <span className="current-badge">Current</span>}
      </div>
      
      <button 
        className="week-nav-btn" 
        onClick={() => onWeekChange(currentWeek + 1)}
        disabled={!canGoNext || isLoading}
        aria-label="Next week"
      >
        →
      </button>
    </div>
  );
};

const MemberGamesList = ({ members, isLoading }) => {
  if (isLoading) {
    return (
      <div className="member-games-loading">
        <div className="loading-spinner"></div>
        <p>Loading games...</p>
      </div>
    );
  }

  if (!members || members.length === 0) {
    return (
      <div className="no-members">
        <p>No league members found</p>
      </div>
    );
  }

  return (
    <div className="member-games-list">
      {members.map(member => (
        <MemberWeekCard key={member.id} member={member} />
      ))}
    </div>
  );
};

const MemberWeekCard = ({ member }) => {
  return (
    <div className="member-week-card">
      <div className="member-header">
        <span className="member-name">{member.displayName}</span>
        <span className="week-record">{member.weekRecord}</span>
      </div>
      <div className="team-games">
        {member.teams.map(team => (
          <GameResult key={team.id} team={team} />
        ))}
      </div>
    </div>
  );
};



const LoadingView = () => (
  <div className="games-loading">
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p className="loading-text">Loading games...</p>
    </div>
  </div>
);

const ErrorView = ({ message }) => (
  <div className="games-error">
    <div className="error-container">
      <div className="error-icon">⚠️</div>
      <h3 className="error-title">Unable to load games</h3>
      <p className="error-message">{message}</p>
    </div>
  </div>
);

export default GamesView;
