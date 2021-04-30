from django.conf import settings
from django.utils import timezone
import os
from os import remove
import random
import string
from datetime import datetime

from spotify import snippets as spotify_snippets

import spotipy

CLIENT_ID = os.getenv("SPOTIFY_FLOWSKIP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_FLOWSKIP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
scopes = [
    'user-modify-playback-state',
    'user-read-playback-state',
    'user-read-private',
]
SCOPE = " ".join(scopes)


def auth_manager(state: str, username: str = '') -> spotipy.SpotifyOAuth:
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


def delete_cached_token(username: str) -> None:
    try:
        file = settings.BASE_DIR / ('.cache-' + username)
        remove(file)
    except Exception as e:
        print(f"WARN: deleting cached_token {e}")


def timestamp_to_datetime(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp)


def get_tokens(tokens: dict) -> dict:
    if not isinstance(tokens['expires_at'], datetime):
        tokens['expires_at'] = datetime.utcfromtimestamp(tokens['expires_at'])
        tokens['expires_at'] = timezone.make_aware(
            tokens['expires_at'],
            timezone.get_current_timezone()
        )

    username = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=4),)

    user_auth_manager = auth_manager(username, username=username)

    if (tokens['expires_at'] - timezone.now()).total_seconds() < 60:
        user_auth_manager.refresh_access_token(tokens['refresh_token'])
        tokens = user_auth_manager.get_cached_token()
        delete_cached_token(username)
        naive = datetime.utcfromtimestamp(tokens['expires_at'])
        tokens['expires_at'] = timezone.make_aware(naive, timezone.get_current_timezone())
    return tokens


def get_current_user(tokens: dict) -> tuple:

    new_tokens = get_tokens(tokens)
    sp = spotipy.Spotify(auth=new_tokens['access_token'])
    data = sp.current_user()
    if new_tokens == tokens:
        new_tokens = None
    return (data, new_tokens)


def api_manager(spotify_basic_data: object) -> spotipy.Spotify:
    db_tokens = spotify_snippets.get_db_tokens(spotify_basic_data)
    new_tokens = get_tokens(db_tokens)
    if db_tokens != new_tokens:
        spotify_snippets.update_db_tokens(spotify_basic_data, new_tokens)
    return spotipy.Spotify(auth=new_tokens['access_token'])
