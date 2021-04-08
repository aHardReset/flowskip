# Django
from django.urls import resolve
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

# Rest Framework
from rest_framework.request import Request
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

# Models
from room import serializers as room_serializers
from room import models as room_models
from user import models as user_models
from flowskip.auths import UserAuthentication

# Utilities
from room import snippets as room_snippets
from spotify import api as spotify_api
from typing import Tuple


TOO_LATE = 50

class RoomManager(APIView):
    authentication_classes = [UserAuthentication]

    def get(self, request, format=None):
        response = {}

        room_serializers.CodeSerializer(data=request.GET).is_valid(raise_exception=True)
        if request.user.room is None:
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Checks if the user code is the same as the request
        # ? Maybe is not neccesary
        if request.user.room.code != request.GET['code']:
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        response = room_serializers.RoomSerializer(request.user.room).data
        response['user_is_host'] = request.user.room.host.session.session_key == request.user.session.session_key
        return Response(response, status=status.HTTP_200_OK)

    def post(self, request, format=None) -> Response:
        response = {}
        
        room_serializers.CreateRoomSerializer(data=request.data).is_valid(raise_exception=True)

        if request.user.spotify_basic_data is None:
            return Response(response, status=status.HTTP_403_FORBIDDEN)
        
        if resolve(request.path).url_name == 'create-personal':
            response, response_status = self.create_personal(request)
        elif resolve(request.path).url_name == 'create-commerce':
            response, response_status = self.create_commerce(request)
        
        return Response(response, status=response_status)

    def create_personal(self, request):
        response = {}
        
        if request.user.room is not None:
            response['code'] = request.user.room.code
            return response, status.HTTP_208_ALREADY_REPORTED
        
        try:
            paid_details = user_models.PaidUsers.objects.get(pk=request.user.spotify_basic_data.id)
        except ObjectDoesNotExist:
            paid_details = None

        room = room_models.Rooms(
            host = request.user,
            guests_can_pause = request.data['guests_can_pause'],
            votes_to_skip = request.data['votes_to_skip'],
        )
        if paid_details:
            room.code = paid_details.exclusive_code
        room.save()
        request.user.room = room
        request.user.save(update_fields=['room'])
        response['code'] = room.code
        return response, status.HTTP_200_OK

    def create_commerce(self, request):
        response = {}

        try:
            paid_details = user_models.Commerces.objects.get(pk=request.user.spotify_basic_data.id)
        except ObjectDoesNotExist:
            return response, status.HTTP_402_PAYMENT_REQUIRED

        # ! Add the geolocalization filter
        
        rooms = room_models.Rooms.objects.filter(pk=request.user)
        if rooms.exists():
            room = rooms[0]
            room.code = paid_details.exclusive_code
            room.guests_can_pause = request.data['guests_can_pause']
            room.votes_to_skip = request.data['votes_to_skip']
            room.save(update_fields=[
                'code',
                'guests_can_pause',
                'votes_to_skip',
            ])
            return response, status.HTTP_208_ALREADY_REPORTED
        
        room = room_models.Rooms(
                host=request.user,
                code=paid_details.exclusive_code,
                guests_can_pause = request.data['guests_can_pause'],
                votes_to_skip = request.data['votes_to_skip'],
            )
        room.save()
        return response, status.HTTP_201_CREATED

