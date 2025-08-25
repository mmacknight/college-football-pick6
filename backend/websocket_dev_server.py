"""
WebSocket-enabled development server for Pick6 backend
Clean implementation using Flask-SocketIO for real-time updates
"""

import sys
import os
import json
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import jwt

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'lambdas', 'shared'))

# Import lambda handlers
import importlib.util

def load_lambda_handler(module_path):
    """Load lambda handler from file path"""
    try:
        spec = importlib.util.spec_from_file_location("lambda_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.lambda_handler
    except Exception as e:
        print(f"ERROR loading handler from {module_path}: {e}")
        return None

# Load all handlers
base_dir = os.path.dirname(__file__)
handlers = {
    'login': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'auth', 'login.py')),
    'signup': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'auth', 'signup.py')),
    'create_league': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'leagues', 'create.py')),
    'join_league': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'leagues', 'join.py')),
    'list_leagues': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'leagues', 'list.py')),
    'my_teams': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'leagues', 'my_teams.py')),
    'draft_board': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'leagues', 'draft_board.py')),
    'draft_status': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'leagues', 'draft_status.py')),
    'get_standings': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'standings', 'get.py')),
    'list_schools': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'schools', 'list.py')),
    'select_team': load_lambda_handler(os.path.join(base_dir, 'lambdas', 'teams', 'team_select.py')),
}

# Create Flask app with SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
CORS(app, origins="*")

# Initialize SocketIO with threading (reliable for development)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    logger=True,
    engineio_logger=True  # Enable more logging to debug connection issues
)

# Store connected users and their rooms
connected_users = {}
user_rooms = {}

# JWT secret (should match your auth lambda)
JWT_SECRET = "your-jwt-secret-key"  # Replace with your actual secret

def verify_jwt_token(token):
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError:
        return None

def flask_to_lambda_event(method='GET', path='/', body=None, query_params=None, path_params=None):
    """Convert Flask request to Lambda event format"""
    return {
        'httpMethod': method,
        'path': path,
        'headers': dict(request.headers),
        'queryStringParameters': query_params or dict(request.args),
        'pathParameters': path_params or {},
        'body': body
    }

def lambda_to_flask_response(lambda_response):
    """Convert Lambda response to Flask response"""
    status_code = lambda_response.get('statusCode', 200)
    body = lambda_response.get('body', '{}')
    
    if isinstance(body, dict):
        return jsonify(body), status_code
    else:
        try:
            parsed_body = json.loads(body)
            return jsonify(parsed_body), status_code
        except:
            return body, status_code

# ================== HTTP API ROUTES ==================

