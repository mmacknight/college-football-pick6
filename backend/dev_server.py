"""
Development server for Pick6 backend APIs
Simulates API Gateway behavior for local development
Now with optional WebSocket support for real-time updates
"""

import sys
import os
import json
import time
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

# WebSocket support (optional)
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
    import jwt
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("💡 WebSocket libraries not installed. Install with: pip install flask-socketio")

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'lambdas', 'shared'))

# Import lambda handlers with explicit paths
import importlib.util

def load_lambda_handler(module_path, handler_name=None):
    try:
        spec = importlib.util.spec_from_file_location("lambda_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.lambda_handler
    except Exception as e:
        print(f"ERROR loading handler from {module_path}: {e}")
        return None

# Load all handlers - temporarily disable new ones to debug
login_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'auth', 'login.py'), 'login')
signup_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'auth', 'signup.py'), 'signup')
create_league_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'create.py'), 'create')
join_league_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'join.py'), 'join')
list_leagues_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'list.py'), 'list_leagues')
get_standings_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'standings', 'get.py'), 'get')
list_schools_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'schools', 'list.py'), 'list_schools')
select_team_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'teams', 'team_select.py'), 'select_team')

# Re-enable new draft handlers
my_teams_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'my_teams.py'))
draft_board_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'draft_board.py'))
draft_status_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'draft_status.py'))

# New games week handler
games_week_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'games_week.py'))
start_draft_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'start_draft.py'))

# League admin handlers
get_settings_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'get_settings.py'))
update_settings_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'update_settings.py'))
remove_player_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'remove_player.py'))
reset_draft_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'reset_draft.py'))
update_player_teams_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'update_player_teams.py'))
update_team_name_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'update_team_name.py'))
lobby_handler = load_lambda_handler(os.path.join(os.path.dirname(__file__), 'lambdas', 'leagues', 'lobby.py'))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Simple CORS setup - allow everything for development
CORS(app)

# Initialize WebSocket support if available
socketio = None
connected_users = {}
user_rooms = {}
JWT_SECRET = "your-development-secret-key"  # Must match auth lambda

if WEBSOCKET_AVAILABLE:
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        async_mode='threading',
        logger=False,
        engineio_logger=False
    )
    print("✅ WebSocket support enabled")

# Add request logging  
@app.before_request
def log_request():
    print(f"📥 {request.method} {request.path} from {request.remote_addr}")
    if request.data:
        print(f"📋 Body: {request.data.decode('utf-8')[:200]}")
    print(f"🎭 Headers: {dict(request.headers)}")

def lambda_to_flask_response(lambda_response):
    """Convert Lambda response to Flask response"""
    status_code = lambda_response.get('statusCode', 200)
    body = lambda_response.get('body', '{}')
    
    if isinstance(body, dict):
        return jsonify(body), status_code
    else:
        # Parse JSON string if needed
        try:
            parsed_body = json.loads(body)
            return jsonify(parsed_body), status_code
        except:
            return body, status_code

def flask_to_lambda_event(method='GET', path='/', body=None, query_params=None, path_params=None):
    """Convert Flask request to Lambda event format"""
    event = {
        'httpMethod': method,
        'path': path,
        'headers': dict(request.headers),
        'queryStringParameters': query_params or dict(request.args),
        'pathParameters': path_params or {},
        'body': body
    }
    
    if body is None and request.data:
        event['body'] = request.data.decode('utf-8')
    
    return event

