import json
import os
import sys
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import from shared layer
from shared.database import get_db_session, League, User, LeagueTeam, LeagueTeamSchoolAssignment, School, Game
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_, text

# DynamoDB for WebSocket connections
dynamodb = boto3.resource('dynamodb')
connections_table = dynamodb.Table(os.environ.get('CONNECTIONS_TABLE', 'websocket-connections'))

# API Gateway for WebSocket broadcasting
def get_api_gateway_management_api():
    """Get API Gateway Management API client for WebSocket"""
    if os.environ.get('IS_LOCAL') == 'true':
        # Local development - no WebSocket broadcasting needed
        return None
    
    endpoint = f"https://{os.environ['API_GATEWAY_WEBSOCKET_ID']}.execute-api.{os.environ['AWS_REGION']}.amazonaws.com/{os.environ['STAGE']}"
    return boto3.client('apigatewaymanagementapi', endpoint_url=endpoint)

def lambda_handler(event, context):
    """Scheduled function to check for game updates and broadcast standings changes"""
    print("🔄 Starting standings updater...")
    
    try:
        # Get database session
        db = get_db_session()
        
        try:
            # Get all active leagues (not completed)
            active_leagues = db.query(League).filter(
                League.status.in_(['active', 'drafting'])
            ).all()
            
            print(f"📊 Found {len(active_leagues)} active leagues to update")
            
            updates_sent = 0
            
            for league in active_leagues:
                print(f"🏈 Processing league: {league.name} (ID: {league.id})")
                
                # Calculate current standings for this league
                standings_data = calculate_league_standings(db, league)
                
                # Check for recent game updates (last 10 minutes)
                recent_games = get_recent_game_updates(db, league.season)
                
                if recent_games or True:  # Always send standings updates for now
                    # Broadcast standings update to all league members
                    success = broadcast_standings_update(league.id, standings_data, recent_games)
                    if success:
                        updates_sent += 1
                        print(f"✅ Sent standings update for league {league.id}")
                    else:
                        print(f"❌ Failed to send standings update for league {league.id}")
            
            print(f"🎯 Standings updater completed: {updates_sent} leagues updated")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Successfully updated {updates_sent} leagues',
                    'leaguesProcessed': len(active_leagues),
                    'updatesSent': updates_sent
                })
            }
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error in standings updater: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def calculate_league_standings(db, league: League) -> Dict[str, Any]:
    """Calculate current standings for a league"""
    
    # Get all league members
    league_members = db.query(LeagueTeam).filter(
        LeagueTeam.league_id == league.id
    ).all()
    
    members = []
    
    for league_team in league_members:
        user = league_team.user
        
        # Get user's drafted schools for this league
        school_assignments = db.query(LeagueTeamSchoolAssignment).filter(
            and_(
                LeagueTeamSchoolAssignment.league_id == league.id,
                LeagueTeamSchoolAssignment.user_id == user.id
            )
        ).all()
        
        # Calculate wins and losses for user's teams
        total_wins = 0
        total_losses = 0
        total_games = 0
        teams = []
        
        for assignment in school_assignments:
            school = assignment.school
            
            # Count wins for this school
            wins_query = db.query(Game).filter(
                and_(
                    Game.season == league.season,
                    Game.completed == True,
                    or_(
                        and_(Game.home_id == school.id, Game.home_points > Game.away_points),
                        and_(Game.away_id == school.id, Game.away_points > Game.home_points)
                    )
                )
            )
            school_wins = wins_query.count()
            total_wins += school_wins
            
            # Count total completed games for this school
            games_query = db.query(Game).filter(
                and_(
                    Game.season == league.season,
                    Game.completed == True,
                    or_(Game.home_id == school.id, Game.away_id == school.id)
                )
            )
            school_games = games_query.count()
            school_losses = school_games - school_wins
            total_losses += school_losses
            total_games += school_games
            
            teams.append({
                'id': school.id,
                'name': school.name,
                'mascot': school.mascot,
                'conference': school.conference,
                'primaryColor': school.primary_color,
                'wins': school_wins,
                'losses': school_losses
            })
        
        members.append({
            'id': str(user.id),
            'displayName': user.display_name,
            'teamName': league_team.team_name,
            'teams': teams,
            'wins': total_wins,
            'losses': total_losses,
            'gamesPlayed': total_games // len(school_assignments) if school_assignments else 0
        })
    
    # Sort by wins descending, then by display name
    members.sort(key=lambda x: (-x['wins'], x['displayName']))
    
    return {
        'id': str(league.id),
        'name': league.name,
        'season': league.season,
        'status': league.status,
        'createdBy': str(league.created_by),
        'members': members
    }

