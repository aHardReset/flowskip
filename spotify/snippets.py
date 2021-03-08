from urllib import parse

ALLOWED_REDIRECTS = ['http://localhost:300']

def construct_state(session_key:str, redirect_url:str, **kwargs) -> str:
    params = {
        'session_key': session_key,
        'redirect_url': redirect_url,
    }
    params = {**params, **kwargs}
    
    return parse.urlencode(params)

def deconstruct_state(query: str) -> dict:
    return parse.parse_qs(query)

def update_data_changed(spotify_basic_data: object ,data: dict)-> object:
    if data['display_name'] != spotify_basic_data.display_name:
            spotify_basic_data.display_name = data['display_name']
            spotify_basic_data.save(update_fields=['display_name'])
    if data['product'] != spotify_basic_data.product:
        spotify_basic_data.product = data['product']
        spotify_basic_data.save(update_fields=['product'])
    if data['external_urls'].get("spotify") != spotify_basic_data.external_url:
        spotify_basic_data.external_url = data['external_urls'].get("spotify")
        spotify_basic_data.save(update_fields=['external_url'])
    try:
        image_url = data['images'][0].get('url')
        if image_url != spotify_basic_data.image_url:
            spotify_basic_data.image_url = image_url
            spotify_basic_data.save(update_fields=['image_url'])
    except IndexError:
        if not spotify_basic_data.image_url is None:
            spotify_basic_data.image_url = None
            spotify_basic_data.save(update_fields=['image_url'])

    return spotify_basic_data