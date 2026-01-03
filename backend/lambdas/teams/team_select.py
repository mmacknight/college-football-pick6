import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment, School, User, LeagueDraft
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event
from sqlalchemy import and_, text

@require_auth
def lambda_handler(event, context):
    """Select/draft a team for a user in a league"""
    try:
        # Parse request body
        if not event.get('body'):
            return validation_error_response({'body': 'Request body is required'})
        
        body = json.loads(event['body'])
        league_id = body.get('leagueId')
        school_id = body.get('schoolId')
        user_id = get_user_id_from_event(event)
        
        # Validate input
        errors = {}
        if not league_id:
            errors['leagueId'] = 'League ID is required'
        if not school_id:
            errors['schoolId'] = 'School ID is required'
        
        if errors:
            return validation_error_response(errors)
        
        db = get_db_session()
        try:
            # Verify league exists
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            # Verify school exists
            school = db.query(School).filter(School.id == school_id).first()
            if not school:
                return not_found_response('School')
            
            # Check if school is already taken in this league
            existing_pick = db.query(LeagueTeamSchoolAssignment).filter(
                and_(LeagueTeamSchoolAssignment.league_id == league_id, 
                     LeagueTeamSchoolAssignment.school_id == school_id)
            ).first()
            
            if existing_pick:
                return error_response('This team has already been selected by another player', 409)
            
            # Check league status - only allow picks in drafting leagues
            if league.status != 'drafting':
                return error_response('Draft is not currently active for this league', 400)
            
            # Check if user has a team in this league
            league_team = db.query(LeagueTeam).filter(
                and_(LeagueTeam.league_id == league_id, LeagueTeam.user_id == user_id)
            ).first()
            
            if not league_team:
                return error_response('You are not a member of this league', 403)
            
            # Check if user has reached max teams for this league
            user_school_count = db.query(LeagueTeamSchoolAssignment).filter(
                and_(LeagueTeamSchoolAssignment.league_id == league_id, 
                     LeagueTeamSchoolAssignment.user_id == user_id)
            ).count()
            
            if user_school_count >= league.max_teams_per_user:
                return error_response(f'You have reached the maximum of {league.max_teams_per_user} teams for this league', 400)
            
            # Check if it's this user's turn - REQUIRED for drafting leagues
            # Get draft state
            draft = db.query(LeagueDraft).filter(LeagueDraft.league_id == league_id).first()
            if not draft:
                return error_response('Draft has not been properly initialized', 400)
            
            if str(draft.current_user_id) != str(user_id):
                return error_response('It is not your turn to pick', 403)
            
            # Determine draft round and overall pick
            current_round = user_school_count + 1
            total_picks = db.query(LeagueTeamSchoolAssignment).filter(
                LeagueTeamSchoolAssignment.league_id == league_id
            ).count()
            draft_pick_overall = total_picks + 1
            
            # Create the school assignment
            school_assignment = LeagueTeamSchoolAssignment(
                league_id=league_id,
                user_id=user_id,
                school_id=school_id,
                draft_round=current_round,
                draft_pick_overall=draft_pick_overall
            )
            
            # BEFORE adding the pick, check if this will be the final pick that completes the draft
            league_teams = db.query(LeagueTeam).filter(LeagueTeam.league_id == league_id).all()
            total_players = len(league_teams)
            total_picks_needed = total_players * league.max_teams_per_user
            
            # Count all existing committed picks in the league
            total_existing_picks = db.query(LeagueTeamSchoolAssignment).filter(
                LeagueTeamSchoolAssignment.league_id == league_id
            ).count()
            
            is_final_pick = (total_existing_picks + 1) == total_picks_needed
            
            if is_final_pick:
                print(f"🚨🚨🚨 THIS IS THE FINAL PICK! 🚨🚨🚨")
                print(f"🎯 Pick #{total_existing_picks + 1} of {total_picks_needed} total needed")
                print(f"🏆 League {league_id} will be set to ACTIVE after this pick!")
                print(f"👤 Final pick made by user: {user_id}")
                print(f"🏫 Final school selected: {school_id}")
            
            # Now add the pick to the transaction
            db.add(school_assignment)
            
            # If this was the final pick, activate the league in the same transaction
            if is_final_pick:
                print(f"✅ Setting league status to 'active'")
                league.status = 'active'
                
                # Update draft completion if draft exists
                draft = db.query(LeagueDraft).filter(LeagueDraft.league_id == league_id).first()
                if draft:
                    draft.completed_at = db.execute(text("SELECT NOW()")).scalar()
                    draft.current_user_id = None
                    draft.current_league_id = None
                    print(f"✅ Draft marked as completed")
                
                print(f"✅ League {league_id} status updated to 'active'")
            
            # Update draft state after successful pick (league is in drafting mode)
            elif league.status == 'drafting':
                draft = db.query(LeagueDraft).filter(LeagueDraft.league_id == league_id).first()
                if draft:
                    # Advance to next pick
                    draft.current_pick_overall += 1
                    
                    # Find next player who hasn't completed their draft
                    league_teams_ordered = db.query(LeagueTeam).filter(
                        LeagueTeam.league_id == league_id
                    ).order_by(LeagueTeam.draft_position).all()
                    
                    if league_teams_ordered:
                        total_users = len(league_teams_ordered)
                        current_round = ((draft.current_pick_overall - 1) // total_users) + 1
                        pick_in_round = (draft.current_pick_overall - 1) % total_users
                        
                        # Snake draft: reverse order on even rounds
                        if current_round % 2 == 0:
                            pick_in_round = total_users - 1 - pick_in_round
                        
                        # Find the next player who hasn't completed their draft
                        attempts = 0
                        while attempts < total_users:
                            candidate_team = league_teams_ordered[pick_in_round]
                            candidate_pick_count = db.query(LeagueTeamSchoolAssignment).filter(
                                and_(LeagueTeamSchoolAssignment.league_id == league_id,
                                     LeagueTeamSchoolAssignment.user_id == candidate_team.user_id)
                            ).count()
                            
                            # If this player hasn't finished their draft, they're next
                            if candidate_pick_count < league.max_teams_per_user:
                                draft.current_user_id = candidate_team.user_id
                                draft.current_league_id = league_id
                                break
                            
                            # Move to next position in snake draft order
                            draft.current_pick_overall += 1
                            current_round = ((draft.current_pick_overall - 1) // total_users) + 1
                            pick_in_round = (draft.current_pick_overall - 1) % total_users
                            
                            if current_round % 2 == 0:
                                pick_in_round = total_users - 1 - pick_in_round
                            
                            attempts += 1
                        
                        # If we couldn't find anyone, draft is complete
                        if attempts >= total_users:
                            print(f"🎉 Draft complete! No more players need to pick.")
                            league.status = 'active'
                            draft.completed_at = db.execute(text("SELECT NOW()")).scalar()
                            draft.current_user_id = None
                            draft.current_league_id = None
            
            db.commit()
            db.refresh(school_assignment)
            
            # Send WebSocket notification to all league members
            try:
                # Import here to avoid circular imports
                import os
                from datetime import datetime
                
                # Environment-aware broadcasting: auto-detect local vs cloud
                is_local_dev = not os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
                
                if is_local_dev:
                    # Local development - broadcasting handled by dev_server.py
                    print(f"📍 Local dev mode - draft update will be broadcast by dev server for league {league_id}")
                    # In local development, the dev_server.py intercepts /teams/select and handles WebSocket broadcasting
                    # No additional action needed here - skip the entire AWS WebSocket logic
                    pass
                else:
                    # Cloud environment - use AWS WebSocket infrastructure
                    import boto3
                    
                    # Get API Gateway Management API
                    stage = os.environ.get('STAGE', 'dev')
                    api_id = os.environ.get('API_GATEWAY_WEBSOCKET_ID')
                    region = os.environ.get('AWS_REGION', 'us-east-1')
                    
                    if api_id:
                        endpoint = f"https://{api_id}.execute-api.{region}.amazonaws.com/{stage}"
                        api_gateway = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint)
                        
                        # Get connections for this league
                        dynamodb = boto3.resource('dynamodb')
                        table_name = os.environ.get('CONNECTIONS_TABLE', f'{stage}-websocket-connections')
                        connections_table = dynamodb.Table(table_name)
                        
                        response = connections_table.scan(
                            FilterExpression='league_id = :league_id',
                            ExpressionAttributeValues={':league_id': str(league_id)}
                        )
                        
                        # Determine message type based on league status
                        update_type = 'draft_complete' if league.status == 'active' else 'team_selected'
                        
                        # Broadcast to all connections
                        message = {
                            'type': 'draft_update',
                            'update_type': update_type,
                            'league_id': str(league_id),
                            'data': {
                                'userId': str(user_id),
                                'school': {
                                    'id': school.id,
                                    'name': school.name,
                                    'mascot': school.mascot,
                                    'conference': school.conference,
                                    'primaryColor': school.primary_color
                                },
                                'draftRound': current_round,
                                'draftPickOverall': draft_pick_overall,
                                'leagueStatus': league.status,
                                'draftComplete': league.status == 'active'
                            },
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        
                        for item in response['Items']:
                            connection_id = item['connection_id']
                            try:
                                api_gateway.post_to_connection(
                                    ConnectionId=connection_id,
                                    Data=json.dumps(message)
                                )
                            except api_gateway.exceptions.GoneException:
                                # Connection is stale, remove it
                                connections_table.delete_item(Key={'connection_id': connection_id})
                            except Exception as e:
                                print(f"Error sending to connection {connection_id}: {str(e)}")
                            
            except Exception as e:
                print(f"Error sending WebSocket notification: {str(e)}")
                # Don't fail the request if WebSocket notification fails
            
            return success_response({
                'id': f"{league_id}_{user_id}_{school_id}",  # Composite identifier
                'leagueId': str(league_id),
                'userId': str(user_id),
                'school': {
                    'id': school.id,
                    'name': school.name,
                    'mascot': school.mascot,
                    'conference': school.conference,
                    'primaryColor': school.primary_color,
                    'secondaryColor': school.secondary_color,
                    'abbreviation': school.abbreviation
                },
                'draftRound': current_round,
                'draftPickOverall': draft_pick_overall,
                'pickedAt': school_assignment.drafted_at.isoformat()
            }, 201)
            
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Team selection error: {str(e)}")
        print(f"Team selection error type: {type(e)}")
        import traceback
        print(f"Team selection traceback: {traceback.format_exc()}")
        return error_response('Failed to select team', 500)
