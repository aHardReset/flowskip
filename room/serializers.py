from rest_framework import serializers
from room import models as room_models


class CreateRoomSerializer(serializers.ModelSerializer):
    guests_can_pause = serializers.BooleanField()
    votes_to_skip = serializers.IntegerField()

    class Meta:
        model = room_models.Rooms
        fields = (
            'guests_can_pause',
            'votes_to_skip',
        )


class RoomInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = room_models.Rooms
        fields = (
            'code',
            'guests_can_pause',
            'votes_to_skip',

        )


class AddToQueueSerializer(serializers.Serializer):
    track_id = serializers.CharField()


class SuccessTracksSerializer(serializers.ModelSerializer):
    """Intended to clear the data before is sending in response
    """
    class Meta:
        model = room_models.SuccessTracks
        exclude = ('room', 'id')


class SkippedTracksSerializer(serializers.ModelSerializer):
    class Meta:
        model = room_models.SkippedTracks
        exclude = ('room', 'id')


class RecommendedTracksSerializer(serializers.ModelSerializer):
    class Meta:
        model = room_models.RecommendedTracks
        exclude = ('room', 'id')


class QueueTracksSerializer(serializers.ModelSerializer):
    class Meta:
        model = room_models.QueueTracks
        exclude = ('room', 'id')


class TrackIdSerializer(serializers.Serializer):
    track_id = serializers.CharField()


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField()


class StateManagerSerializer(TrackIdSerializer, CodeSerializer):
    pass
