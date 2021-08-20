# Django
from django.urls import resolve
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict

# Rest Framework
from rest_framework import exceptions, status
from rest_framework.views import APIView
from rest_framework.response import Response

# Models
from room import serializers as room_serializers
from room.models import Rooms, TracksState, Votes
from user import models as user_models
from flowskip.auths import UserAuthentication
# Utilities
from room import snippets as room_snippets
from spotify import api as spotify_api
from spotipy.exceptions import SpotifyException
from room.decorators import is_host_required, in_room_required
from spotify.decorators import is_authenticated_in_spotify_required

TOO_LATE = 50


class RoomManager(APIView):
    authentication_classes = [UserAuthentication]

    @in_room_required
    def get(self, request, format=None):
        response = {}

        response = room_serializers.RoomInfoSerializer(request.user.room).data
        host_seesion_key = request.user.room.host.session.session_key
        user_session_key = request.user.session.session_key
        response['host'] = model_to_dict(
            request.user.room.host.spotify_basic_data,
            fields=['id', 'display_name', 'uri', 'image_url', 'external_url']
        )
        response['user_is_host'] = host_seesion_key == user_session_key
        return Response(response, status=status.HTTP_200_OK)

    @is_authenticated_in_spotify_required
    def post(self, request, format=None) -> Response:
        response = {}

        room_serializers.CreateRoomSerializer(data=request.data).is_valid(raise_exception=True)

        if request.user.spotify_basic_data is None:
            return Response(response, status=status.HTTP_403_FORBIDDEN)

        if resolve(request.path).url_name == 'create':
            response, response_status = self.create_personal(request)
        elif resolve(request.path).url_name == 'create-advanced':
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

        room = Rooms(
            host=request.user,
            guests_can_pause=request.data['guests_can_pause'],
            votes_to_skip=request.data['votes_to_skip'],
        )
        if paid_details:
            room.code = paid_details.exclusive_code
        room.save()
        request.user.room = room
        request.user.save(update_fields=['room'])
        response['code'] = room.code
        return response, status.HTTP_201_CREATED

    def create_commerce(self, request):
        response = {}

        try:
            paid_details = user_models.Commerces.objects.get(pk=request.user.spotify_basic_data.id)
        except ObjectDoesNotExist:
            return response, status.HTTP_402_PAYMENT_REQUIRED

        # ! Add the geolocalization filter

        rooms = Rooms.objects.filter(pk=request.user)
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

        room = Rooms(
            host=request.user,
            code=paid_details.exclusive_code,
            guests_can_pause=request.data['guests_can_pause'],
            votes_to_skip=request.data['votes_to_skip'],
        )
        room.save()
        return response, status.HTTP_201_CREATED

    @in_room_required
    @is_host_required
    def patch(self, request, format=None):
        response = {}
        room_serializers.CreateRoomSerializer(data=request.data).is_valid(raise_exception=True)
        request.user.room.guests_can_pause = request.data['guests_can_pause']
        request.user.room.votes_to_skip = request.data['votes_to_skip']
        request.user.room.save(update_fields=[
            'guests_can_pause',
            'votes_to_skip',
        ])

        return Response(response, status=status.HTTP_200_OK)


class ParticipantManager(APIView):
    authentication_classes = [UserAuthentication]

    def post(self, request, format=None):
        response = {}
        room_serializers.CodeSerializer(data=request.data).is_valid(raise_exception=True)
        if request.user.room is not None:
            response['code'] = request.user.room.code
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)

        try:
            room = Rooms.objects.get(code=request.data['code'])
        except ObjectDoesNotExist:
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

        if request.user.room is None:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        if request.user.room.host.session.session_key == request.user.session.session_key:
            _ = Rooms.objects.filter(host=request.user).delete()
            return Response({}, status=status.HTTP_200_OK)

        request.user.room = None
        request.user.save(update_fields=['room'])
        return Response({}, status=status.HTTP_200_OK)

    @staticmethod
    def geo_filter(request):
        print("The user is commerce, so check its geolocalization")