def get_recent_game_updates(db, season: int, minutes_ago: int = 10) -> List[Dict[str, Any]]:
    """Get games that have been updated in the last N minutes"""
    
    # For now, we'll simulate recent updates by getting recently completed games
    # In production, you'd track when games were last updated
    cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
    
    # Get recently completed games (this is a simplified approach)
    recent_games = db.query(Game).filter(
        and_(
            Game.season == season,
            Game.completed == True
        )
    ).order_by(Game.week.desc()).limit(20).all()
    
    game_updates = []
    for game in recent_games:
        home_school = db.query(School).filter(School.id == game.home_id).first()
        away_school = db.query(School).filter(School.id == game.away_id).first()
        
        game_updates.append({
            'id': game.id,
            'week': game.week,
            'homeTeam': {
                'id': home_school.id,
                'name': home_school.name,
                'mascot': home_school.mascot,
                'primaryColor': home_school.primary_color
            },
            'awayTeam': {
                'id': away_school.id,
                'name': away_school.name,
                'mascot': away_school.mascot,
                'primaryColor': away_school.primary_color
            },
            'score': {
                'home': game.home_points or 0,
                'away': game.away_points or 0
            },
            'completed': game.completed
        })
    
    return game_updates

def broadcast_standings_update(league_id: str, standings_data: Dict[str, Any], recent_games: List[Dict[str, Any]]) -> bool:
    """Broadcast standings update to all WebSocket connections for a league"""
    
    # Check if we're in local development
    if os.environ.get('IS_LOCAL') == 'true':
        print(f"📡 [LOCAL] Would broadcast standings update to league {league_id}")
        print(f"📊 Standings: {len(standings_data.get('members', []))} members")
        print(f"🏈 Recent games: {len(recent_games)} games")
        return True
    
    try:
        # Get all WebSocket connections for this league
        response = connections_table.scan(
            FilterExpression='league_id = :league_id',
            ExpressionAttributeValues={':league_id': str(league_id)}
        )
        
        if not response.get('Items'):
            print(f"📡 No WebSocket connections found for league {league_id}")
            return True
        
        api_gateway = get_api_gateway_management_api()
        if not api_gateway:
            print(f"📡 No API Gateway client available")
            return False
        
        # Create the message
        message = {
            'type': 'standings_update',
            'league_id': str(league_id),
            'data': {
                'standings': standings_data,
                'recentGames': recent_games,
                'updateTime': datetime.utcnow().isoformat()
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        successful_sends = 0
        failed_sends = 0
        
        # Send to all connections
        for item in response['Items']:
            connection_id = item['connection_id']
            
            try:
                api_gateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message)
                )
                successful_sends += 1
            except api_gateway.exceptions.GoneException:
                # Connection is stale, remove it
                connections_table.delete_item(Key={'connection_id': connection_id})
                failed_sends += 1
            except Exception as e:
                print(f"❌ Error sending to connection {connection_id}: {str(e)}")
                failed_sends += 1
        
        print(f"📡 Broadcast to league {league_id}: {successful_sends} successful, {failed_sends} failed")
        return successful_sends > 0
        
    except Exception as e:
        print(f"❌ Error broadcasting standings update: {str(e)}")
        return False

# For local testing
if __name__ == "__main__":
    # Set local environment
    os.environ['IS_LOCAL'] = 'true'
    
    # Test the function
    result = lambda_handler({}, {})
    print(f"Test result: {result}")
