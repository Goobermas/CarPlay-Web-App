import os
import requests
from flask import Flask, redirect, request, session, jsonify, render_template, render_template_string
from supabase import create_client, Client
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
import eventlet
import threading
import time

# Patch for async support
eventlet.monkey_patch()

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_USER_URL = 'https://api.spotify.com/v1/me'
SPOTIFY_API_URL = 'https://api.spotify.com/v1/me/player/currently-playing'

track_cache = {}

def background_now_playing():
    while True:
        with app.app_context():
            user_id = session.get('user_id')
            access_token = session.get('access_token')
            if not access_token:
                time.sleep(5)
                continue

            headers = {'Authorization': f"Bearer {access_token}"}
            response = requests.get(SPOTIFY_API_URL, headers=headers)

            if response.status_code == 200 and response.json():
                track_data = response.json()
                track_info = {
                    'name': track_data['item']['name'],
                    'artist': track_data['item']['artists'][0]['name'],
                    'album_art': track_data['item']['album']['images'][0]['url']
                }
                if track_info != track_cache.get(user_id):
                    track_cache[user_id] = track_info
                    socketio.emit('track_update', track_info)
        time.sleep(2)

@app.route('/')
def home():
    if 'access_token' in session:
        return redirect('/carplay')
    else:
        auth_url = f"{SPOTIFY_AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=user-read-playback-state user-modify-playback-state user-read-email user-read-private"
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
    token_response = requests.post(SPOTIFY_TOKEN_URL, data=data)
    token_info = token_response.json()

    if 'access_token' not in token_info:
        print("Spotify token response:", token_response.status_code, token_response.text)
        return jsonify({'error': 'Failed to authenticate with Spotify'}), 400

    access_token = token_info['access_token']
    refresh_token = token_info.get('refresh_token')
    headers = {'Authorization': f"Bearer {access_token}"}
    user_response = requests.get(SPOTIFY_USER_URL, headers=headers)

    if user_response.status_code != 200:
        print("Spotify /me response:", user_response.status_code, user_response.text)
        return jsonify({'error': 'Failed to fetch user info from Spotify'}), 400

    try:
        user_data = user_response.json()
        user_id = user_data.get('id')
        display_name = user_data.get('display_name') or 'No Name'
        email = user_data.get('email') or 'noemail@example.com'

        supabase.table("users").upsert({
            "id": user_id,
            "email": email,
            "display_name": display_name,
            "access_token": access_token,
            "refresh_token": refresh_token
        }).execute()

        session['user_id'] = user_id
        session['access_token'] = access_token
    except Exception as e:
        print("User data error:", str(e))
        return jsonify({'error': 'Spotify user data malformed'}), 400

    return redirect('/carplay')

@app.route('/carplay')
def carplay():
    if 'access_token' in session:
        return render_template('index.html')
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    user_id = session['user_id']
    user_data = supabase.table("users").select("display_name, email").eq("id", user_id).single().execute()
    display_name = user_data.data.get("display_name", "Unknown")
    email = user_data.data.get("email", "Unknown")
    return render_template_string('''
        <h1>You are logged in as Spotify user {{ user_id }}</h1>
        <p><strong>Display Name:</strong> {{ display_name }}</p>
        <p><strong>Email:</strong> {{ email }}</p>
        <a href="/logout"><button>Log Out</button></a>
    ''', user_id=user_id, display_name=display_name, email=email)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    background_thread = threading.Thread(target=background_now_playing)
    background_thread.daemon = True
    background_thread.start()
    socketio.run(app, host='0.0.0.0', port=5000)
