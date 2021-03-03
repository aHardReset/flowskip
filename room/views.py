from django.shortcuts import render
from django.contrib.sessions.models import Session
from rest_framework import status
from rest_framework import response
from rest_framework.views import APIView
from rest_framework.response import Response

from room.serializers import CreateRoomSerializer, RoomSerializer
from room.models import Rooms
from user.models import Users, PaidUsers, Commerces
# Create your views here.

class CreatePersonal(APIView):
    def post(self, request, format=None):
        response = {}

        try:
            session_key = request.data['session_key']
            votes_to_skip = request.data['votes_to_skip']
            guests_can_pause = request.data['guests_can_pause']
        except KeyError as key:
            response['msg'] = f'not {key} found in request'
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CreateRoomSerializer
        serializer = serializer(data=request.data)
        if not serializer.is_valid():
            response['msg'] = 'data posted not valid'
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            spotify_basic_data = user.spotify_basic_data
        except Session.DoesNotExist:
            response['msg'] = f'session with session_key: {session_key} not found'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            response['msg'] = f'user with session_key: {session_key} not found'
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        if spotify_basic_data is None:
            response['msg'] = f'user with session_key: {session_key} not authenticated'
            return Response(response, status=status.HTTP_403_FORBIDDEN)
        
        user_rooms = Rooms.objects.filter(pk=user)
        if user_rooms.exists():
            user_room = user_rooms[0]
            response['msg'] = 'this user owns a room'
            response['code'] = user_room.code
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
        
        if not user.room is None:
            response['msg'] = 'this user is in a room already'
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
        response['msg'] = f'room created'
        response['code'] = room.code
        return Response(response, status=status.HTTP_200_OK)

class CreateCommerce(APIView):
    def post(self, request, format=None):
        response={}
        
        try:
            session_key = request.data['session_key']
        except KeyError as key:
            response['msg'] = f'not {key} found in request'
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CreateRoomSerializer
        serializer = serializer(data=request.data)
        if not serializer.is_valid():
            response['msg'] = 'data posted not valid'
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            spotify_basic_data = user.spotify_basic_data
        except Session.DoesNotExist:
            response['msg'] = f'session with session_key: {session_key} not found'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            response['msg'] = f'user with session_key: {session_key} not found'
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        if spotify_basic_data is None:
            response['msg'] = f'user with session_key: {session_key} not authenticated'
            return Response(response, status=status.HTTP_403_FORBIDDEN)
        
        try:
            paid_details = Commerces.objects.get(pk=spotify_basic_data.id)
        except Commerces.DoesNotExist:
            response['msg'] = f'user with session_key: {session_key} not has commerce'
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
            response['msg'] = f'Room for user with session_key: {session_key} updated'
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
        
        room = Rooms(
                host = user,
                code=paid_details.exclusive_code,
                guests_can_pause = serializer.data['guests_can_pause'],
                votes_to_skip = serializer.data['votes_to_skip'],
            )
        room.save()
        response['msg'] = f'New room for user with session_key: {session_key} created'
        return Response(response, status=status.HTTP_201_CREATED)

class Join(APIView):
    def post(self, request, format=None):
        response={}

        try:
            session_key = request.data['session_key']
            code = request.data['code']
        except KeyError as key:
            response['msg'] = f'not {key} found in request'
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
        except Session.DoesNotExist:
            response['msg'] = f'session with session_key: {session_key} not found'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            response['msg'] = f'user with session_key: {session_key} not found'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        rooms = Rooms.objects.filter(code=code)
        if not rooms.exists():
            response['msg'] = f'room with code: {code} does not exists'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        room = rooms[0]

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
        except KeyError as key:
            response['msg'] = f'not {key} found in request'
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        rooms = Rooms.objects.filter(code=code)
        if not rooms.exists():
            response['msg'] = f'room with code: {code} does not exists'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        room = rooms[0]

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
                    'image_url': spotify_basic_data.image_url
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
        except KeyError as key:
            response['msg'] = f"not {key} provided in request"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = Session.objects.get(pk=session_key)
        except Session.DoesNotExist:
            response['msg'] = f'session {session_key} not found'
            return Response(response, status=status.HTTP_200_OK)

        try:
            user = Users.objects.get(pk=session)
        except Users.DoesNotExist:
            response['msg'] = f'user with session_key: {session_key} not found'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        room = user.room
        if room is None:
            response['msg'] = f'the user with session_key: {session_key} is not associated to any room'
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        if room.code != code:
            response['msg'] = f'code provided is incorrect, maybe the room has changed'
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        
        response = RoomSerializer(room).data
        response['user_is_host'] = room.host.session.session_key == session_key
        return Response(response, status=status.HTTP_200_OK)

class Leave(APIView):
    def patch(self, request, format=None):
        response = {}

        try:
            session_key = request.data["session_key"]
        except KeyError as key:
            response['msg'] = f"not {key} provided in request"
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = Session.objects.get(pk=session_key)
        except Session.DoesNotExist:
            response['msg'] = f'session {session_key} not found'
            return Response(response, status=status.HTTP_200_OK)

        try:
            user = Users.objects.get(pk=session)
        except Users.DoesNotExist:
            response['msg'] = f'user with session_key: {session_key} not found'
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