class StateManager(APIView):
    authentication_classes = [UserAuthentication]

    @in_room_required
    def post(self, request, format=None):
        response = {}

        room_serializers.CodeSerializer(data=request.data).is_valid(raise_exception=True)
        if not request.user.room.code == request.data['code']:
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)

        switch = resolve(request.path).url_name.lower()
        if switch == 'vote-to-skip':
            response, status_code = self._post_vote_to_skip(request)
        else:
            response['detail'] = f'Bad request: {switch}'
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(response, status=status_code)

    @staticmethod
    def _post_vote_to_skip(request):

        room_serializers.TrackIdSerializer(data=request.data).is_valid(raise_exception=True)

        if request.user.room.track_id is None:
            return {}, status.HTTP_410_GONE

        current_playing_track = request.user.room.current_playing_track
        progress_ms = current_playing_track['progress_ms']
        duration_ms = current_playing_track['item']['duration_ms']
        if (progress_ms / duration_ms) * 100 > TOO_LATE:
            return {}, status.HTTP_410_GONE

        room_votes = Votes.objects.filter(room=request.user.room).filter(action="SK")
        _ = room_votes.exclude(track_id=request.user.room.track_id).delete()
        if request.user.room.track_id != request.data['track_id']:
            return {}, status.HTTP_301_MOVED_PERMANENTLY

        track_votes = room_votes.filter(track_id=request.data['track_id'])
        votes = track_votes.count()
        for user in track_votes.values('user'):
            if request.user.session.session_key == user['user']:
                return {}, status.HTTP_208_ALREADY_REPORTED
        vote = Votes(
            room=request.user.room,
            user=request.user,
            action="SK",
            track_id=request.data['track_id']
        )
        vote.save()
        votes += 1

        if votes >= request.user.room.votes_to_skip:
            # El verdugo -> has hecho el voto de gracia
            sp_api = spotify_api.api_manager(request.user.room.host.spotify_basic_data)
            sp_api.next_track()
            room_snippets.register_track_in_state("SK", request.user.room, current_playing_track)
        return {}, status.HTTP_201_CREATED

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
            room = Rooms.objects.get(code=request.GET['code'])
        except ObjectDoesNotExist:
            return Response(response, status=status.HTTP_200_OK)
        # return [dict(Serializer(i).data) for i in query]
        query = TracksState.objects.filter(room=room).filter(state="SU")
        response['success_tracks'] = [
            dict(room.serializers.TracksStateSerializer(i).data)
            for i
            in query
        ]
        query = TracksState.objects.filter(room=room).filter(state="SK")
        response['skipped_tracks'] = [
            dict(room.serializers.TracksStateSerializer(i).data)
            for i
            in query
        ]
        query = TracksState.objects.filter(room=room).filter(state="RE")
        response['recommended_tracks'] = [
            dict(room.serializers.TracksStateSerializer(i).data)
            for i
            in query
        ]
        query = TracksState.objects.filter(room=room).filter(state="QU")
        response['queue_tracks'] = [
            dict(room.serializers.TracksStateSerializer(i).data)
            for i in query
        ]
        return response, status.HTTP_200_OK

    def patch(self, request, format=None):
        response = {}
        room_serializers.CodeSerializer(
            data=request.data
        ).is_valid(raise_exception=True)
        try:
            room = Rooms.objects.get(code=request.data['code'])
        except ObjectDoesNotExist:
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        if (timezone.now() - room.modified_at).total_seconds() > 2:
            sp_api_tunnel = spotify_api.api_manager(room.host.spotify_basic_data)
            data = sp_api_tunnel.current_playback()
            room = room_snippets.clean_playback(room, data)
        response['current_playback'] = room.current_playing_track

        if response['current_playback'] != {}:
            progress_ms = response['current_playback']['progress_ms']
            duration_ms = response['current_playback']['item']['duration_ms']
            same_track = response['current_playback']['item']['id'] == request.data['track_id']
            if not same_track:
                track_in_queue = TracksState.objects.filter(
                    room=room
                ).filter(
                    state="QU"
                ).filter(
                    track_id=response['current_playback']['item']['id']
                )
                if track_in_queue.exists():
                    track_in_queue[0].delete()
            if (progress_ms / duration_ms) * 100 > TOO_LATE and same_track:
                room_snippets.register_track_in_state(
                    'SU',
                    room,
                    response['current_playback']
                )

        participants_in_req = request.data.get('participants')
        if type(participants_in_req) is list:
            participants_in_db = room_snippets.construct_participants(
                user_models.Users.objects.filter(room=room)
            )
            response['participants'] = room_snippets.calculate_dict_deltas(
                participants_in_db,
                participants_in_req
            )
        votes_in_req = request.data.get('votes')
        if type(votes_in_req) is list:
            votes_in_db = room_snippets.construct_participants([
                vote.user
                for vote
                in Votes.objects.filter(room=room)
                .filter(track_id=room.track_id).filter(action="SK")
            ])
            response['votes_to_skip'] = room_snippets.calculate_dict_deltas(
                votes_in_db,
                votes_in_req,
                gone=False
            )
        queue_in_req = request.data.get('queue')
        if type(queue_in_req) is list:
            queue_in_db = [
                dict(room.serializers.TracksStateSerializer(i).data)
                for i
                in TracksState.objects.filter(room=room).filter(state="QU")
            ]
            response['queue'] = room_snippets.calculate_dict_deltas(
                queue_in_db,
                queue_in_req,
                gone=False,
            )
        response_code = status.HTTP_200_OK
        return Response(response, status=response_code)

    @in_room_required
    def put(self, request, format=None):
        response = {}
        room_serializers.CodeSerializer(data=request.data).is_valid(raise_exception=True)
        if not request.user.room.code == request.data['code']:
            response['detail'] = 'Room code does not match'
            return Response(response, status=status.HTTP_426_UPGRADE_REQUIRED)

        switch = resolve(request.path).url_name.lower()
        if switch == 'add-to-queue':
            response, status_code = self._put_add_to_queue(request)
        elif switch == 'toggle-is-playing':
            response, status_code = self._put_toggle_is_playing(request)
        else:
            response['detail'] = f'Bad request: {switch}'
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(response, status=status_code)

    @staticmethod
    def _put_add_to_queue(request):
        recommended_tracks = TracksState.objects.filter(
            room=request.user.room
        ).filter(
            state="RE"
        )
        recommended_tracks_ids = set(
            query['track_id']
            for query
            in recommended_tracks.values("track_id"))

        if not request.data['track_id'] in recommended_tracks_ids and not request.user.is_host:
            raise exceptions.NotFound("track_id not recommended")
        sp_api_tunnel = spotify_api.api_manager(request.user.room.host.spotify_basic_data)
        sp_api_tunnel.add_to_queue(request.data['track_id'])
        deleted_recommended_track = recommended_tracks.filter(track_id=request.data['track_id'])

        if deleted_recommended_track.exists():
            to_queue = deleted_recommended_track.values()[0]
            _ = deleted_recommended_track.delete()
        else:
            track_info = sp_api_tunnel.track(request.data['track_id'])
            to_queue = {}
            to_queue['uri'] = track_info['uri']
            to_queue['name'] = track_info['name']
            to_queue['album_name'] = track_info['album']['name']
            to_queue['album_image_url'] = track_info['album']['images'][0]['url']
            to_queue['track_id'] = track_info['id']
            to_queue['artists_str'] = ', '.join([
                artist['name'] for artist in track_info['artists']
            ])
            to_queue['external_url'] = track_info['external_urls']['spotify']

        uri = to_queue['uri']
        name = to_queue['name']
        album_name = to_queue['album_name']
        album_image_url = to_queue['album_image_url']
        track_id = to_queue['track_id']
        artists_str = to_queue['artists_str']
        external_url = to_queue['external_url']

        from django.db.utils import OperationalError
        try:
            track = TracksState(
                room=request.user.room,
                track_id=track_id,
                uri=uri,
                external_url=external_url or None,
                album_name=album_name or None,
                album_image_url=album_image_url or None,
                artists_str=artists_str or None,
                name=name or None,
                state="QU",
            )
            track.save()
        except OperationalError:
            import codecs
            import translitcodec # noqa

            name = codecs.encode(name, 'translit/long')
            album_name = codecs.encode(album_name, 'translit/long')
            artists_str = codecs.encode(artists_str, 'translit/long')

            track = TracksState(
                room=request.user.room,
                track_id=track_id,
                uri=uri,
                external_url=external_url or None,
                album_name=album_name or None,
                album_image_url=album_image_url or None,
                artists_str=artists_str or None,
                name=name or None,
                state="QU",
            )
            track.save()
        return {}, status.HTTP_201_CREATED

    @staticmethod
    def _put_toggle_is_playing(request):
        response = {}
        room_serializers.TrackIdSerializer(data=request.data).is_valid(raise_exception=True)
        if (
            (
                not request.user.room.track_id == request.data['track_id']
                or request.user.room.track_id is not None
            )
            and not request.user.is_host
        ):
            response['detail'] = 'track_id does not match'
            return response, status.HTTP_426_UPGRADE_REQUIRED

        if request.user.session.session_key != request.user.room.host.session.session_key:
            if not request.user.room.guests_can_pause:
                response['detail'] = "Pause for guests not allowed"
                return response, status.HTTP_403_FORBIDDEN

        sp_api_tunnel = spotify_api.api_manager(request.user.room.host.spotify_basic_data)
        try:
            sp_api_tunnel.pause_playback()
            status_code = status.HTTP_200_OK
        except SpotifyException:
            try:
                sp_api_tunnel.start_playback()
                status_code = status.HTTP_200_OK
            except SpotifyException:
                response['detail'] = 'Unable to toggle. Maybe Spotify API down. ' \
                    'Or spotify device not started. ' \
                    'Make sure that host is premium (update user details)'
                status_code = status.HTTP_403_FORBIDDEN

        return response, status_code
