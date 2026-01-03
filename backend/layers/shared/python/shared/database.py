import os
from sqlalchemy import create_engine, Column, String, Integer, UUID, TIMESTAMP, ForeignKey, Boolean, Numeric, ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from uuid import uuid4
from datetime import datetime

# Database URL - switches between local and AWS
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://pick6admin:pick6password@localhost:5432/pick6db')

import ssl
# Clean URL and configure SSL separately for pg8000
clean_url = DATABASE_URL.replace('postgresql://', 'postgresql+pg8000://').split('?')[0]

# SSL configuration - only use SSL for production (non-localhost)
if 'localhost' in DATABASE_URL or '127.0.0.1' in DATABASE_URL:
    # Local development - no SSL
    engine = create_engine(clean_url)
else:
    # Production - use SSL
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False  # Neon uses different hostname in cert
    engine = create_engine(clean_url, connect_args={"ssl_context": ssl_context})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class School(Base):
    __tablename__ = "schools"
    
    id = Column(Integer, primary_key=True)  # CollegeFootballData team_id (e.g., 333)
    team_slug = Column(String(50), unique=True, nullable=False)  # normalized slug (e.g., "alabama")
    abbreviation = Column(String(10))  # team abbreviation (e.g., "ALA")
    name = Column(String(100), nullable=False)
    mascot = Column(String(100))
    conference = Column(String(50))
    primary_color = Column(String(7))
    secondary_color = Column(String(7))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationships
    home_games = relationship("Game", foreign_keys="Game.home_id", back_populates="home_school")
    away_games = relationship("Game", foreign_keys="Game.away_id", back_populates="away_school")
    school_assignments = relationship("LeagueTeamSchoolAssignment", back_populates="school")

class User(Base):
    __tablename__ = "users"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_leagues = relationship("League", back_populates="creator")
    league_teams = relationship("LeagueTeam", back_populates="user")

class League(Base):
    __tablename__ = "leagues"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    season = Column(Integer, nullable=False)
    join_code = Column(String(8), unique=True, nullable=False)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String(20), default="pre_draft")  # pre_draft, drafting, active, completed
    max_teams_per_user = Column(Integer, default=6)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", back_populates="created_leagues")
    league_teams = relationship("LeagueTeam", back_populates="league")

class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True)  # CollegeFootballData game ID
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    season_type = Column(String(20), default='regular')
    start_date = Column(TIMESTAMP)
    start_time_tbd = Column(Boolean, default=False)
    completed = Column(Boolean, default=False)
    neutral_site = Column(Boolean, default=False)
    conference_game = Column(Boolean, default=False)
    attendance = Column(Integer)
    venue_id = Column(Integer)
    venue = Column(String(200))
    home_id = Column(Integer, ForeignKey("schools.id"))
    home_team = Column(String(100))
    home_classification = Column(String(20))
    home_conference = Column(String(50))
    home_points = Column(Integer, default=0)
    home_line_scores = Column(ARRAY(Integer))
    home_postgame_win_probability = Column(Numeric(10,9))
    home_pregame_elo = Column(Integer)
    home_postgame_elo = Column(Integer)
    away_id = Column(Integer, ForeignKey("schools.id"))
    away_team = Column(String(100))
    away_classification = Column(String(20))
    away_conference = Column(String(50))
    away_points = Column(Integer, default=0)
    away_line_scores = Column(ARRAY(Integer))
    away_postgame_win_probability = Column(Numeric(10,9))
    away_pregame_elo = Column(Integer)
    away_postgame_elo = Column(Integer)
    excitement_index = Column(Numeric(10,7))
    highlights = Column(String)
    notes = Column(String)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    home_school = relationship("School", foreign_keys=[home_id])
    away_school = relationship("School", foreign_keys=[away_id])

class LeagueTeam(Base):
    """A user's team in a specific league - represents one user's participation in one league"""
    __tablename__ = "league_teams"
    
    league_id = Column(PG_UUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    team_name = Column(String(100))  # "Mike's Dominators" (optional custom name)
    draft_position = Column(Integer)  # 1, 2, 3, 4 (draft order within league)
    joined_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationships
    league = relationship("League", back_populates="league_teams")
    user = relationship("User", back_populates="league_teams")
    school_assignments = relationship("LeagueTeamSchoolAssignment", back_populates="league_team")

class LeagueTeamSchoolAssignment(Base):
    """Assignment of a school to a user's team in a league - shows which schools each user has drafted"""
    __tablename__ = "league_team_school_assignments"
    
    league_id = Column(PG_UUID(as_uuid=True), ForeignKey("leagues.id"), primary_key=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), primary_key=True)
    draft_round = Column(Integer)  # 1, 2, 3, 4
    draft_pick_overall = Column(Integer)  # 1-16 in 4-person league
    drafted_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Add composite foreign key constraint
    __table_args__ = (
        ForeignKeyConstraint(['league_id', 'user_id'], ['league_teams.league_id', 'league_teams.user_id']),
    )
    
    # Relationships
    league_team = relationship("LeagueTeam", back_populates="school_assignments")
    school = relationship("School", back_populates="school_assignments")

class LeagueDraft(Base):
    """Draft management for a league"""
    __tablename__ = "league_drafts"
    
    league_id = Column(PG_UUID(as_uuid=True), ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True)
    current_pick_overall = Column(Integer, default=1)
    current_league_id = Column(PG_UUID(as_uuid=True), ForeignKey("leagues.id"))
    current_user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    total_picks = Column(Integer)  # members * max_teams_per_user
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    
    # Add composite foreign key constraint for current picker
    __table_args__ = (
        ForeignKeyConstraint(['current_league_id', 'current_user_id'], ['league_teams.league_id', 'league_teams.user_id']),
    )
    
    # Relationships
    league = relationship("League", foreign_keys=[league_id])
    current_league = relationship("League", foreign_keys=[current_league_id])
    current_user = relationship("User", foreign_keys=[current_user_id])

# Database utility functions
def get_db():
    """Get database session - for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """Get database session - for direct use"""
    return SessionLocal()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