class ParticipantManager(APIView):
    authentication_classes = [UserAuthentication]
    def post(self, request, format=None):
        response={}
        room_serializers.CodeSerializer(data=request.data).is_valid(raise_exception=True)
        if not request.user.room is None:
            response['code'] = request.user.room.code
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)

        try:
            room = room_models.Rooms.objects.get(code=request.data['code'])
        except ObjectDoesNotExist as e:
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        if user_models.Commerces.objects.filter(exclusive_code=room.code).exists():
            self.geo_filter(request)
        
        request.user.room = room
        request.user.save(update_fields=['room'])
        return Response(response, status=status.HTTP_201_CREATED)

    def get(self, request, format=None):
        response = {}
        
        return Response(response, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    def delete(self, request, format=None):
        response = {}

        if request.user.room is None:
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        if request.user.room.host.session.session_key == request.user.session.session_key:
            _ = room_models.Rooms.objects.filter(host=request.user).delete()
            return Response(response, status=status.HTTP_204_NO_CONTENT)
        
        request.user.room = None
        request.user.save(update_fields=['room'])
        return Response(response, status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def geo_filter(request):
        print("The user is commerce, so check its geolocalization")

class StateManager(APIView):
    authentication_classes = [UserAuthentication]
    
    def post(self, request, format=None):
        response = {}

        room_serializers.CodeSerializer(data=request.data).is_valid(raise_exception=True)
        if not request.user.room.code == request.data['code']:
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        
        switch = resolve(request.path).url_name.lower()
        if switch == 'vote-to-skip':
            response, status_code = self._post_vote_to_skip(request)
        return Response(response, status=status_code)
    
    @staticmethod
    def _post_vote_to_skip(request):
        response = {}

        room_serializers.TrackIdSerializer(data=request.data).is_valid(raise_exception=True)
        try:
            room = room_models.Rooms.objects.get(code=request.data['code'])
        except ObjectDoesNotExist:
            return Response(response, status=status.HTTP_200_OK)
        
        if room.track_id is None:
            return response, status.HTTP_410_GONE
        
        current_playing_track = room.current_playing_track
        progress_ms = current_playing_track['progress_ms']
        duration_ms = current_playing_track['item']['duration_ms']
        if (progress_ms/duration_ms)*100 > TOO_LATE:
            response['msg'] = f"too late to vote"
            return response, status.HTTP_410_GONE
        
        room_votes = room_models.VotesToSkip.objects.filter(room=room)
        room_votes.exclude(track_id=room.track_id).delete()
        if room.track_id != request.data['track_id']:
            return response, status.HTTP_301_MOVED_PERMANENTLY
        
        track_votes = room_models.VotesToSkip.objects.filter(track_id=request.data['track_id'])
        votes = track_votes.count()
        for user in track_votes.values('user'):
            if request.user.session.session_key == user['user']:
                return response, status.HTTP_208_ALREADY_REPORTED
        vote = room_models.VotesToSkip(room=room, user=request.user, track_id=room.track_id)
        vote.save()
        votes += 1

        if votes >= room.votes_to_skip:
            response['msg'] = "skipping song"
            # El verdugo -> has hecho el voto de gracia
            sp_api = spotify_api.api_manager(room.host.spotify_basic_data)
            sp_api.next_track()
            room_snippets.register_track(room_models.SkippedTracks, room, current_playing_track)
        return response, status.HTTP_201_CREATED

    def get(self, request, format=None):
        response = {}

        room_serializers.CodeSerializer(data=request.GET).is_valid(raise_exception=True)
        
        if request.user.room.code != request.GET['code']:
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)
        
        switch = resolve(request.path).url_name.lower()
        if switch == 'tracks':
            response, status_code = self._get_tracks(request)
        return Response(response, status=status_code)

    @staticmethod
    def _get_tracks(request):
        response = {}
        try:
            room = room_models.Rooms.objects.get(code=request.GET['code'])
        except ObjectDoesNotExist:
            return Response(response, status=status.HTTP_200_OK)
        query = room_models.SuccessTracks.objects.filter(room=room)
        response['success_tracks'] = room_snippets.query_to_list_dict(query, room_serializers.SuccessTracksSerializer)
        query = room_models.SkippedTracks.objects.filter(room=room)
        response['skipped_tracks'] = room_snippets.query_to_list_dict(query, room_serializers.SkippedTracksSerializer)
        query = room_models.RecommendedTracks.objects.filter(room=room)
        response['recommended_tracks'] = room_snippets.query_to_list_dict(query, room_serializers.RecommendedTracksSerializer)
        return response, status.HTTP_200_OK
    
    def patch(self, request, format=None):
        response = {}
        room_serializers.StateManagerSerializer(
            data=request.data
        ).is_valid(raise_exception=True)
        try:
            room = room_models.Rooms.objects.get(code=request.data['code'])
        except ObjectDoesNotExist as e:
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        sp_api_tunel = spotify_api.api_manager(room.host.spotify_basic_data)
        is_host = room.host.session.session_key == request.user.session.session_key
        if (timezone.now() - room.modified_at).total_seconds() > 2:
            data = sp_api_tunel.current_playback()
            room = room_snippets.clean_playback(room, data)
        response['current_playback'] = room.current_playing_track

        if response['current_playback'] != {}:
            progress_ms = response['current_playback']['progress_ms']
            durarion_ms = response['current_playback']['item']['duration_ms']
            same_track = response['current_playback']['item']['id'] == request.data['track_id']
            if (progress_ms/durarion_ms) *100 > TOO_LATE and same_track:
                room_snippets.register_track(room_models.SuccessTracks, room, response['current_playback'])

        participants_in_req = request.data.get('participants', [])
        if type(participants_in_req) is list:
            participants_in_db = user_models.Users.objects.filter(room=room)
            participants_in_db = room_snippets.construct_participants(participants_in_db)
            response['participants'] = room_snippets.calculate_user_deltas(participants_in_db, participants_in_req)
        
        votes_in_req = request.data.get('votes', [])
        if type(votes_in_req) is list:
            votes_in_db = room_models.VotesToSkip.objects.filter(
                room=room
            ).filter(track_id=room.track_id)

            votes_in_db = [vote.user for vote in votes_in_db]
            votes_in_db = room_snippets.construct_participants(votes_in_db)
            response['votes_to_skip'] = room_snippets.calculate_user_deltas(votes_in_db, votes_in_req, gone=False)
        response_code = status.HTTP_200_OK
        return Response(response, status=response_code)
