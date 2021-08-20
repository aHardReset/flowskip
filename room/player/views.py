# Django
from typing import Callable, Tuple
import re
from django.urls import resolve
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import exceptions

from room import serializers as room_serializers
from room.decorators import in_room_required, is_host_required
from flowskip.auths import UserAuthentication
from spotify import api as spotify_api
from spotipy.exceptions import SpotifyException

valid_actions_endpoints = dict()
valid_actions_endpoints['POST'] = (
    'next-track',
    'previous-track',
    'seek-track',
    'repeat',
    'volume',
    'shuffle',
    'add-to-queue'
)
valid_actions_endpoints['PUT'] = (
    'start-playback',
    'pause-playback',
    'transfer-playback',
)


# Create your views here.
class PlayerManager(APIView):
    authentication_classes = [UserAuthentication]

    @in_room_required
    @is_host_required
    def get(self, request, format=None):
        response = {}

        room_serializers.CodeSerializer(data=request.GET).is_valid(raise_exception=True)
        if not request.user.room.code == request.GET['code']:
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)

        switch = resolve(request.path).url_name.lower()
        if switch == 'devices':
            pass
        else:
            response['detail'] = f'Bad request: {switch}'
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(response, status=status_code)

    @in_room_required
    @is_host_required
    def post(self, request, format=None):
        response = {}
        room_serializers.CodeSerializer(data=request.data).is_valid(raise_exception=True)
        if not request.user.room.code == request.data['code']:
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        del(request.data['code'])

        action = self.action_validation(resolve(request.path).url_name.lower(), request.method)

        sp_api_tunnel = spotify_api.api_manager(request.user.room.host.spotify_basic_data)
        actions_callables = (
            sp_api_tunnel.next_track,
            sp_api_tunnel.previous_track,
            sp_api_tunnel.seek_track,
            sp_api_tunnel.repeat,
            sp_api_tunnel.volume,
            sp_api_tunnel.shuffle,
            sp_api_tunnel.add_to_queue
        )

        response, status_code = self.modify_player(
            actions_names=valid_actions_endpoints[request.method],
            actions_callables=actions_callables,
            action=action,
            body=request.data,
            success_code=status.HTTP_204_NO_CONTENT
        )

        return Response(response, status=status_code)

    @in_room_required
    @is_host_required
    def put(self, request, format=None):
        response = {}

        room_serializers.CodeSerializer(data=request.data).is_valid(raise_exception=True)
        if not request.user.room.code == request.data['code']:
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        del(request.data['code'])

        action = action = self.action_validation(resolve(request.path).url_name.lower(), request.method)

        sp_api_tunnel = spotify_api.api_manager(request.user.room.host.spotify_basic_data)
        actions_callables = (
            sp_api_tunnel.start_playback,
            sp_api_tunnel.pause_playback,
            sp_api_tunnel.transfer_playback,
        )

        response, status_code = self.modify_player(
            actions_names=valid_actions_endpoints[request.method],
            actions_callables=actions_callables,
            action=action,
            body=request.data,
            success_code=status.HTTP_204_NO_CONTENT
        )

        return Response(response, status=status_code)

    def modify_player(
        self,
        actions_names: Tuple[str],
        actions_callables: Tuple[Callable],
        action: str, body: dict,
        success_code: int
    ) -> Tuple[dict, int]:
        response = {}
        actions = dict(
            (action_name, action_value)
            for action_name, action_value
            in zip(actions_names, actions_callables)
        )
        try:
            response, status_code = self.do_spotify_action(
                action=actions[action],
                success_code=success_code,
                **body
            )
        except KeyError:
            response['detail'] = 'Request valid but not available yet'
            status_code = status.HTTP_501_NOT_IMPLEMENTED
        except TypeError as e:
            e = re.sub(r'[ -~]+\(+\)', 'Bad request:', str(e))
            response['detail'] = e
            status_code = status.HTTP_400_BAD_REQUEST
        return response, status_code

    @staticmethod
    def do_spotify_action(action: Callable, success_code, **kwargs):
        response = {}
        print(kwargs)
        try:
            action(**kwargs)
            status_code = success_code
        except SpotifyException as e:
            response['detail'] = F"spotify has returned an error: '{e}'"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return response, status_code

    @staticmethod
    def action_validation(action: str, method: str) -> str:
        if action not in valid_actions_endpoints[method]:
            raise exceptions.ValidationError(f'Bad request: {action}')
        return action
