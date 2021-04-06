import random
import json
import string
from django.apps import apps
from django.utils import timezone
from django.db.utils import OperationalError
import codecs

def generate_unique_code(lenght:int = 6) -> str:
    """Generates a random string that pretends to be the
    unique in terms of room.models.Rooms.code

    Args:
        lenght (int, optional): Length of the code. Defaults to 6.

    Returns:
        str: The generated code
    """
    Rooms = apps.get_model('room','Rooms')
    PaidUsers = apps.get_model('user', 'PaidUsers')
    Commerces = apps.get_model('user', 'Commerces')
    while True:
        code = ''.join(
            random.choices(string.ascii_uppercase, k=lenght),
        )
        lenght += 1
        anonymous = Rooms.objects.filter(code = code).exists()
        paid_users = PaidUsers.objects.filter(exclusive_code = code).exists()
        commerce = Commerces.objects.filter(exclusive_code = code).exists() 
        if not anonymous or paid_users or commerce:
            break
        
    return code

def save_track_in_db(Table: object, room: object, data: dict) -> None:
    uri = data['uri']
    name = data['name']
    album_name = data['album']['name']
    images = data['album']['images']
    index = len(images) // 2
    album_image_url = images[index]['url']
    artists_str = ", ".join([
        artist['name'] for artist 
        in data['artists']
    ])
    external_url = data['external_urls']['spotify']
    try:
        track = Table(
            room = room,
            track_id = room.track_id,
            uri = uri,
            external_url = external_url if external_url else None,
            album_name = album_name if album_name else None,
            album_image_url = album_image_url if album_image_url else None,
            artists_str = artists_str if artists_str else None,
            name = name if name else None,
        )
        track.save()
    except OperationalError as msg:
        import translitcodec # noqa

        name = codecs.encode(name, 'translit/long')
        album_name = codecs.encode(album_name, 'translit/long')
        artists_str = codecs.encode(artists_str, 'translit/long')

        track = Table(
            room = room,
            track_id = room.track_id,
            uri = uri,
            external_url = external_url if external_url else None,
            album_name = album_name if album_name else None,
            album_image_url = album_image_url if album_image_url else None,
            artists_str = artists_str if artists_str else None,
            name = name if name else None,
        )
        track.save()

def register_track(Table: object, room: object, data: dict) -> None:
    last_track = Table.objects.last()
    if last_track:
        if last_track.track_id != data['item']['id']:
            save_track_in_db(Table, room, data['item'])
    else:
        save_track_in_db(Table, room, data['item'])

def clean_playback(room: object, data: dict) -> object:
    
    if data:
        del data['timestamp']
        del data['context']
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

def construct_participant(spotify_basic_data: object, user: object)-> dict:
    Parent = apps.get_model("spotify", "SpotifyBasicData")
    if not isinstance(spotify_basic_data, Parent):
        raise ValueError("I need spotify basic data")
    
    return {
        'is_authenticated': True if spotify_basic_data else False,
        'id': spotify_basic_data.id if spotify_basic_data else user.session.session_key[-6:],
        'display_name': spotify_basic_data.display_name if spotify_basic_data else None,
        'image_url': spotify_basic_data.image_url if spotify_basic_data else None,
        'external-url' : spotify_basic_data.external_url if spotify_basic_data else None,
        'product': spotify_basic_data.product if spotify_basic_data else None,
    }

def construct_participants(users: list[object]) -> list[dict]:
    Parent = apps.get_model("user", "Users")
    participants = []
    for user in users:
        if not isinstance(user, Parent):
            raise TypeError("I need a user")

        spotify_basic_data = user.spotify_basic_data
        participants.append(
            construct_participant(spotify_basic_data, user)
        )

    return participants
    
def calculate_user_deltas(
    in_db: list[dict], 
    in_req: list[dict],
    new: bool = True,
    gone: bool = True
    ) -> dict:

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
    
def query_to_list_dict(query: list, Serializer: object) -> list[dict]:
    return [dict(Serializer(i).data) for i in query]