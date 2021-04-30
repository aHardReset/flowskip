"""Useful functions for anaging room views"""

# Django
from django.apps import apps
from django.utils import timezone
from django.db.utils import OperationalError

# Python standar modules
import codecs
import random
import json
import string
from typing import List


def generate_unique_code(lenght: int = 6) -> str:
    """Generates a random string that pretends to be
    unique in terms of room.models.Rooms.code

    Args:
        lenght (int, optional): Length of the code. Defaults to 6.

    Returns:
        str: The generated code
    """
    Rooms = apps.get_model('room', 'Rooms')
    PaidUsers = apps.get_model('user', 'PaidUsers')
    Commerces = apps.get_model('user', 'Commerces')
    while True:
        code = ''.join(
            random.choices(string.ascii_uppercase, k=lenght),
        )
        lenght += 1
        anonymous = Rooms.objects.filter(code=code).exists()
        paid_users = PaidUsers.objects.filter(exclusive_code=code).exists()
        commerce = Commerces.objects.filter(exclusive_code=code).exists()
        if not anonymous or paid_users or commerce:
            break
    return code


def save_track_in_state(state: str, room: object, track: dict) -> None:
    """Takes an spotify api track object and saves it
    to our database

    Args:
        Table (Type): table class
        room (object): room which the track belongs
        track (dict): spotify track api
    """
    TracksState = apps.get_model("room", "TracksState")

    uri = track['uri']
    name = track['name']
    album_name = track['album']['name']
    images = track['album']['images']
    index = len(images) // 2
    album_image_url = images[index]['url']
    track_id = track['id']
    artists_str = ", ".join([
        artist['name'] for artist
        in track['artists']
    ])
    external_url = track['external_urls']['spotify']
    try:
        track = TracksState(
            room=room,
            track_id=track_id,
            uri=uri,
            external_url=external_url or None,
            album_name=album_name or None,
            album_image_url=album_image_url or None,
            artists_str=artists_str or None,
            name=name or None,
            state=state
        )
        track.save()
    except OperationalError:
        import translitcodec # noqa

        name = codecs.encode(name, 'translit/long')
        album_name = codecs.encode(album_name, 'translit/long')
        artists_str = codecs.encode(artists_str, 'translit/long')

        track = TracksState(
            room=room,
            track_id=track_id,
            uri=uri,
            external_url=external_url or None,
            album_name=album_name or None,
            album_image_url=album_image_url or None,
            artists_str=artists_str or None,
            name=name or None,
            state=state
        )
        track.save()


def register_track_in_state(state: str, room: object, data: dict) -> None:
    """Check if a track is valid to be added, A track
    is not valid if the last row is the same track

    Args:
        Table (Type): Table
        room (object): [description]
        data (dict): [description]
    """
    TracksState = apps.get_model("room", "TracksState")

    last_track = TracksState.objects.filter(state=state).last()
    if last_track:
        if last_track.track_id != data['item']['id']:
            save_track_in_state(state, room, data['item'])
    else:
        save_track_in_state(state, room, data['item'])


def clean_playback(room: object, data: dict) -> object:
    """Cleans the spotify playback object and
    saves the result to the database

    Args:
        room (object): Rooms instance
        data (dict): Spotify playback object

    Returns:
        object: Flowskip playback object
    """

    if data:
        del data['timestamp']
        del data['actions']
        del data['item']['available_markets']
        del data['item']['album']['available_markets']
        room.track_id = data['item']['id']
    else:
        data = {}
        room.track_id = None
    room.current_playing_track = data
    room.modified_at = timezone.now()
    room.save(update_fields=[
        'track_id',
        'current_playing_track',
        'modified_at',
    ])
    return room


def construct_participant(user: object) -> dict:
    """constructs either an anonymous user or a logged user

    Args:
        spotify_basic_data (object): SpotifyBasicData instance
        user (object): [description]

    Raises:
        ValueError: [description]

    Returns:
        dict: [description]
    """
    Parent = apps.get_model("spotify", "SpotifyBasicData")
    if not isinstance(user.spotify_basic_data, Parent):
        raise ValueError("I need spotify basic data")
    return {
        'is_authenticated': True if user.spotify_basic_data else False,
        'id': user.spotify_basic_data.id or user.session.session_key[-6:],
        'display_name': user.spotify_basic_data.display_name or None,
        'image_url': user.spotify_basic_data.image_url or None,
        'external-url': user.spotify_basic_data.external_url or None,
        'product': user.spotify_basic_data.product or None,
    }


def construct_participants(users: list[object]) -> list[dict]:
    """construct a list of participant given a queryset

    Args:
        users (list[object]): Queryset with users

    Raises:
        TypeError: Only works with users

    Returns:
        list[dict]: Cleanned list of user
    """
    Parent = apps.get_model("user", "Users")
    participants = []
    for user in users:
        if not isinstance(user, Parent):
            raise TypeError("I need a user")

        participants.append(
            construct_participant(user)
        )
    return participants


def calculate_dict_deltas(
    in_db: List[dict],
    in_req: List[dict],
    new: bool = True,
    gone: bool = True
) -> dict:
    """Takes two List[dict] and compare to do diffs

    Args:
        in_db (List[dict]): A list
        in_req (List[dict]): B list
        new (bool, optional): will return A - B ?. Defaults to True.
        gone (bool, optional): will return B - A ?. Defaults to True.

    Returns:
        dict: **new if new, **gone if gone
    """
    response = {}
    response['all'] = in_db

    in_db_set = set()
    for each in in_db:
        in_db_set.add(json.dumps(each, sort_keys=True))

    in_req_set = set()
    for each in in_req:
        in_req_set.add(json.dumps(each, sort_keys=True))

    if new:
        new_set = in_db_set - in_req_set
        new_set = [json.loads(p) for p in new_set]
        response['new'] = new_set
    if gone:
        gone_set = in_req_set - in_db_set
        gone_set = [json.loads(p) for p in gone_set]
        response['gone'] = gone_set
    return response
