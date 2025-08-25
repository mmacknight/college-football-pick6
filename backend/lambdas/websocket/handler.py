import json
import boto3
import os
from datetime import datetime, timedelta
import logging
from shared.database import get_db_connection, LeagueDraft, League, LeagueTeam, User
from shared.auth import verify_jwt_token
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB for connection management
dynamodb = boto3.resource('dynamodb')
connections_table = dynamodb.Table(os.environ.get('CONNECTIONS_TABLE', 'websocket-connections'))

# Initialize API Gateway Management API
def get_api_gateway_management_api():
    endpoint = f"https://{os.environ['API_GATEWAY_WEBSOCKET_ID']}.execute-api.{os.environ['AWS_REGION']}.amazonaws.com/{os.environ['STAGE']}"
    return boto3.client('apigatewaymanagementapi', endpoint_url=endpoint)

def lambda_handler(event, context):
    """Main WebSocket handler for connect/disconnect/message events"""
    route_key = event.get('requestContext', {}).get('routeKey')
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    try:
        if route_key == '$connect':
            return handle_connect(event, connection_id)
        elif route_key == '$disconnect':
            return handle_disconnect(connection_id)
        elif route_key == 'message':
            return handle_message(event, connection_id)
        elif route_key == 'ping':
            return handle_ping(connection_id)
        else:
            logger.warning(f"Unknown route: {route_key}")
            return {'statusCode': 400}
    except Exception as e:
        logger.error(f"Error handling WebSocket event: {str(e)}")
        return {'statusCode': 500}

def handle_connect(event, connection_id):
    """Handle new WebSocket connections"""
    try:
        # Extract JWT token from query parameters
        query_params = event.get('queryStringParameters') or {}
        token = query_params.get('token')
        
        if not token:
            logger.warning("No token provided for WebSocket connection")
            return {'statusCode': 401}
        
        # Verify JWT token
        payload = verify_jwt_token(token)
        if not payload:
            logger.warning("Invalid token for WebSocket connection")
            return {'statusCode': 401}
        
        user_id = payload.get('user_id')
        league_id = query_params.get('league_id')
        
        if not league_id:
            logger.warning("No league_id provided for WebSocket connection")
            return {'statusCode': 400}
        
        # Verify user is member of the league
        engine = get_db_connection()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            league_team = session.query(LeagueTeam).filter_by(
                league_id=league_id,
                user_id=user_id
            ).first()
            
            if not league_team:
                logger.warning(f"User {user_id} not member of league {league_id}")
                return {'statusCode': 403}
        finally:
            session.close()
        
        # Store connection info
        connections_table.put_item(
            Item={
                'connection_id': connection_id,
                'user_id': user_id,
                'league_id': league_id,
                'connected_at': datetime.utcnow().isoformat(),
                'last_ping': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow() + timedelta(hours=2)).timestamp())
            }
        )
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id} in league {league_id}")
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Error in handle_connect: {str(e)}")
        return {'statusCode': 500}

def handle_disconnect(connection_id):
    """Handle WebSocket disconnections"""
    try:
        connections_table.delete_item(Key={'connection_id': connection_id})
        logger.info(f"WebSocket disconnected: {connection_id}")
        return {'statusCode': 200}
    except Exception as e:
        logger.error(f"Error in handle_disconnect: {str(e)}")
        return {'statusCode': 500}

def handle_message(event, connection_id):
    """Handle incoming WebSocket messages"""
    try:
        body = json.loads(event.get('body', '{}'))
        message_type = body.get('type')
        
        if message_type == 'subscribe_draft':
            return handle_subscribe_draft(connection_id, body)
        elif message_type == 'subscribe_standings':
            return handle_subscribe_standings(connection_id, body)
        elif message_type == 'heartbeat':
            return handle_heartbeat(connection_id)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return {'statusCode': 400}
            
    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}")
        return {'statusCode': 500}

def handle_ping(connection_id):
    """Handle ping requests for keepalive"""
    try:
        # Update last ping time
        connections_table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='SET last_ping = :timestamp',
            ExpressionAttributeValues={':timestamp': datetime.utcnow().isoformat()}
        )
        
        # Send pong response
        api_gateway = get_api_gateway_management_api()
        api_gateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'type': 'pong', 'timestamp': datetime.utcnow().isoformat()})
        )
        
        return {'statusCode': 200}
    except Exception as e:
        logger.error(f"Error in handle_ping: {str(e)}")
        return {'statusCode': 500}

