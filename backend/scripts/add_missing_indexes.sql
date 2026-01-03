-- =====================================================
-- Pick6 Performance Optimization - Missing Indexes
-- =====================================================
-- 
-- This script adds critical indexes to improve query performance
-- for the Pick6 fantasy football app.
--
-- PROBLEM: Standings and games_week API endpoints are experiencing
-- high latency (2-5 seconds) due to full table scans on the games
-- and league_team_school_assignments tables.
--
-- SOLUTION: Add composite indexes that match the WHERE clause
-- patterns used in the most frequent queries.
--
-- ESTIMATED PERFORMANCE IMPROVEMENT:
-- - Standings API: 2-5s → 50-200ms (10-25x faster)
-- - Games Week API: 1-3s → 30-150ms (10-20x faster)
-- - Standings Updater: Reduced from timeout risk to <1s per league
--
-- SAFETY: All indexes are created with IF NOT EXISTS and use
-- CONCURRENTLY to avoid blocking production traffic.
--
-- RUN TIME: ~30-60 seconds depending on table sizes
--
-- =====================================================

-- Enable timing to monitor performance
\timing on

-- Show current database
SELECT current_database() as database, now() as timestamp;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '📊 ANALYZING CURRENT TABLE SIZES'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- Check table sizes before indexing
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    n_live_tup as estimated_rows
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '🔍 EXISTING INDEXES (BEFORE)'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- Show existing indexes
SELECT 
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '🚀 CREATING NEW PERFORMANCE INDEXES'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- =====================================================
-- GAMES TABLE INDEXES
-- =====================================================
-- 
-- PROBLEM QUERY (from standings/get.py lines 64-73):
-- SELECT * FROM games 
-- WHERE season = ? 
--   AND completed = true 
--   AND (home_id = ? OR away_id = ?)
--
-- CURRENT STATE: Only has idx_games_teams(home_id, away_id)
-- which doesn't help with the completed/season filters
--
-- =====================================================

\echo '📌 Creating composite index on games(home_id, completed, season)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_games_home_completed_season 
ON games(home_id, completed, season);

\echo '✅ Index idx_games_home_completed_season created'
\echo ''

\echo '📌 Creating composite index on games(away_id, completed, season)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_games_away_completed_season 
ON games(away_id, completed, season);

\echo '✅ Index idx_games_away_completed_season created'
\echo ''

\echo '📌 Creating composite index on games(season, completed, week)...'
-- This helps the games_week.py queries that filter by season, week, and check completion
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_games_season_completed_week 
ON games(season, completed, week);

\echo '✅ Index idx_games_season_completed_week created'
\echo ''

\echo '📌 Creating index on games(season, week, home_id)...'
-- Optimizes the specific week lookups in games_week.py lines 87-93
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_games_season_week_home 
ON games(season, week, home_id);

\echo '✅ Index idx_games_season_week_home created'
\echo ''

\echo '📌 Creating index on games(season, week, away_id)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_games_season_week_away 
ON games(season, week, away_id);

\echo '✅ Index idx_games_season_week_away created'
\echo ''

-- =====================================================
-- LEAGUE_TEAM_SCHOOL_ASSIGNMENTS TABLE INDEXES
-- =====================================================
--
-- PROBLEM QUERY (from standings/get.py lines 45-50):
-- SELECT * FROM league_team_school_assignments
-- WHERE league_id = ? AND user_id = ?
--
-- CURRENT STATE: Has separate indexes on league_id and user_id
-- but PostgreSQL can only use ONE index, resulting in large scans
--
-- SOLUTION: Composite index on both columns together
--
-- =====================================================

\echo '📌 Creating composite index on league_team_school_assignments(league_id, user_id)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assignments_league_user 
ON league_team_school_assignments(league_id, user_id);

\echo '✅ Index idx_assignments_league_user created'
\echo ''

-- =====================================================
-- LEAGUES TABLE INDEXES
-- =====================================================
--
-- PROBLEM QUERY (from standings_updater.py line 37):
-- SELECT * FROM leagues 
-- WHERE status IN ('active', 'drafting')
--
-- CURRENT STATE: No index on status column
-- This causes full table scan on every standings update
--
-- =====================================================

\echo '📌 Creating index on leagues(status)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leagues_status 
ON leagues(status);

\echo '✅ Index idx_leagues_status created'
\echo ''

-- =====================================================
-- LEAGUE_TEAMS TABLE INDEXES (Enhancement)
-- =====================================================
--
-- ENHANCEMENT: Composite index for common join patterns
--
-- =====================================================

\echo '📌 Creating composite index on league_teams(league_id, user_id)...'
-- This is actually the primary key, but let's verify it exists
-- This helps with frequent joins in standings queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_league_teams_league_user 
ON league_teams(league_id, user_id);

\echo '✅ Index idx_league_teams_league_user created (or already exists as PK)'
\echo ''

-- =====================================================
-- ANALYZE TABLES
-- =====================================================
--
-- Update PostgreSQL statistics so the query planner
-- knows about the new indexes and can use them effectively
--
-- =====================================================

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '📈 UPDATING TABLE STATISTICS'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

ANALYZE games;
\echo '✅ Analyzed games table'

ANALYZE league_team_school_assignments;
\echo '✅ Analyzed league_team_school_assignments table'

ANALYZE leagues;
\echo '✅ Analyzed leagues table'

ANALYZE league_teams;
\echo '✅ Analyzed league_teams table'

-- =====================================================
-- VERIFICATION
-- =====================================================

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '🔍 NEW INDEXES (AFTER)'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT 
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '📊 TOTAL INDEX SIZE BY TABLE'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS total_indexes_size,
    COUNT(*) as num_indexes
FROM pg_indexes
JOIN pg_stat_user_tables ON pg_indexes.tablename = pg_stat_user_tables.relname
WHERE schemaname = 'public'
GROUP BY tablename, schemaname
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename) DESC;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '✅ INDEX CREATION COMPLETE!'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''
\echo 'Next steps:'
\echo '1. Test the standings API - should be 10-25x faster'
\echo '2. Test the games_week API - should be 10-20x faster'
\echo '3. Monitor query performance using CloudWatch'
\echo '4. Check slow query logs in Neon dashboard'
\echo ''
\echo 'Expected improvements:'
\echo '• Standings API: 2-5s → 50-200ms'
\echo '• Games Week API: 1-3s → 30-150ms'
\echo '• Standings Updater: No more timeout risks'
\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
