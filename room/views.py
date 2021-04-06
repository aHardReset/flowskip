# Django
from django.contrib.sessions.models import Session
from django.urls import resolve
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

# Rest Framework
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

import json

# Models
from room import serializers as room_serializers
from room.serializers import CreateRoomSerializer, RoomSerializer
from room.models import Rooms, VotesToSkip, SkippedTracks, SuccessTracks, RecommendedTracks
from user.models import Users, PaidUsers, Commerces
from flowskip.auths import SessionAuthentication

# Utilities
from room import snippets as room_snippets
from spotify import api as spotify_api
from flowskip import response_msgs

TOO_LATE = 0

class RoomManager(APIView):
    authentication_classes = [SessionAuthentication]

    def get(self, request, format=None):
        response = {}

        try:
            session_key = request.GET['session_key']
            code = request.GET['code']
            room = request.user.room
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

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
            response, response_status = self.create_personal(serializer, user, spotify_basic_data)
        if resolve(request.path).url_name == 'create-commerce':
            response, response_status = self.create_commerce(serializer, user, spotify_basic_data)
        
        return Response(response, status=response_status)

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
    authentication_classes = [SessionAuthentication]
    def post(self, request, format=None):
        response={}

        try:
            session_key = request.data['session_key']
            code = request.data['code']
            if not request.user.room is None:
                response['msg'] = f'user with session_key: {session_key} is already in a room with code: {request.user.room.code}'
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
        request.user.room = room
        request.user.save(update_fields=['room'])
        response['msg'] = f'user with session_key: {session_key} added to room with code: {code}'
        return Response(response, status=status.HTTP_201_CREATED)

    def get(self, request, format=None):
        response = {}

        
        return Response(response, status=status.HTTP_200_OK)
    
    def delete(self, request, format=None):
        response = {}

        try:
            session_key = request.data["session_key"]
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if request.user.room is None:
            response['msg'] = f"user with session_key: {session_key} does not have a room"
            return Response(response, status=status.HTTP_204_NO_CONTENT)
        
        if request.user.room.host.session.session_key == session_key:
            room = Rooms.objects.filter(host=request.user).delete()
            response['msg'] = f'user with session:key:{session_key} was host of {room[0]} rooms and the room was killed'
            return Response(response, status=status.HTTP_204_NO_CONTENT)
        
        request.user.room = None
        request.user.save(update_fields=['room'])
        response['msg'] = f'user with session_key:{session_key} leave the room'
        return Response(response, status=status.HTTP_204_NO_CONTENT)

    def geo_filter(self, request):
        print("The user is commerce, so check its geolocalization")