@app.route('/auth/login', methods=['POST'])
def auth_login():
    if not handlers['login']:
        return jsonify({'error': 'Login handler not loaded'}), 500
    
    event = flask_to_lambda_event('POST', '/auth/login', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = handlers['login'](event, {})
    return lambda_to_flask_response(response)

@app.route('/auth/signup', methods=['POST'])
def auth_signup():
    if not handlers['signup']:
        return jsonify({'error': 'Signup handler not loaded'}), 500
        
    event = flask_to_lambda_event('POST', '/auth/signup', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = handlers['signup'](event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues', methods=['GET'])
def list_leagues():
    if not handlers['list_leagues']:
        return jsonify({'error': 'List leagues handler not loaded'}), 500
        
    event = flask_to_lambda_event('GET', '/leagues')
    response = handlers['list_leagues'](event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues', methods=['POST'])
def create_league():
    if not handlers['create_league']:
        return jsonify({'error': 'Create league handler not loaded'}), 500
        
    event = flask_to_lambda_event('POST', '/leagues', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = handlers['create_league'](event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/join', methods=['POST'])
def join_league():
    if not handlers['join_league']:
        return jsonify({'error': 'Join league handler not loaded'}), 500
        
    event = flask_to_lambda_event('POST', '/leagues/join', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = handlers['join_league'](event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/my-teams', methods=['GET'])
def get_my_teams(league_id):
    if not handlers['my_teams']:
        return jsonify({'error': 'My teams handler not loaded'}), 500
        
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/my-teams', 
                                  path_params={'id': league_id})
    response = handlers['my_teams'](event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/draft-board', methods=['GET'])
def get_draft_board(league_id):
    if not handlers['draft_board']:
        return jsonify({'error': 'Draft board handler not loaded'}), 500
        
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/draft-board', 
                                  path_params={'id': league_id})
    response = handlers['draft_board'](event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/draft-status', methods=['GET'])
def get_draft_status(league_id):
    if not handlers['draft_status']:
        return jsonify({'error': 'Draft status handler not loaded'}), 500
        
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/draft-status', 
                                  path_params={'id': league_id})
    response = handlers['draft_status'](event, {})
    return lambda_to_flask_response(response)

@app.route('/leagues/<league_id>/standings', methods=['GET'])
def get_standings(league_id):
    if not handlers['get_standings']:
        return jsonify({'error': 'Standings handler not loaded'}), 500
        
    event = flask_to_lambda_event('GET', f'/leagues/{league_id}/standings', 
                                  path_params={'league_id': league_id})
    response = handlers['get_standings'](event, {})
    return lambda_to_flask_response(response)

@app.route('/schools', methods=['GET'])
def list_schools():
    if not handlers['list_schools']:
        return jsonify({'error': 'Schools handler not loaded'}), 500
        
    event = flask_to_lambda_event('GET', '/schools')
    response = handlers['list_schools'](event, {})
    return lambda_to_flask_response(response)

@app.route('/teams/select', methods=['POST'])
def select_team():
    if not handlers['select_team']:
        return jsonify({'error': 'Select team handler not loaded'}), 500
        
    event = flask_to_lambda_event('POST', '/teams/select', request.get_json())
    if event['body'] and isinstance(event['body'], dict):
        event['body'] = json.dumps(event['body'])
    
    response = handlers['select_team'](event, {})
    
    # After team selection, notify all users in the league about the draft update
    try:
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        league_id = body.get('league_id')
        if league_id:
            broadcast_to_league(league_id, 'draft_update', {
                'type': 'team_selected',
                'league_id': league_id,
                'timestamp': time.time()
            })
    except Exception as e:
        print(f"Error broadcasting draft update: {e}")
    
    return lambda_to_flask_response(response)

@app.route('/health', methods=['GET'])
def health_check():
    return {'status': 'healthy', 'message': 'Pick6 WebSocket API Server Running'}, 200

# ================== WEBSOCKET EVENTS ==================

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

# ================== BROADCAST FUNCTIONS ==================

def broadcast_to_league(league_id, message_type, data):
    """Broadcast message to all users in a league"""
    room = f"league_{league_id}"
    print(f"📡 Broadcasting {message_type} to league {league_id}")
    socketio.emit(message_type, data, room=room)

def broadcast_to_user(user_id, message_type, data):
    """Broadcast message to a specific user"""
    # Find user's session ID
    for sid, user_info in connected_users.items():
        if user_info['user_id'] == user_id:
            print(f"📡 Broadcasting {message_type} to user {user_info['username']}")
            socketio.emit(message_type, data, room=sid)
            break

# ================== BACKGROUND TASKS (OPTIONAL) ==================

def start_background_tasks():
    """Start background tasks for periodic updates"""
    def score_updater():
        """Simulate periodic score updates"""
        while True:
            time.sleep(30)  # Update every 30 seconds
            # In real implementation, this would fetch real scores
            fake_scores = {
                'game_id': 'game_123',
                'home_team': 'Team A',
                'away_team': 'Team B',
                'home_score': 21,
                'away_score': 14,
                'quarter': 2,
                'time_remaining': '10:45'
            }
            
            # Broadcast to all connected users
            socketio.emit('score_update', fake_scores, broadcast=True)
    
    # Start background thread
    score_thread = threading.Thread(target=score_updater, daemon=True)
    score_thread.start()

if __name__ == '__main__':
    print("🚀 Starting Pick6 WebSocket Development Server...")
    print("📊 Database: PostgreSQL at localhost:5432")
    print("🌐 API Server: http://localhost:3001")
    print("⚡ WebSocket: ws://localhost:3001")
    print("🔄 Real-time Updates: WebSocket-based")
    print("Press Ctrl+C to stop")
    print()
    
    # Start background tasks (optional)
    # start_background_tasks()
    
    # Run with SocketIO
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=3001, 
        debug=True,
        use_reloader=False  # Disable reloader to prevent duplicate background tasks
    )
