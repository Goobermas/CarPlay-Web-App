import os
from flask import Flask, redirect, request, session, jsonify, render_template
import requests
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')  # Use environment variable or fallback to a default key

# Set up database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///spotify_sessions.db')  # Using SQLite as default
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Spotify API info from environment variables
CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/callback')  # Default fallback URL
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1/me/player/currently-playing'

# Database model for storing user session data (access_token, refresh_token)
class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), unique=True, nullable=False)
    access_token = db.Column(db.String(512), nullable=False)
    refresh_token = db.Column(db.String(512), nullable=False)

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()

# Serve CarPlay screen after login
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/carplay')
    else:
        auth_url = f"{SPOTIFY_AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=user-read-playback-state user-modify-playback-state"
        return redirect(auth_url)

# Render CarPlay screen UI
@app.route('/carplay')
def carplay():
    if 'user_id' in session:
        return render_template('index.html')
    return redirect('/')

# Spotify callback and token handling
@app.route('/callback')
def callback():
    code = request.args.get('code')
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(SPOTIFY_TOKEN_URL, data=data)
    token_info = response.json()

    # Extract user information from Spotify API response (optional)
    user_id = session.get('user_id', 'unknown_user')  # You can set this based on Spotify's profile info (e.g., user ID)

    # Store tokens in the database
    user_session = UserSession.query.filter_by(user_id=user_id).first()
    if user_session:
        user_session.access_token = token_info['access_token']
        user_session.refresh_token = token_info['refresh_token']
    else:
        new_session = UserSession(
            user_id=user_id,
            access_token=token_info['access_token'],
            refresh_token=token_info['refresh_token']
        )
        db.session.add(new_session)
    
    db.session.commit()

    # Store user_id in session for tracking user
    session['user_id'] = user_id
    session['access_token'] = token_info['access_token']
    return redirect('/carplay')

# Track info endpoint (JSON)
@app.route('/now-playing')
def now_playing():
    user_id = session.get('user_id')  # Retrieve the unique user_id from session

    # Retrieve the user's tokens from the database
    user_session = UserSession.query.filter_by(user_id=user_id).first()
    if user_session:
        access_token = user_session.access_token
    else:
        return jsonify({'error': 'User session not found'}), 404

    headers = {'Authorization': f"Bearer {access_token}"}
    response = requests.get(SPOTIFY_API_URL, headers=headers)

    if response.status_code == 200 and response.json():
        track_data = response.json()
        track_info = {
            'name': track_data['item']['name'],
            'artist': track_data['item']['artists'][0]['name'],
            'album_art': track_data['item']['album']['images'][0]['url']
        }
        return jsonify(track_info)
    
    return jsonify({'error': 'No track playing or token expired'}), 204

# Playback control endpoints
@app.route('/control/<action>')
def control(action):
    user_id = session.get('user_id')  # Retrieve the unique user_id from session
    user_session = UserSession.query.filter_by(user_id=user_id).first()

    if user_session:
        access_token = user_session.access_token
    else:
        return jsonify({'error': 'User session not found'}), 404

    headers = {'Authorization': f"Bearer {access_token}"}
    if action == 'play':
        requests.put(f'https://api.spotify.com/v1/me/player/play', headers=headers)
    elif action == 'pause':
        requests.put(f'https://api.spotify.com/v1/me/player/pause', headers=headers)
    elif action == 'next':
        requests.post(f'https://api.spotify.com/v1/me/player/next', headers=headers)
    elif action == 'previous':
        requests.post(f'https://api.spotify.com/v1/me/player/previous', headers=headers)
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
