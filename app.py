import os
from flask import Flask, redirect, request, session, jsonify, render_template
import requests
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/callback')
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1/me/player/currently-playing'
SPOTIFY_CONTROL_URL = 'https://api.spotify.com/v1/me/player'

# Serve CarPlay screen after login
@app.route('/')
def home():
    if 'access_token' in session:
        return redirect('/carplay')
    else:
        auth_url = f"{SPOTIFY_AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=user-read-playback-state user-modify-playback-state"
        return redirect(auth_url)

@app.route('/carplay')
def carplay():
    if 'access_token' in session:
        return render_template('index.html')
    return redirect('/')

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
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        return redirect('/carplay')
    else:
        return jsonify({'error': 'Failed to authenticate with Spotify'}), 400

@app.route('/now-playing')
def now_playing():
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'User not authenticated'}), 401

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
    else:
        return jsonify({'error': 'No track playing or token expired'}), 204

@app.route('/control/<action>')
def control(action):
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'User not authenticated'}), 401

    headers = {'Authorization': f"Bearer {access_token}"}
    actions = {
        'play': requests.put(f'{SPOTIFY_CONTROL_URL}/play', headers=headers),
        'pause': requests.put(f'{SPOTIFY_CONTROL_URL}/pause', headers=headers),
        'next': requests.post(f'{SPOTIFY_CONTROL_URL}/next', headers=headers),
        'previous': requests.post(f'{SPOTIFY_CONTROL_URL}/previous', headers=headers)
    }
    
    if action in actions:
        return '', 204
    return jsonify({'error': 'Invalid action'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
