import re
from typing import Callable, Tuple, NamedTuple
from spotipy import SpotifyException
from rest_framework import status
from urllib import parse

ALLOWED_REDIRECTS = ['http://localhost:300']


def construct_state_value(session_key: str, redirect_url: str, **kwargs) -> str:
    params = {
        'session_key': session_key,
        'redirect_url': redirect_url,
    }
    params = {**params, **kwargs}
    return parse.urlencode(params)


def deconstruct_state_value(query: str) -> dict:
    return parse.parse_qs(query)


def update_data_changed(spotify_basic_data: object, data: dict) -> object:
    update_fields = list()
    if data['display_name'] != spotify_basic_data.display_name:
        spotify_basic_data.display_name = data['display_name']
        update_fields.append('display_name')
    if data['product'] != spotify_basic_data.product:
        spotify_basic_data.product = data['product']
        update_fields.append('product')
    if data['external_urls'].get("spotify") != spotify_basic_data.external_url:
        spotify_basic_data.external_url = data['external_urls'].get("spotify")
        update_fields.append('external_url')
    try:
        image_url = data['images'][0].get('url')
        if image_url != spotify_basic_data.image_url:
            spotify_basic_data.image_url = image_url
            update_fields.append('external_url')
    except IndexError:
        spotify_basic_data.image_url = None
        update_fields.append('external_url')

    if update_fields:
        spotify_basic_data.save(update_fields=update_fields)
    return spotify_basic_data


def get_db_tokens(spotify_basic_data: object) -> dict:
    tokens = {
        'access_token': spotify_basic_data.access_token,
        'refresh_token': spotify_basic_data.refresh_token,
        'expires_at': spotify_basic_data.access_token_expires_at
    }
    return tokens


def update_db_tokens(spotify_basic_data: object, new_tokens: dict) -> object:
    spotify_basic_data.access_token = new_tokens['access_token']
    spotify_basic_data.refresh_token = new_tokens['refresh_token']
    spotify_basic_data.access_token_expires_at = new_tokens['expires_at']
    spotify_basic_data.save(update_fields=[
        'access_token',
        'refresh_token',
        'access_token_expires_at'
    ])
    return spotify_basic_data


def spotify_action(action: Callable, success_code, **kwargs):
    response = {}
    try:
        response = action(**kwargs)
        if response == "" or response is None:
            response = {}
        status_code = success_code
    except SpotifyException as e:
        response['detail'] = F"spotify has returned an error: '{e}'"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return response, status_code


def spotify_action_handler(
    actions_names: Tuple[str],
    actions_definitions: NamedTuple,
    action: str,
    body: dict,
) -> Tuple[dict, int]:
    response = {}
    actions = dict(
        (action_name, action_value)
        for action_name, action_value
        in zip(actions_names, actions_definitions)
    )
    try:
        response, status_code = spotify_action(
            action=actions[action].callable,
            success_code=actions[action].success_code,
            **body
        )
    except KeyError:
        response = 'Request valid but not available yet'
        status_code = status.HTTP_501_NOT_IMPLEMENTED
    except TypeError as e:
        e = re.sub(r'[ -~]+\(+\)', 'Bad request:', str(e))
        response['detail'] = e
        status_code = status.HTTP_400_BAD_REQUEST
    return response, status_code
