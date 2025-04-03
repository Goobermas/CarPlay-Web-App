import os
from flask import Flask, redirect, request, session, jsonify, render_template
import requests

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

# Store user tokens in memory (Better: Use a database like Redis)
user_tokens = {}

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
        access_token = token_info['access_token']
        
        # Get user ID from Spotify
        headers = {'Authorization': f"Bearer {access_token}"}
        user_response = requests.get(SPOTIFY_USER_URL, headers=headers)
        if user_response.status_code == 200:
            user_data = user_response.json()
            user_id = user_data['id']
            
            # Store tokens per user
            user_tokens[user_id] = {
                'access_token': token_info['access_token'],
                'refresh_token': token_info.get('refresh_token')
            }
            session['user_id'] = user_id
            return redirect('/carplay')
        else:
            return jsonify({'error': 'Failed to fetch user info from Spotify'}), 400
    return jsonify({'error': 'Failed to authenticate with Spotify'}), 400

@app.route('/carplay')
def carplay():
    if 'user_id' in session:
        return render_template('index.html')
    return redirect('/')

@app.route('/now-playing')
def now_playing():
    user_id = session.get('user_id')
    if not user_id or user_id not in user_tokens:
        return jsonify({'error': 'User not authenticated'}), 401

    access_token = user_tokens[user_id]['access_token']
    headers = {'Authorization': f"Bearer {access_token}"}
    response = requests.get(SPOTIFY_API_URL, headers=headers)

    if response.status_code == 200:
        try:
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
        except ValueError:
            return jsonify({'error': 'Invalid JSON response from Spotify'}), 500
    elif response.status_code == 401:
        return jsonify({'error': 'Access token expired, please re-authenticate'}), 401
    return jsonify({'error': 'Failed to fetch currently playing track'}), 500

@app.route('/control/<action>')
def control(action):
    user_id = session.get('user_id')
    if not user_id or user_id not in user_tokens:
        return jsonify({'error': 'User not authenticated'}), 401

    access_token = user_tokens[user_id]['access_token']
    headers = {'Authorization': f"Bearer {access_token}"}
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
