import React from 'react';
import './GameResult.css';

const GameResult = ({ team, compact = false }) => {
  if (!team.game) {
    return (
      <div className={`game-result no-game ${compact ? 'compact' : ''}`}>
        <div className="game-basic-info">
          {!compact && (
            <>
              <span 
                className="team-dot" 
                style={{ color: team.primaryColor || '#6c757d' }}
              >
                ●
              </span>
              <span className="team-name">{team.name}</span>
            </>
          )}
          <span className="opponent-name">No game this week</span>
        </div>
        <div className="game-status-info">
          <span className="game-time"></span>
          <span className="home-away-indicator"></span>
        </div>
      </div>
    );
  }

  const { game } = team;
  const isLive = game.status === 'in_progress';
  const isCompleted = game.status === 'completed';
  const isScheduled = game.status === 'scheduled';

  // Parse score for score bug display
  let teamScore = 0;
  let opponentScore = 0;
  
  if (game.score && game.score !== 'TBD') {
    const scores = game.score.split('-');
    if (scores.length === 2) {
      teamScore = parseInt(scores[0]) || 0;
      opponentScore = parseInt(scores[1]) || 0;
    }
  }

  // Determine result for styling - much more chill
  let resultClass = 'scheduled';
  let resultIcon = '●';
  
  if (isCompleted) {
    if (teamScore > opponentScore) {
      resultClass = 'win';
      resultIcon = '●';
    } else if (teamScore < opponentScore) {
      resultClass = 'loss';
      resultIcon = '●';
    } else {
      resultClass = 'tie';
      resultIcon = '●';
    }
  } else if (isLive) {
    resultClass = 'live';
    resultIcon = '●';
  }

  // Show score bug for live and completed games
  const showScoreBug = (isLive || isCompleted) && game.score !== 'TBD';

  return (
    <div className={`game-result ${resultClass} ${compact ? 'compact' : ''}`}>
      <div className="game-basic-info">
        {!compact && (
          <>
            <span 
              className="team-dot"
              style={{ color: team.primaryColor || '#6c757d' }}
            >
              ●
            </span>
            <span className="team-name">{team.name}</span>
          </>
        )}
        <span className="vs-text">{game.isHome ? 'vs' : '@'}</span>
        <span className="opponent-name">{game.opponent}</span>
      </div>
      
      {showScoreBug ? (
        <ScoreBug 
          teamName={team.name}
          teamScore={teamScore}
          opponentName={game.opponent}
          opponentScore={opponentScore}
          isHome={game.isHome}
          isLive={isLive}
          quarter={game.quarter}
          timeRemaining={game.timeRemaining}
          teamColor={team.primaryColor}
          opponentColor={game.opponentColor}
          resultClass={resultClass}
        />
      ) : (
        <div className="game-status-info">
          <span className="game-time">
            {isScheduled ? (game.date || 'Scheduled') : game.status}
          </span>
          <span className="home-away-indicator">
            {game.isHome ? 'HOME' : 'AWAY'}
          </span>
        </div>
      )}
    </div>
  );
};

const ScoreBug = ({ 
  teamName, 
  teamScore, 
  opponentName, 
  opponentScore, 
  isHome, 
  isLive,
  quarter,
  timeRemaining,
  teamColor,
  opponentColor,
  resultClass 
}) => {
  const teamAbbrev = getTeamAbbreviation(teamName);
  const opponentAbbrev = getTeamAbbreviation(opponentName);
  
  return (
    <div className={`score-bug ${isLive ? 'live' : 'final'}`}>
      <div className="score-bug-header">
        <div className="score-teams">
          <div className="score-team">
            <span className="team-abbrev">{teamAbbrev}</span>
            <span className="team-score">{teamScore}</span>
          </div>
          <div className="score-divider">-</div>
          <div className="score-team">
            <span className="team-abbrev">{opponentAbbrev}</span>
            <span className="team-score">{opponentScore}</span>
          </div>
        </div>
        
        <div className="game-status">
          {isLive ? (
            <span className="live-status">
              LIVE {quarter && `Q${quarter}`} {timeRemaining}
            </span>
          ) : (
            <span className="final-status">FINAL</span>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper function to get team abbreviations
const getTeamAbbreviation = (teamName) => {
  const abbreviations = {
    'Alabama': 'ALA',
    'Georgia': 'UGA', 
    'Michigan': 'MICH',
    'Ohio State': 'OSU',
    'Texas': 'TEX',
    'Oregon': 'ORE',
    'Penn State': 'PSU',
    'Notre Dame': 'ND',
    'Clemson': 'CLEM',
    'USC': 'USC',
    'UCLA': 'UCLA',
    'Florida': 'UF',
    'LSU': 'LSU',
    'Auburn': 'AUB',
    'Tennessee': 'TENN',
    'Kentucky': 'UK',
    'Oklahoma': 'OU',
    'Colorado': 'CU',
    'Utah': 'UTAH',
    'Arizona State': 'ASU',
    'Washington': 'UW',
    'Kansas State': 'KSU',
    'Kansas': 'KU',
    'Boston College': 'BC',
    'North Carolina': 'UNC',
    'Virginia Tech': 'VT',
    'Wisconsin': 'WIS',
    'Purdue': 'PUR',
    'Indiana': 'IU',
    'Northwestern': 'NW',
    'Iowa': 'IOWA',
    'Minnesota': 'MINN',
    'Maryland': 'MD',
    'West Virginia': 'WVU',
    'Mississippi State': 'MSST',
    'Missouri': 'MIZ',
    'Ole Miss': 'MISS',
    'Texas A&M': 'A&M',
    'BYU': 'BYU',
    'Cincinnati': 'UC',
    'UCF': 'UCF',
    'Iowa State': 'ISU',
    'Army': 'ARMY',
    'Duke': 'DUKE',
    'Nebraska': 'NEB',
    'Michigan State': 'MSU',
    'UTEP': 'UTEP'
  };
  
  return abbreviations[teamName] || teamName.substring(0, 4).toUpperCase();
};

export default GameResult;