@app.route('/auth/login', methods=['POST'])
def auth_login():
    try:
        if login_handler is None:
            return jsonify({'error': 'Login handler not loaded'}), 500
        
        event = flask_to_lambda_event('POST', '/auth/login', request.get_json())
        if event['body'] and isinstance(event['body'], dict):
            event['body'] = json.dumps(event['body'])
        
        print(f"🔐 Login request: {event.get('body', 'No body')}")
        response = login_handler(event, {})
        print(f"🔐 Login response: {response}")
        return lambda_to_flask_response(response)
    except Exception as e:
        print(f"❌ Login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/auth/signup', methods=['POST'])
def auth_signup():
    event = flask_to_lambda_event('POST', '/auth/signup', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = signup_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues', methods=['GET'])
def list_leagues():
    event = flask_to_lambda_event('GET', '/leagues')
    response = list_leagues_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues', methods=['POST'])
def create_league():
    event = flask_to_lambda_event('POST', '/leagues', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = create_league_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/join', methods=['POST'])
def join_league():
    event = flask_to_lambda_event('POST', '/leagues/join', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = join_league_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/my-teams', methods=['GET'])
def get_my_teams(league_id):
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/my-teams', 
                                  path_params={'id': league_id})
    response = my_teams_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/draft-board', methods=['GET'])
def get_draft_board(league_id):
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/draft-board', 
                                  path_params={'id': league_id})
    response = draft_board_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/draft-status', methods=['GET'])
def get_draft_status(league_id):
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/draft-status', 
                                  path_params={'id': league_id})
    response = draft_status_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/standings', methods=['GET'])
def get_standings(league_id):
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/standings', 
                                  path_params={'league_id': league_id})
    response = get_standings_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/games/week/<week>', methods=['GET'])
def get_league_games_week(league_id, week):
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/games/week/{week}', 
                                  path_params={'league_id': league_id, 'week': week})
    response = games_week_handler(event, {})
    return lambda_to_flask_response(response)

# League Admin Routes
@app.route('/leagues/<league_id>/settings', methods=['GET'])
def get_league_settings(league_id):
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/settings', 
                                  path_params={'id': league_id})
    response = get_settings_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/settings', methods=['PUT'])
def update_league_settings(league_id):
    event = flask_to_lambda_event('PUT', f'/leagues/{league_id}/settings', 
                                  request.get_json(), 
                                  path_params={'id': league_id})
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    response = update_settings_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/players/<user_id>', methods=['DELETE'])
def remove_player_from_league(league_id, user_id):
    event = flask_to_lambda_event('DELETE', f'/leagues/{league_id}/players/{user_id}', 
                                  path_params={'id': league_id, 'userId': user_id})
    response = remove_player_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/reset-draft', methods=['POST'])
def reset_league_draft(league_id):
    event = flask_to_lambda_event('POST', f'/leagues/{league_id}/reset-draft', 
                                  path_params={'id': league_id})
    response = reset_draft_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/players/<user_id>/teams', methods=['PUT'])
def update_player_teams(league_id, user_id):
    event = flask_to_lambda_event('PUT', f'/leagues/{league_id}/players/{user_id}/teams', 
                                  request.get_json(), 
                                  path_params={'id': league_id, 'userId': user_id})
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    response = update_player_teams_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/team-name', methods=['PUT'])
def update_team_name(league_id):
    event = flask_to_lambda_event('PUT', f'/leagues/{league_id}/team-name', 
                                  request.get_json(), 
                                  path_params={'id': league_id})
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    response = update_team_name_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/start-draft', methods=['POST'])
def start_league_draft(league_id):
    event = flask_to_lambda_event('POST', f'/leagues/{league_id}/start-draft', 
                                  path_params={'id': league_id})
    response = start_draft_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/lobby', methods=['GET'])
def get_league_lobby(league_id):
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/lobby', 
                                  path_params={'id': league_id})
    response = lobby_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/schools', methods=['GET'])
def list_schools():
    event = flask_to_lambda_event('GET', '/schools')
    response = list_schools_handler(event, {})
    return lambda_to_flask_response(response)

