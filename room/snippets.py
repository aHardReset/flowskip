import random
import json
import string
from django.apps import apps
from django.utils import timezone

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
    
    uri = data['item']['uri']
    name = data['item']['name']
    external_url = data['item']['external_urls']
    
    album_name = data['item']['album']['name']
    images = data['item']['album']['images']
    index = len(images) // 2
    album_image_url = images[index]['url']
    
    artists_str = ", ".join([
        artist['name'] for artist 
        in data['item']['artists']
    ])

    track = Table(
        room = room,
        track_id = room.track_id,
        uri = uri,
        name = name,
        external_url = external_url,
        album_name = album_name,
        album_image_url = album_image_url,
        artists_str = artists_str,
    )
    track.save()

def register_track(Table: object, room: object, data: dict) -> None:
    last_track = Table.objects.last()
    if last_track:
        if last_track.track_id != data['item']['id']:
            save_track_in_db(Table, room, data)
    else:
        save_track_in_db(Table, room, data)

def clean_playing_track(room: object, data: dict) -> object:
    
    if data:
        del data['timestamp']
        del data['context']
        del data['actions']
        del data['item']['available_markets']
        del data['item']['href']
        del data['item']['album']['href']
        del data['item']['album']['available_markets']
        room.track_id = data['item']['id']
    else:
        data = {}
        room.track_id = None
        
    room.current_playing_track = json.dumps(data)
    room.modified_at = timezone.now()
    room.save(update_fields=[
        'track_id',
        'current_playing_track',
        'modified_at',
    ])
    
    return room

def construct_participant(spotify_basic_data: object)-> dict:
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
            construct_participant(spotify_basic_data)
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
    response = []
    for i in query:
        response.append(Serializer(i).data)
    return response