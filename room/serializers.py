from rest_framework import serializers
from room.models import Rooms, TracksState


class CreateRoomSerializer(serializers.ModelSerializer):
    guests_can_pause = serializers.BooleanField()
    votes_to_skip = serializers.IntegerField()

    class Meta:
        model = Rooms
        fields = (
            'guests_can_pause',
            'votes_to_skip',
        )


class RoomInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rooms
        fields = (
            'code',
            'guests_can_pause',
            'votes_to_skip',

        )


class AddToQueueSerializer(serializers.Serializer):
    track_id = serializers.CharField()


class TracksStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TracksState
        exclude = ('room', 'id', 'state')


class TrackIdSerializer(serializers.Serializer):
    track_id = serializers.CharField()


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField()


class StateManagerSerializer(TrackIdSerializer, CodeSerializer):
    pass
