import os
from flask import Flask, redirect, request, session, jsonify, render_template
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_USER_URL = 'https://api.spotify.com/v1/me'

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
        refresh_token = token_info['refresh_token']

        headers = {'Authorization': f"Bearer {access_token}"}
        user_response = requests.get(SPOTIFY_USER_URL, headers=headers)
        if user_response.status_code == 200:
            user_data = user_response.json()
            user_id = user_data['id']

            # Insert or update the user in Supabase
            supabase.table("users").upsert({
                "id": user_id,
                "access_token": access_token,
                "refresh_token": refresh_token
            }).execute()

            session['user_id'] = user_id
            return redirect('/dashboard')
        else:
            return jsonify({'error': 'Failed to fetch user info'}), 400
    return jsonify({'error': 'Failed to authenticate with Spotify'}), 400

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    return f"Welcome, Spotify user {session['user_id']}!"

if __name__ == '__main__':
    app.run(debug=True)
