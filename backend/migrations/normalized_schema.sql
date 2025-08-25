-- Drop existing tables that need restructuring
DROP TABLE IF EXISTS league_teams CASCADE;
DROP VIEW IF EXISTS league_standings CASCADE;

-- League membership (each user has exactly one team per league)
CREATE TABLE league_teams (
    league_id UUID REFERENCES leagues(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_name VARCHAR(100), -- optional custom team name
    draft_position INTEGER, -- 1, 2, 3, 4 (draft order within league)
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (league_id, user_id) -- composite key: one team per user per league
);

-- School assignments (which schools each user has drafted)
CREATE TABLE league_team_school_assignments (
    league_id UUID,
    user_id UUID,
    school_id INTEGER REFERENCES schools(id),
    draft_round INTEGER, -- 1, 2, 3, 4
    draft_pick_overall INTEGER, -- 1-16 in 4-person league
    drafted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (league_id, user_id, school_id), -- composite key: prevents duplicate picks
    FOREIGN KEY (league_id, user_id) REFERENCES league_teams(league_id, user_id) ON DELETE CASCADE,
    UNIQUE(league_id, school_id), -- each school can only be picked once per league
    UNIQUE(league_id, draft_pick_overall) -- each overall pick number is unique
);

-- Draft state management
CREATE TABLE league_drafts (
    league_id UUID PRIMARY KEY REFERENCES leagues(id) ON DELETE CASCADE,
    current_pick_overall INTEGER DEFAULT 1,
    current_league_id UUID,
    current_user_id UUID,
    total_picks INTEGER, -- members * max_teams_per_user
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (current_league_id, current_user_id) REFERENCES league_teams(league_id, user_id)
);

-- Update league status column if it doesn't exist
ALTER TABLE leagues ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pre_draft';

-- Indexes for performance
CREATE INDEX idx_league_teams_league ON league_teams(league_id);
CREATE INDEX idx_league_teams_user ON league_teams(user_id);
CREATE INDEX idx_assignments_league ON league_team_school_assignments(league_id);
CREATE INDEX idx_assignments_user ON league_team_school_assignments(user_id);
CREATE INDEX idx_assignments_school ON league_team_school_assignments(school_id);
CREATE INDEX idx_assignments_draft_order ON league_team_school_assignments(league_id, draft_pick_overall);

-- Updated view for fast standings calculation using new schema
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
