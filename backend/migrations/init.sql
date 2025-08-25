-- Pick6 College Football Fantasy Database Schema

-- Schools/Teams table
CREATE TABLE schools (
    id INTEGER PRIMARY KEY, -- CollegeFootballData team_id (e.g., 333)
    team_slug VARCHAR(50) UNIQUE NOT NULL, -- normalized slug (e.g., "alabama") 
    abbreviation VARCHAR(10), -- team abbreviation (e.g., "ALA")
    name VARCHAR(100) NOT NULL,
    mascot VARCHAR(100),
    conference VARCHAR(50),
    primary_color VARCHAR(7), -- hex color code
    secondary_color VARCHAR(7), -- hex color code
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leagues table
CREATE TABLE leagues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    season INTEGER NOT NULL, -- e.g. 2024
    join_code VARCHAR(8) UNIQUE NOT NULL,
    created_by UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'draft', -- draft, active, completed
    max_teams_per_user INTEGER DEFAULT 6,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Games table - the heart of win calculations
CREATE TABLE games (
    id INTEGER PRIMARY KEY, -- CollegeFootballData game ID
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    season_type VARCHAR(20) DEFAULT 'regular', -- regular, postseason
    start_date TIMESTAMP,
    start_time_tbd BOOLEAN DEFAULT false,
    completed BOOLEAN DEFAULT false,
    neutral_site BOOLEAN DEFAULT false,
    conference_game BOOLEAN DEFAULT false,
    attendance INTEGER,
    venue_id INTEGER,
    venue VARCHAR(200),
    home_id INTEGER REFERENCES schools(id),
    home_team VARCHAR(100),
    home_classification VARCHAR(20), -- fbs, fcs, ii, iii
    home_conference VARCHAR(50),
    home_points INTEGER DEFAULT 0,
    home_line_scores INTEGER[],
    home_postgame_win_probability DECIMAL(10,9),
    home_pregame_elo INTEGER,
    home_postgame_elo INTEGER,
    away_id INTEGER REFERENCES schools(id),
    away_team VARCHAR(100),
    away_classification VARCHAR(20), -- fbs, fcs, ii, iii
    away_conference VARCHAR(50),
    away_points INTEGER DEFAULT 0,
    away_line_scores INTEGER[],
    away_postgame_win_probability DECIMAL(10,9),
    away_pregame_elo INTEGER,
    away_postgame_elo INTEGER,
    excitement_index DECIMAL(10,7),
    highlights TEXT,
    notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- League membership and team picks
CREATE TABLE league_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    league_id UUID REFERENCES leagues(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    school_id INTEGER REFERENCES schools(id),
    pick_order INTEGER, -- draft order
    picked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(league_id, school_id), -- each team can only be picked once per league
    UNIQUE(league_id, user_id, pick_order) -- each user's pick order is unique
);

-- Indexes for performance
CREATE INDEX idx_games_season_week ON games(season, week);
CREATE INDEX idx_games_teams ON games(home_id, away_id);
CREATE INDEX idx_games_completed ON games(completed);
CREATE INDEX idx_league_teams_league ON league_teams(league_id);
CREATE INDEX idx_league_teams_user ON league_teams(user_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_leagues_join_code ON leagues(join_code);

-- View for fast standings calculation
CREATE OR REPLACE VIEW league_standings AS
SELECT 
    l.id as league_id,
    l.name as league_name,
    u.id as user_id,
    u.display_name,
    COUNT(CASE 
        WHEN (g.home_id = lt.school_id AND g.home_points > g.away_points) 
          OR (g.away_id = lt.school_id AND g.away_points > g.home_points)
        THEN 1 
    END) as total_wins,
    COUNT(CASE 
        WHEN g.completed = true 
        THEN 1 
    END) as games_played,
    ARRAY_AGG(DISTINCT lt.school_id) as team_ids
FROM leagues l
JOIN league_teams lt ON l.id = lt.league_id
JOIN users u ON lt.user_id = u.id
LEFT JOIN games g ON (g.home_id = lt.school_id OR g.away_id = lt.school_id)
    AND g.season = l.season
GROUP BY l.id, l.name, u.id, u.display_name;

-- Sample schools will be loaded via API - skip manual insert for now
-- Real data with all fields will be loaded by the season_init script

-- Sample games will be added after schools are loaded
-- Real game data will be populated via API 