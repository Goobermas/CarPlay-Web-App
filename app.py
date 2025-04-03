import os
import sqlite3
import requests
from flask import Flask, redirect, request, session, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/callback')
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1/me/player/currently-playing'
SPOTIFY_CONTROL_URL = 'https://api.spotify.com/v1/me/player'
SPOTIFY_USER_URL = 'https://api.spotify.com/v1/me'

def init_db():
    conn = sqlite3.connect('spotify_users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        access_token TEXT,
                        refresh_token TEXT
                      )''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect('spotify_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT access_token, refresh_token FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def save_user(user_id, access_token, refresh_token):
    conn = sqlite3.connect('spotify_users.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO users (id, access_token, refresh_token) 
                      VALUES (?, ?, ?)''', (user_id, access_token, refresh_token))
    conn.commit()
    conn.close()

@app.route('/')
def home():
    auth_url = f"{SPOTIFY_AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=user-read-playback-state user-modify-playback-state"
    return redirect(auth_url)

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
    
    if 'access_token' in token_info:
        headers = {'Authorization': f"Bearer {token_info['access_token']}"}
        user_response = requests.get(SPOTIFY_USER_URL, headers=headers)
        if user_response.status_code == 200:
            user_id = user_response.json()['id']
            save_user(user_id, token_info['access_token'], token_info['refresh_token'])
            session['user_id'] = user_id
            return redirect('/carplay')
    return jsonify({'error': 'Failed to authenticate with Spotify'}), 400

@app.route('/carplay')
def carplay():
    if 'user_id' in session:
        return render_template('index.html')
    return redirect('/')

@app.route('/now-playing')
def now_playing():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    user = get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found in database'}), 401
    
    headers = {'Authorization': f"Bearer {user[0]}"}
    response = requests.get(SPOTIFY_API_URL, headers=headers)

    if response.status_code == 200:
        track_data = response.json()
        if track_data and 'item' in track_data:
            track_info = {
                'name': track_data['item']['name'],
                'artist': track_data['item']['artists'][0]['name'],
                'album_art': track_data['item']['album']['images'][0]['url']
            }
            return jsonify(track_info)
        else:
            return jsonify({'error': 'No track currently playing'}), 204
    elif response.status_code == 401:
        return jsonify({'error': 'Access token expired, please re-authenticate'}), 401
    return jsonify({'error': 'Failed to fetch currently playing track'}), 500

@app.route('/control/<action>')
def control(action):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    user = get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found in database'}), 401
    
    headers = {'Authorization': f"Bearer {user[0]}"}
    actions = {
        'play': lambda: requests.put(f'{SPOTIFY_CONTROL_URL}/play', headers=headers),
        'pause': lambda: requests.put(f'{SPOTIFY_CONTROL_URL}/pause', headers=headers),
        'next': lambda: requests.post(f'{SPOTIFY_CONTROL_URL}/next', headers=headers),
        'previous': lambda: requests.post(f'{SPOTIFY_CONTROL_URL}/previous', headers=headers)
    }
    
    if action in actions:
        try:
            actions[action]()
            return '', 204
        except requests.RequestException:
            return jsonify({'error': 'Failed to execute action'}), 500
    return jsonify({'error': 'Invalid action'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
