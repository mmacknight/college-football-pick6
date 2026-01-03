-- Migration script to add ON UPDATE CASCADE to foreign key constraints
-- This allows school ID updates to automatically cascade to referencing tables

-- Drop existing foreign key constraints
ALTER TABLE games 
DROP CONSTRAINT IF EXISTS games_home_id_fkey,
DROP CONSTRAINT IF EXISTS games_away_id_fkey;

ALTER TABLE league_team_school_assignments 
DROP CONSTRAINT IF EXISTS league_team_school_assignments_school_id_fkey;

-- Re-add constraints with ON UPDATE CASCADE
ALTER TABLE games 
ADD CONSTRAINT games_home_id_fkey 
    FOREIGN KEY (home_id) REFERENCES schools(id) ON UPDATE CASCADE;

ALTER TABLE games 
ADD CONSTRAINT games_away_id_fkey 
    FOREIGN KEY (away_id) REFERENCES schools(id) ON UPDATE CASCADE;

ALTER TABLE league_team_school_assignments 
ADD CONSTRAINT league_team_school_assignments_school_id_fkey 
    FOREIGN KEY (school_id) REFERENCES schools(id) ON UPDATE CASCADE;

-- Verify the constraints were added correctly
SELECT 
    tc.table_name, 
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.update_rule,
    rc.delete_rule
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND ccu.table_name = 'schools'
ORDER BY tc.table_name, kcu.column_name;