class StateManager(APIView):
    authentication_classes = [SessionAuthentication]
    
    def post(self, request, format=None):
        response = {}
        try:
            self.session_key = request.data['session_key']
            self.code = request.data['code']
            self.track_id = request.data.get('track_id')
            self.user = request.user
            self.room = Rooms.objects.get(code=self.code)
            self.sp_api_tunel = spotify_api.api_manager(self.room.host.spotify_basic_data)
            self.is_host = self.room.host.session.session_key == self.session_key
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e).replace("query", self.session_key)
            return Response(response, status=status.HTTP_200_OK)
        if not request.user.room.code == self.code:
            response['msg'] = f'code {self.code} incorrect, maybe the room has changed'
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        
        switch = resolve(request.path).url_name.lower()
        if switch == 'vote-to-skip':
            response = self.vote_to_skip()
        return Response(response, status=self.response_code)
    
    def vote_to_skip(self):
        response = {}
        if not self.track_id:
            response['msg'] = f"track_id {self.track_id} not found in request"
            self.response_code = status.HTTP_400_BAD_REQUEST
            return None
        
        if self.room.track_id == "":
            response['msg'] = f"there's no track played ever in this room"
            self.response_code = status.HTTP_304_NOT_MODIFIED
            return None
        
        current_playing_track = json.loads(self.room.current_playing_track)
        progress_ms = current_playing_track['progress_ms']
        duration_ms = current_playing_track['item']['duration_ms']
        if (progress_ms/duration_ms)*100 > TOO_LATE:
            response['msg'] = f"too late to vote"
            self.response_code = status.HTTP_410_GONE
            return None
        
        room_votes = VotesToSkip.objects.filter(room=self.room)
        room_votes.exclude(track_id=self.room.track_id).delete()
        if self.room.track_id != self.track_id:
            response['msg'] = 'maybe you have voted to old track_id'
            self.response_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            return None
        
        track_votes = VotesToSkip.objects.filter(track_id=self.track_id)
        votes = track_votes.count()
        for user in track_votes.values('user'):
            if self.user.session.session_key == user['user']:
                response['msg'] = 'This user has vote already'
                self.response_code = status.HTTP_208_ALREADY_REPORTED
                return None
        vote = VotesToSkip(
            room= self.room,
            user = self.user,
            track_id = self.room.track_id
        )
        vote.save()
        votes += 1
    
        response['msg'] = "new vote registered"
        self.response_code = status.HTTP_200_OK
        if votes >= self.room.votes_to_skip:
            response['msg'] = "skipping song"
            # El verdugo -> has hecho el voto de gracia
            self.sp_api_tunel.next_track()
            room_snippets.register_track(SkippedTracks, self.room, current_playing_track)
        return response

    def get(self, request, format=None):
        response = {}

        try:
            code = request.GET['code']
            room = Rooms.objects.get(code=code)
            is_host = room.host.session.session_key == request.user.session.session_key
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e).replace("query", request.user.session.session_key)
            return Response(response, status=status.HTTP_200_OK)
        
        if not request.user.room.code == code:
            response['msg'] = f'code {code} incorrect, maybe the room has changed'
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        
        response_status = status.HTTP_200_OK
        switch = resolve(request.path).url_name.lower()
        if switch == 'tracks':
            query = SuccessTracks.objects.filter(room=room)
            response['success_tracks'] = room_snippets.query_to_list_dict(query, room_serializers.SuccessTracksSerializer)
            query = SkippedTracks.objects.filter(room=room)
            response['skipped_tracks'] = room_snippets.query_to_list_dict(query, room_serializers.SkippedTracksSerializer)
            query = RecommendedTracks.objects.filter(room=room)
            response['recommended_tracks'] = room_snippets.query_to_list_dict(query, room_serializers.RecommendedTracksSerializer)
        return Response(response, status=response_status)
    
    def patch(self, request, format=None):
        response = {}
        try:
            track_id = self.request.data['track_id']
            room = Rooms.objects.get(code=self.request.data['code'])
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = str(e)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        sp_api_tunel = spotify_api.api_manager(room.host.spotify_basic_data)
        is_host = room.host.session.session_key == request.user.session.session_key
        data = {}
        if (timezone.now() - room.modified_at).total_seconds() > 2:
            data = sp_api_tunel.current_playback()
            room = room_snippets.clean_playback(room, data)
        response['current_playback'] = room.current_playing_track

        if data != {}:
            progress_ms = data['progress_ms']
            durarion_ms = data['item']['duration_ms']
            same_track = data['item']['id'] == track_id
            if (progress_ms/durarion_ms) *100 > TOO_LATE and same_track:
                room_snippets.register_track(SuccessTracks, room, data)

        participants_in_req = request.data.get('participants', [])
        if type(participants_in_req) is list:
            participants_in_db = Users.objects.filter(room=room)
            participants_in_db = room_snippets.construct_participants(participants_in_db)
            response['participants'] = room_snippets.calculate_user_deltas(participants_in_db, participants_in_req)
        
        votes_in_req = request.data.get('votes', [])
        if type(votes_in_req) is list:
            votes_in_db = VotesToSkip.objects.filter(
                room=room
            ).filter(track_id=room.track_id)

            votes_in_db = [vote.user for vote in votes_in_db]
            votes_in_db = room_snippets.construct_participants(votes_in_db)
            response['votes_to_skip'] = room_snippets.calculate_user_deltas(votes_in_db, votes_in_req)
        response_code = status.HTTP_200_OK
        return Response(response, status=response_code)