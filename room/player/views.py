# Django
from django.urls import resolve
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from room import serializers as room_serializers
from room.decorators import in_room_required, is_host_required
from flowskip.auths import UserAuthentication
from spotify.decorators import is_authenticated_in_spotify_required
from spotify import api as spotify_api
from spotipy.exceptions import SpotifyException


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
        
        switch = resolve(request.path).url_name.lower()
        if switch == 'next-track':
            pass
        elif switch == 'previous-track':
            pass
        elif switch == 'seek-track':
            pass
        elif switch == 'repeat':
            pass
        elif switch == 'volume':
            pass
        elif switch == 'shuffle':
            pass
        elif switch == 'add-to-queue':
            pass
        else:
            response['detail'] = f'Bad request: {switch}'
            status_code = status.HTTP_400_BAD_REQUEST
        
        return Response(response, status=status_code)

    @in_room_required
    @is_host_required
    def put(self, request, format=None):
        response = {}

        room_serializers.CodeSerializer(data=request.data).is_valid(raise_exception=True)
        if not request.user.room.code == request.data['code']:
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)

        switch = resolve(request.path).url_name.lower()
        if switch == 'play':
            response, status_code = self._put_play(request)
        elif switch == 'pause':
            response, status_code = self._put_pause(request)
        elif switch == 'toggle-is-playing':
            pass
        elif switch == 'transfer':
            pass
        else:
            response['detail'] = f'Bad request: {switch}'
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(response, status=status_code)

    @staticmethod
    def _put_play(request):
        response = {}
        sp_api_tunnel = spotify_api.api_manager(request.user.room.host.spotify_basic_data)
        try:
            sp_api_tunnel.start_playback()
            status_code = status.HTTP_200_OK
        except SpotifyException as e:
            response, status_code = _spotify_error_handler(e)
        return response, status_code

    @staticmethod
    def _put_pause(request):
        response = {}
        sp_api_tunnel = spotify_api.api_manager(request.user.room.host.spotify_basic_data)
        try:
            sp_api_tunnel.pause_playback()
            status_code = status.HTTP_200_OK
        except SpotifyException as e:
            response, status_code = _spotify_error_handler(e)
        return response, status_code


def _spotify_error_handler(e):
    response = {}
    response['detail'] = F"spotify has returned an error: '{e}'"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return response, status_code
