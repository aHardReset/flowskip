from django.conf import settings

from os import environ
from os import remove
import random
import string
from datetime import datetime, timedelta
from time import mktime

import spotipy

CLIENT_ID = environ["SPOTIFY_FLOWSKIP_CLIENT_ID"]
CLIENT_SECRET = environ["SPOTIFY_FLOWSKIP_CLIENT_SECRET"]
REDIRECT_URI = "http://127.0.0.1:8000/spotify/spotify-oauth-redirect"
SCOPE = 'user-read-private user-read-playback-state user-modify-playback-state user-read-currently-playing user-library-read'

def auth_manager(state:str, username:str = '')->spotipy.SpotifyOAuth:
    return spotipy.SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        open_browser=False,
        show_dialog=False,
        state=state,
        username=username
    )

def delete_cached_token(username:str)->None:
    try:
        file = settings.BASE_DIR / ('.cache-' + username)
        remove(file)
    except Exception as e:
        print(f"WARN: deleting cached_token {e}")

def timestamp_to_datetime(timestamp: float)->datetime:
    return datetime.fromtimestamp(timestamp)

def get_tokens(tokens: dict)->dict:
    
    if isinstance(tokens['expires_at'], datetime):
        tokens['expires_at'] = mktime(tokens['expires_at'].timetuple())
    expires_at_timestamp = tokens['expires_at']
    expires_at_timestamp = int(expires_at_timestamp) - 2

    username = ''.join(random.choices(string.ascii_uppercase, k=4),)
    username += str(expires_at_timestamp)

    user_auth_manager = auth_manager(username, username=username)
    
    if user_auth_manager.is_token_expired({'expires_at': expires_at_timestamp}):
        user_auth_manager.refresh_access_token(tokens['refresh_token'])
        tokens = user_auth_manager.get_cached_token()
        delete_cached_token(username)
    tokens['expires_at'] = datetime.utcfromtimestamp(tokens['expires_at'])
    return tokens

def get_current_user(tokens: dict)-> tuple:
    
    new_tokens = get_tokens(tokens)
    sp = spotipy.Spotify(auth=new_tokens['access_token'])
    data = sp.current_user()
    if new_tokens == tokens:
        new_tokens = None
    return (data, new_tokens)

def get_current_playback(tokens: dict) -> tuple:
    new_tokens = get_tokens(tokens)
    sp = spotipy.Spotify(auth=new_tokens['access_token'])
    data = sp.current_playback()
    if not data:
        data = {}
    if new_tokens == tokens:
        new_tokens = None
    return (data, new_tokens)