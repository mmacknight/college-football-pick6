-- Pick6 College Football Fantasy Database Schema
-- Complete schema with all tables and views
-- This is the single source of truth for the database structure

-- Schools/Teams table
CREATE TABLE IF NOT EXISTS schools (
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
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leagues table
CREATE TABLE IF NOT EXISTS leagues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    season INTEGER NOT NULL, -- e.g. 2024
    join_code VARCHAR(8) UNIQUE NOT NULL,
    created_by UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pre_draft', -- pre_draft, drafting, active, completed
    max_teams_per_user INTEGER DEFAULT 6,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Games table - the heart of win calculations
CREATE TABLE IF NOT EXISTS games (
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
    home_id INTEGER REFERENCES schools(id) ON UPDATE CASCADE,
    home_team VARCHAR(100),
    home_classification VARCHAR(20), -- fbs, fcs, ii, iii
    home_conference VARCHAR(50),
    home_points INTEGER DEFAULT 0,
    home_line_scores INTEGER[],
    home_postgame_win_probability DECIMAL(10,9),
    home_pregame_elo INTEGER,
    home_postgame_elo INTEGER,
    away_id INTEGER REFERENCES schools(id) ON UPDATE CASCADE,
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

-- League membership (each user has exactly one team per league)
CREATE TABLE IF NOT EXISTS league_teams (
    league_id UUID REFERENCES leagues(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_name VARCHAR(100), -- optional custom team name
    draft_position INTEGER, -- 1, 2, 3, 4 (draft order within league)
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (league_id, user_id) -- composite key: one team per user per league
);

-- School assignments (which schools each user has drafted)
CREATE TABLE IF NOT EXISTS league_team_school_assignments (
    league_id UUID,
    user_id UUID,
    school_id INTEGER REFERENCES schools(id) ON UPDATE CASCADE,
    draft_round INTEGER, -- 1, 2, 3, 4
    draft_pick_overall INTEGER, -- 1-16 in 4-person league
    drafted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (league_id, user_id, school_id), -- composite key: prevents duplicate picks
    FOREIGN KEY (league_id, user_id) REFERENCES league_teams(league_id, user_id) ON DELETE CASCADE,
    UNIQUE(league_id, school_id), -- each school can only be picked once per league
    UNIQUE(league_id, draft_pick_overall) -- each overall pick number is unique
);

-- Draft state management
CREATE TABLE IF NOT EXISTS league_drafts (
    league_id UUID PRIMARY KEY REFERENCES leagues(id) ON DELETE CASCADE,
    current_pick_overall INTEGER DEFAULT 1,
    current_league_id UUID,
    current_user_id UUID,
    total_picks INTEGER, -- members * max_teams_per_user
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (current_league_id, current_user_id) REFERENCES league_teams(league_id, user_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_games_season_week ON games(season, week);
CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_id, away_id);
CREATE INDEX IF NOT EXISTS idx_games_completed ON games(completed);
CREATE INDEX IF NOT EXISTS idx_league_teams_league ON league_teams(league_id);
CREATE INDEX IF NOT EXISTS idx_league_teams_user ON league_teams(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_leagues_join_code ON leagues(join_code);
CREATE INDEX IF NOT EXISTS idx_assignments_league ON league_team_school_assignments(league_id);
CREATE INDEX IF NOT EXISTS idx_assignments_user ON league_team_school_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_assignments_school ON league_team_school_assignments(school_id);
CREATE INDEX IF NOT EXISTS idx_assignments_draft_order ON league_team_school_assignments(league_id, draft_pick_overall);

-- View for fast standings calculation
CREATE OR REPLACE VIEW league_standings AS
SELECT 
    lt.league_id,
    lt.user_id,
    u.display_name,
    lt.team_name,
    lt.draft_position,
    COUNT(CASE 
        WHEN (g.home_id = ltsa.school_id AND g.home_points > g.away_points) 
          OR (g.away_id = ltsa.school_id AND g.away_points > g.home_points)
        THEN 1 END) as wins,
    COUNT(CASE WHEN g.completed = true THEN 1 END) as games_played,
    ARRAY_AGG(DISTINCT ltsa.school_id) as team_ids
FROM league_teams lt
JOIN users u ON lt.user_id = u.id
LEFT JOIN league_team_school_assignments ltsa ON lt.league_id = ltsa.league_id AND lt.user_id = ltsa.user_id
LEFT JOIN games g ON (g.home_id = ltsa.school_id OR g.away_id = ltsa.school_id) 
    AND g.completed = true 
    AND g.season = (SELECT season FROM leagues WHERE id = lt.league_id)
GROUP BY lt.league_id, lt.user_id, u.display_name, lt.team_name, lt.draft_position
ORDER BY wins DESC, games_played ASC;

-- Note: Schools and games data should be loaded via the data loading scripts
-- to avoid API rate limits and ensure consistency