def handle_subscribe_draft(connection_id, body):
    """Handle draft subscription requests"""
    try:
        league_id = body.get('league_id')
        if not league_id:
            return {'statusCode': 400}
        
        # Update connection with draft subscription
        connections_table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='SET subscribed_to_draft = :league_id',
            ExpressionAttributeValues={':league_id': league_id}
        )
        
        # Send confirmation
        api_gateway = get_api_gateway_management_api()
        api_gateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                'type': 'subscription_confirmed',
                'league_id': league_id
            })
        )
        
        return {'statusCode': 200}
    except Exception as e:
        logger.error(f"Error in handle_subscribe_draft: {str(e)}")
        return {'statusCode': 500}

def handle_subscribe_standings(connection_id, body):
    """Handle standings subscription requests"""
    try:
        league_id = body.get('league_id')
        if not league_id:
            return {'statusCode': 400}
        
        # Update connection with standings subscription
        connections_table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='SET subscribed_to_standings = :league_id',
            ExpressionAttributeValues={':league_id': league_id}
        )
        
        # Send confirmation
        api_gateway = get_api_gateway_management_api()
        api_gateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                'type': 'standings_subscription_confirmed',
                'league_id': league_id
            })
        )
        
        return {'statusCode': 200}
    except Exception as e:
        logger.error(f"Error in handle_subscribe_standings: {str(e)}")
        return {'statusCode': 500}

def handle_heartbeat(connection_id):
    """Handle heartbeat messages"""
    try:
        connections_table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='SET last_ping = :timestamp',
            ExpressionAttributeValues={':timestamp': datetime.utcnow().isoformat()}
        )
        return {'statusCode': 200}
    except Exception as e:
        logger.error(f"Error in handle_heartbeat: {str(e)}")
        return {'statusCode': 500}

def broadcast_to_league(league_id, message, exclude_connection_id=None):
    """Broadcast a message to all connections subscribed to a league"""
    try:
        # Get all connections for this league
        response = connections_table.scan(
            FilterExpression='league_id = :league_id',
            ExpressionAttributeValues={':league_id': league_id}
        )
        
        api_gateway = get_api_gateway_management_api()
        successful_sends = 0
        failed_sends = 0
        
        for item in response['Items']:
            connection_id = item['connection_id']
            
            # Skip excluded connection
            if exclude_connection_id and connection_id == exclude_connection_id:
                continue
            
            try:
                api_gateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message)
                )
                successful_sends += 1
            except api_gateway.exceptions.GoneException:
                # Connection is stale, remove it
                connections_table.delete_item(Key={'connection_id': connection_id})
                logger.info(f"Removed stale connection: {connection_id}")
                failed_sends += 1
            except Exception as e:
                logger.error(f"Error sending to connection {connection_id}: {str(e)}")
                failed_sends += 1
        
        logger.info(f"Broadcast to league {league_id}: {successful_sends} successful, {failed_sends} failed")
        return successful_sends
        
    except Exception as e:
        logger.error(f"Error in broadcast_to_league: {str(e)}")
        return 0

# Utility function to be called from other Lambdas
def notify_draft_update(league_id, update_type, data):
    """Notify all league members of a draft update"""
    message = {
        'type': 'draft_update',
        'update_type': update_type,
        'league_id': league_id,
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return broadcast_to_league(league_id, message)

# Utility function for standings updates
def notify_standings_update(league_id, standings_data, recent_games=None):
    """Notify all league members of a standings update"""
    message = {
        'type': 'standings_update',
        'league_id': str(league_id),
        'data': {
            'standings': standings_data,
            'recentGames': recent_games or [],
            'updateTime': datetime.utcnow().isoformat()
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return broadcast_to_league(league_id, message)

def notify_game_update(league_id, game_data):
    """Notify all league members of a game score update"""
    message = {
        'type': 'game_update',
        'league_id': str(league_id),
        'data': game_data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return broadcast_to_league(league_id, message)
