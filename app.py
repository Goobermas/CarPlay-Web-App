from flask import Flask, redirect, request, session, jsonify, render_template
import requests
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

# Spotify API info
CLIENT_ID = 'cd1e42e0d54146e08575481eaab4f3b8'
CLIENT_SECRET = '892b295926c74022a02cf8a291593b59'
REDIRECT_URI = 'http://localhost:5000/callback'
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1/me/player/currently-playing'

# Serve CarPlay screen after login
@app.route('/')
def home():
    if 'access_token' in session:
        return redirect('/carplay')
    else:
        auth_url = f"{SPOTIFY_AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=user-read-playback-state user-modify-playback-state"
        return redirect(auth_url)

# Render CarPlay screen UI
@app.route('/carplay')
def carplay():
    if 'access_token' in session:
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
    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']
    return redirect('/carplay')

# Track info endpoint (JSON)
@app.route('/now-playing')
def now_playing():
    headers = {'Authorization': f"Bearer {session.get('access_token')}"}
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

# Playback control endpoints
@app.route('/control/<action>')
def control(action):
    headers = {'Authorization': f"Bearer {session.get('access_token')}"}
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