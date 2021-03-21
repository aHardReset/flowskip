

# 200 - 201 OK's
def session_started(session_key: str) -> str:
    return f'new session with session_key: {session_key} started'

def user_created(session_key: str) -> str:
    return f'new user with session_key: {session_key} created'

def user_deleted(total: int, session_key: str) -> str:
    return f"{total} users deleted with session_key: {session_key}"

def authenticate_url_generated(redirect_url: str) -> str:
    return " ".join(
        ['URL generated, when the user act will be redirected',
        f'to: {redirect_url}']
    )

def room_created()-> str: return 'room created'

def commerce_room_updated(session_key: str) -> str:
    f'room for user with session_key: {session_key} updated'

# 208 Errors
def user_already_authenticated(session_key: str) -> str:
    return f'user with session_key: {session_key} already authenticated'

def user_already_exists(session_key: str) -> str:
    return f'user with session_key: {session_key} already exists'

def user_already_in_room(code: str) -> str:
    return f'this user is already in a room with code: {code}'

# 400-403 Errors
def key_error(key: str) -> str:
    return f'not key: {key} provided in request'

def serializer_not_valid() -> str:
    return 'data posted not valid'

def user_not_authenticated(session_key: str) -> str:
    return " ".join(
        [f'user with session_key: {session_key}',
        'is not authenticated']
    )

def room_does_not_exists(code: str) -> str:
    return f'room with code: {code} does not exists'

# 404 Errors
def session_does_not_exists(session_key: str) -> str: 
    return f'session with session_key: {session_key} does not exists'

def user_does_not_exists(session_key:str)-> str:
    return f'user with session_key: {session_key} does not exists'

def user_does_not_have_a_commerce(session_key: str)-> str:
    return " ".join(
        [f'user with session_key: {session_key}', 
        'does not have commerce']
    )

# 3rd party errors