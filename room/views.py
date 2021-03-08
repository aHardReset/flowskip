from django.shortcuts import render
from django.contrib.sessions.models import Session
from rest_framework import status
from rest_framework import response
from rest_framework.views import APIView
from rest_framework.response import Response

from room.serializers import CreateRoomSerializer, RoomSerializer
from room.models import Rooms
from user.models import Users, PaidUsers, Commerces
from spotify.api import get_current_playback
from flowskip import response_msgs
# Create your views here.

class CreatePersonal(APIView):
    def post(self, request, format=None):
        response = {}

        try:
            session_key = request.data['session_key']
            votes_to_skip = request.data['votes_to_skip']
            guests_can_pause = request.data['guests_can_pause']
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            spotify_basic_data = user.spotify_basic_data
            if spotify_basic_data is None:
                response['msg'] = response_msgs.user_not_authenticated(session_key)
                return Response(response, status=status.HTTP_403_FORBIDDEN)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreateRoomSerializer
        serializer = serializer(data=request.data)
        if not serializer.is_valid():
            response['msg'] = response_msgs.serializer_not_valid()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.room is None:
            response['msg'] = response_msgs.user_already_in_room(user.room.code)
            response['code'] = user.room.code
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
        
        try:
            paid_details = PaidUsers.objects.get(pk=spotify_basic_data.id)
        except PaidUsers.DoesNotExist:
            paid_details = None

        if paid_details is None:
            room = Rooms(
                host = user,
                guests_can_pause = guests_can_pause,
                votes_to_skip = votes_to_skip,
            )
        else:
            room = Rooms(
                host = user,
                code=paid_details.exclusive_code,
                guests_can_pause = guests_can_pause,
                votes_to_skip = votes_to_skip,
            )
        room.save()
        user.room = room
        user.save(update_fields=['room'])
        response['msg'] = response_msgs.room_created()
        response['code'] = room.code
        return Response(response, status=status.HTTP_200_OK)

class CreateCommerce(APIView):
    def post(self, request, format=None):
        response={}
        
        try:
            session_key = request.data['session_key']
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            spotify_basic_data = user.spotify_basic_data
            if spotify_basic_data is None:
                response['msg'] = response_msgs.user_not_authenticated(session_key)
                return Response(response, status=status.HTTP_403_FORBIDDEN)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreateRoomSerializer
        serializer = serializer(data=request.data)
        if not serializer.is_valid():
            response['msg'] = response_msgs.serializer_not_valid()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            paid_details = Commerces.objects.get(pk=spotify_basic_data.id)
        except Commerces.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_have_a_commerce(session_key)
            return Response(response, status=status.HTTP_402_PAYMENT_REQUIRED)

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
            response['msg'] = response_msgs.commerce_room_updated(session_key)
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
        
        room = Rooms(
                host = user,
                code=paid_details.exclusive_code,
                guests_can_pause = serializer.data['guests_can_pause'],
                votes_to_skip = serializer.data['votes_to_skip'],
            )
        room.save()
        response['msg'] = response_msgs.room_created()
        return Response(response, status=status.HTTP_201_CREATED)

class Join(APIView):
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
            response['msg'] = response_msgs.key_error()
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)  
        except Rooms.DoesNotExist:
            response['msg'] = response_msgs.room_does_not_exists(code)
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        is_commerce = Commerces.objects.filter(exclusive_code=room.code).exists()
        if is_commerce:
            # ! Add the geolocalization filter
            pass
        user.room = room
        user.save(update_fields=['room'])
        response['msg'] = f'user with session_key: {session_key} added to room with code: {code}'
        return Response(response, status=status.HTTP_201_CREATED)

class Participants(APIView):
    def get(self, request, format=None):
        response = {}

        try:
            code = request.GET['code']
            room = Rooms.objects.get(code=code)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Rooms.DoesNotExist:
            response['msg'] = response_msgs.room_does_not_exists(code)
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        response['users'] = []
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
            
            response['users'].append(participant)
        return Response(response, status=status.HTTP_200_OK)
        
class Details(APIView):
    def get(self, request, format=None):
        serializer = RoomSerializer
        response = {}

        try:
            session_key = request.GET["session_key"]
            code = request.GET["code"]
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            room = user.room
            if room is None:
                response['msg'] = f'the user with session_key: {session_key} is not associated to any room'
                return Response(response, status=status.HTTP_404_NOT_FOUND)
            if room.code != code:
                response['msg'] = f'code provided is incorrect, maybe the room has changed'
                return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_200_OK)
        except Users.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        response = RoomSerializer(room).data
        response['user_is_host'] = room.host.session.session_key == session_key
        return Response(response, status=status.HTTP_200_OK)

class Leave(APIView):
    def patch(self, request, format=None):
        response = {}

        try:
            session_key = request.data["session_key"]
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            if user.room is None:
                response['msg'] = f"user with session_key: {session_key} does not have a room"
                return Response(response, status=status.HTTP_204_NO_CONTENT)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_200_OK)   
        except Users.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        if user.room.host.session.session_key == session_key:
            room = Rooms.objects.filter(host=user).delete()
            response['msg'] = f'user with session:key:{session_key} was host of {room[0]} rooms and the room was killed'
            return Response(response, status=status.HTTP_204_NO_CONTENT)
        
        user.room = None
        user.save(update_fields=['room'])
        response['msg'] = f'user with session_key:{session_key} leave the room'
        return Response(response, status=status.HTTP_204_NO_CONTENT)
