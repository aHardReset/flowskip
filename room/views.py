# Django
from typing import Tuple
from django.contrib.sessions.models import Session
from django.urls import resolve
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

# Rest Framework
from rest_framework import status
from rest_framework import response
from rest_framework.views import APIView
from rest_framework.response import Response

import json

# Models
from room.serializers import CreateRoomSerializer, RoomSerializer
from room.models import Rooms
from user.models import Users, PaidUsers, Commerces

# Utilities
from spotify import api as spotify_api
from spotify.snippets import get_db_tokens, update_db_tokens
from flowskip import response_msgs


class RoomManager(APIView):

    def get(self, request, format=None):
        response = {}

        try:
            session_key = request.GET['session_key']
            code = request.GET['code']
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            room = user.room
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_200_OK)

        if room is None:
            response['msg'] = f'the user with session_key: {session_key} is not associated to any room'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        if room.code != code:
            response['msg'] = f'code {code} is incorrect, maybe the room has changed'
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        response = RoomSerializer(room).data
        response['user_is_host'] = room.host.session.session_key == session_key
        return Response(response, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        response = {}
        
        try:
            session_key = request.data['session_key']
            request.data['votes_to_skip']
            request.data['guests_can_pause']
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            spotify_basic_data = user.spotify_basic_data
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_200_OK)

        if spotify_basic_data is None:
            response['msg'] = response_msgs.user_not_authenticated(session_key)
            return Response(response, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateRoomSerializer
        serializer = serializer(data=request.data)
        if not serializer.is_valid():
            response['msg'] = response_msgs.serializer_not_valid()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
        if resolve(request.path).url_name == 'create-personal':
            response, status = self.create_personal(serializer, user, spotify_basic_data)
            return Response(response, status=status)
        if resolve(request.path).url_name == 'create-commerce':
            response, status = self.create_commerce(serializer, user, spotify_basic_data)
            return Response(response, status=status)

    def create_personal(self, serializer, user, spotify_basic_data, format=None):
        response = {}
        
        if not user.room is None:
            response['msg'] = response_msgs.user_already_in_room(user.room.code)
            response['code'] = user.room.code
            return response, status.HTTP_208_ALREADY_REPORTED
        try:
            paid_details = PaidUsers.objects.get(pk=spotify_basic_data.id)
        except PaidUsers.DoesNotExist:
            paid_details = None

        if paid_details is None:
            room = Rooms(
                host = user,
                guests_can_pause = serializer.data['guests_can_pause'],
                votes_to_skip = serializer.data['votes_to_skip'],
            )
        else:
            room = Rooms(
                host = user,
                code=paid_details.exclusive_code,
                guests_can_pause = serializer.data['guests_can_pause'],
                votes_to_skip = serializer.data['votes_to_skip'],
            )
        room.save()
        user.room = room
        user.save(update_fields=['room'])
        response['msg'] = response_msgs.room_created()
        response['code'] = room.code
        return response, status.HTTP_200_OK

    def create_commerce(self, serializer, user, spotify_basic_data, format=None):
        response = {} 

        try:
            paid_details = Commerces.objects.get(pk=spotify_basic_data.id)
        except Commerces.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_have_a_commerce(user.session_key)
            return response, status.HTTP_402_PAYMENT_REQUIRED

        # ! Add the geolocalization filter
        
        rooms = Rooms.objects.filter(pk=user)
        if rooms.exists():
            room = rooms[0]
            room.code = paid_details.exclusive_code
            room.guests_can_pause = serializer.data['guests_can_pause']
            room.votes_to_skip = serializer.data['votes_to_skip']
            room.save(update_fields=[
                'code',
                'guests_can_pause',
                'votes_to_skip',
            ])
            response['msg'] = response_msgs.commerce_room_updated(user.session_key)
            return response, status.HTTP_208_ALREADY_REPORTED
        
        room = Rooms(
                host = user,
                code=paid_details.exclusive_code,
                guests_can_pause = serializer.data['guests_can_pause'],
                votes_to_skip = serializer.data['votes_to_skip'],
            )
        room.save()
        response['msg'] = response_msgs.room_created()
        return response, status.HTTP_201_CREATED

class ParticipantManager(APIView):
    def post(self, request, format=None):
        response={}

        try:
            session_key = request.data['session_key']
            code = request.data['code']
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            if not user.room is None:
                response['msg'] = f'user with session_key: {session_key} is already in a room with code: {user.room.code}'
                return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
            room = Rooms.objects.get(code=code)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        is_commerce = Commerces.objects.filter(exclusive_code=room.code).exists()
        if is_commerce:
            self.geo_filter(request)
        user.room = room
        user.save(update_fields=['room'])
        response['msg'] = f'user with session_key: {session_key} added to room with code: {code}'
        return Response(response, status=status.HTTP_201_CREATED)

    def get(self, request, format=None):
        response = {}

        
        return Response(response, status=status.HTTP_200_OK)
    
    def delete(self, request, format=None):
        response = {}

        try:
            session_key = request.data["session_key"]
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        if user.room is None:
            response['msg'] = f"user with session_key: {session_key} does not have a room"
            return Response(response, status=status.HTTP_204_NO_CONTENT)
        
        if user.room.host.session.session_key == session_key:
            room = Rooms.objects.filter(host=user).delete()
            response['msg'] = f'user with session:key:{session_key} was host of {room[0]} rooms and the room was killed'
            return Response(response, status=status.HTTP_204_NO_CONTENT)
        
        user.room = None
        user.save(update_fields=['room'])
        response['msg'] = f'user with session_key:{session_key} leave the room'
        return Response(response, status=status.HTTP_204_NO_CONTENT)

    def geo_filter(self, request):
        print("The user is commerce, so check its geolocalization")

class StateManager(APIView):
    def post(self, request, format=None):
        response = {}
        try:
            session_key = request.data['session_key']
            code = request.data['code']
            song_id = request.data.get('song_id')
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            room = Rooms.objects.get(code=code)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_200_OK)
        if not user.room.code == code:
            response['msg'] = f'code {code} incorrect, maybe the room has changed'
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        
        switch = resolve(request.path).url_name.lower()
        if switch == 'vote_to_skip':
            pass
        return Response(response, status=status.HTTP_201_CREATED)
    
    @staticmethod
    def vote_to_skip(user, song_id):
        pass
        
        return Response(response, status=status.HTTP_200_OK)

    def get(self, request, format=None):
        response = {}

        try:
            session_key = request.GET['session_key']
            code = request.GET['code']
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            room = Rooms.objects.get(code=code)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_200_OK)
        
        if not user.room.code == code:
            response['msg'] = f'code {code} incorrect, maybe the room has changed'
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        
        sp = spotify_api.api_manager(room.host.spotify_basic_data)
        
        switch = resolve(request.path).url_name.lower()
        if switch == 'current-playing-track':
            response = self.frontend_current_playing_track(room)
        elif switch == 'current-playback':
            response = self.frontend_current_playback(sp.current_playback())
        elif switch == 'participants':
            response = self.get_room_participants(room)
        
        return Response(response, status=status.HTTP_200_OK)
    
    @staticmethod
    def frontend_current_playing_track(room: object):
        if (timezone.now() - room.modified_at).total_seconds() > 2:
            sp = spotify_api.api_manager(room.host.spotify_basic_data)
            data = sp.current_user_playing_track()
            if data:
                del data['timestamp']
                del data['context']
                room.song_id = data['item']['id']
            else:
                data = {}
                room.song_id = ""
            
            room.current_playback = json.dumps(data)
            room.modified_at = timezone.now()
            room.save(update_fields=[
                'song_id',
                'current_playback',
                'modified_at',
            ])
        return json.loads(room.current_playback)
    
    @staticmethod
    def frontend_current_playback(data: dict) -> dict:
        if data:
            # ! Si esta en shuffle desactivar
            # ! del data['shuffle']
            del data['device']
            del data['context']
            del data['actions']
            del data['timestamp']
        # ! Store the data, song_id in the CurrentPlayback
        # ? If current_song_id != song_id delete all in the rows
        # ! This function only will query the database not spotify
        # ! We will make a request in spotify on the create room
        # ! And schedule a function every one second.
        return data if data else {}

    @staticmethod
    def get_room_participants(room: object)-> dict:
        participants = []

        users = Users.objects.filter(room=room)
        for user in users:
            spotify_basic_data = user.spotify_basic_data
            # Llamar a spotify
            if spotify_basic_data is None:
                participant = {
                    'is_authenticated': False,
                    'id': user.session.session_key[-6:]
                }
            else:
                participant = {
                    'is_authenticated': True,
                    'id': user.session.session_key[-6:],
                    'display_name': spotify_basic_data.display_name,
                    'image_url': spotify_basic_data.image_url,
                    'external-url' : spotify_basic_data.external_url,
                    'product': spotify_basic_data.product
                }
            participants.append(participant)
        
        return participants