@app.route('/teams/select', methods=['POST'])
def select_team():
    event = flask_to_lambda_event('POST', '/teams/select', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = select_team_handler(event, {})
    
    # After team selection, notify all users in the league about the draft update
    print(f"🔍 Checking WebSocket broadcast - socketio available: {socketio is not None}")
    if socketio:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            print(f"🔍 Parsed body: {body}")
            # Handle both 'league_id' and 'leagueId' field names
            league_id = body.get('league_id') or body.get('leagueId')
            print(f"🔍 League ID found: {league_id}")
            if league_id:
                print(f"🚀 About to broadcast draft update for league {league_id}")
                broadcast_to_league(league_id, 'draft_update', {
                    'type': 'team_selected',
                    'league_id': league_id,
                    'timestamp': time.time()
                })
                print(f"✅ Broadcast completed for league {league_id}")
            else:
                print("❌ No league_id found in request body")
        except Exception as e:
            print(f"❌ Error broadcasting draft update: {e}")
    else:
        print("❌ SocketIO not available")
    
    return lambda_to_flask_response(response)

@app.route('/health', methods=['GET'])
def health_check():
    print("🏥 Health check endpoint hit!")
    return {'status': 'healthy', 'message': 'Pick6 API Server Running'}, 200

@app.route('/test', methods=['GET'])
def test_endpoint():
    print("🧪 Test endpoint hit!")
    return {'test': 'working'}, 200

# ================== WEBSOCKET EVENT HANDLERS ==================

def verify_jwt_token(token):
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError:
        return None

def broadcast_to_league(league_id, message_type, data):
    """Broadcast message to all users in a league"""
    if not socketio:
        return
    room = f"league_{league_id}"
    print(f"📡 Broadcasting {message_type} to league {league_id}")
    socketio.emit(message_type, data, room=room)

def broadcast_standings_update(league_id, standings_data, recent_games=None):
    """Broadcast standings update to all league members"""
    if not socketio:
        return
    
    room = f"league_{league_id}"
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
    
    print(f"📊 Broadcasting standings update to league {league_id}")
    socketio.emit('standings_update', message, room=room)

if WEBSOCKET_AVAILABLE and socketio:
    
    @socketio.on('connect')
    def handle_connect(auth):
        """Handle client connection"""
        print(f"🔌 Client connecting: {request.sid}")
        
        # Get token from auth or query parameters
        token = None
        if auth and isinstance(auth, dict):
            token = auth.get('token')
        
        if not token:
            # Try to get from query parameters
            token = request.args.get('token')
        
        if not token:
            print(f"❌ No token provided for connection {request.sid}")
            disconnect()
            return False
        
        # Verify token
        user_info = verify_jwt_token(token)
        if not user_info:
            print(f"❌ Invalid token for connection {request.sid}")
            disconnect()
            return False
        
        # Store user info
        user_id = user_info.get('user_id') or user_info.get('id')
        connected_users[request.sid] = {
            'user_id': user_id,
            'username': user_info.get('username', 'Unknown'),
            'connected_at': time.time()
        }
        
        print(f"✅ User {user_info.get('username')} connected (sid: {request.sid})")
        emit('connected', {'status': 'success', 'message': 'Connected to Pick6 real-time updates'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        if request.sid in connected_users:
            user = connected_users[request.sid]
            print(f"🔌 User {user['username']} disconnected (sid: {request.sid})")
            
            # Remove from all rooms
            if request.sid in user_rooms:
                for room in user_rooms[request.sid]:
                    leave_room(room)
                del user_rooms[request.sid]
            
            del connected_users[request.sid]
        else:
            print(f"🔌 Unknown client disconnected (sid: {request.sid})")

    @socketio.on('join_league')
    def handle_join_league(data):
        """Join a league room for real-time updates"""
        if request.sid not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return
        
        league_id = data.get('league_id')
        if not league_id:
            emit('error', {'message': 'League ID required'})
            return
        
        room = f"league_{league_id}"
        join_room(room)
        
        # Track user rooms
        if request.sid not in user_rooms:
            user_rooms[request.sid] = set()
        user_rooms[request.sid].add(room)
        
        user = connected_users[request.sid]
        print(f"📋 User {user['username']} joined league {league_id} room")
        
        emit('joined_league', {'league_id': league_id, 'room': room})

    @socketio.on('leave_league')
    def handle_leave_league(data):
        """Leave a league room"""
        if request.sid not in connected_users:
            return
        
        league_id = data.get('league_id')
        if not league_id:
            return
        
        room = f"league_{league_id}"
        leave_room(room)
        
        # Remove from tracked rooms
        if request.sid in user_rooms:
            user_rooms[request.sid].discard(room)
        
        user = connected_users[request.sid]
        print(f"📋 User {user['username']} left league {league_id} room")
        
        emit('left_league', {'league_id': league_id})

    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection keepalive"""
        emit('pong')
    
    @socketio.on('subscribe_standings')
    def handle_subscribe_standings(data):
        """Handle standings subscription"""
        if request.sid not in connected_users:
            print("❌ Unknown user trying to subscribe to standings")
            return
        
        league_id = data.get('league_id')
        if not league_id:
            print("❌ No league_id provided for standings subscription")
            return
        
        user = connected_users[request.sid]
        print(f"📊 User {user['username']} subscribed to standings for league {league_id}")
        
        # Send confirmation
        emit('standings_subscription_confirmed', {'league_id': league_id})

def standings_updater_background():
    """Background thread to periodically send standings updates"""
    while True:
        try:
            # Only run if WebSocket is available and connected users exist
            if WEBSOCKET_AVAILABLE and socketio and connected_users:
                # Simulate calling the standings updater
                print("🔄 Running background standings updater...")
                
                # For local development, we'll simulate the standings updater
                # instead of importing the AWS Lambda version
                try:
                    # Simulate standings update locally
                    from lambdas.shared.database import get_db_session, League
                    
                    db = get_db_session()
                    active_leagues = db.query(League).filter(
                        League.status.in_(['active', 'drafting'])
                    ).all()
                    db.close()
                    
                    print(f"📊 Found {len(active_leagues)} active leagues")
                    
                    # For each active league, simulate broadcasting updates
                    for league in active_leagues:
                        if f"league_{league.id}" in [room for user_rooms_set in user_rooms.values() for room in user_rooms_set]:
                            print(f"📡 Would broadcast standings update to league {league.id}")
                            # We could trigger actual standings refresh here if needed
                    
                    print("📊 Local standings update simulation completed")
                    
                except Exception as e:
                    print(f"❌ Error in local standings updater: {e}")
            
            # Wait 3 minutes (180 seconds)
            time.sleep(180)
            
        except Exception as e:
            print(f"❌ Error in standings updater background thread: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == '__main__':
    import sys
    
    # Check if --gunicorn flag is passed
    use_gunicorn = '--gunicorn' in sys.argv
    
    if use_gunicorn:
        print("🚀 Starting Pick6 with Gunicorn (Production-grade)...")
        print("📊 Database: PostgreSQL at localhost:5432")
        print("🌐 API Server: http://localhost:3001")
        if WEBSOCKET_AVAILABLE:
            print("⚡ WebSocket: ws://localhost:3001 (Real-time updates)")
        else:
            print("🔄 Real-time Updates: Simple polling every 4 seconds")
        print("⚡ Multiple workers for better performance")
        print("Press Ctrl+C to stop")
        print()
        
        # Start with Gunicorn
        import os
        if socketio:
            # Use socketio-compatible command
            os.system("gunicorn -c gunicorn.conf.py --worker-class eventlet -w 1 dev_server:app")
        else:
            os.system("gunicorn -c gunicorn.conf.py dev_server:app")
    else:
        print("🚀 Starting Pick6 Development Server...")
        print("📊 Database: PostgreSQL at localhost:5432")
        print("🌐 API Server: http://localhost:3001")
        if WEBSOCKET_AVAILABLE:
            print("⚡ WebSocket: ws://localhost:3001 (Real-time updates)")
            print("🔄 Real-time Updates: WebSocket-based")
            print("📊 Standings Updates: Every 3 minutes")
            
            # Start background standings updater thread
            updater_thread = threading.Thread(target=standings_updater_background, daemon=True)
            updater_thread.start()
            print("🔄 Background standings updater started")
        else:
            print("🔄 Real-time Updates: Simple polling every 4 seconds")
            print("💡 Install WebSocket support: pip install flask-socketio")
        print("💡 For better performance with multiple browsers, use: python dev_server.py --gunicorn")
        print("Press Ctrl+C to stop")
        print()
        
        # Start server (with or without WebSocket)
        if socketio:
            socketio.run(app, host='0.0.0.0', port=3001, debug=True, use_reloader=False)
        else:
            app.run(host='0.0.0.0', port=3001, debug=False)
