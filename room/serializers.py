from rest_framework import serializers
from room import models as room_models

class CreateRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = room_models.Rooms
        fields=(
            'guests_can_pause',
            'votes_to_skip',
        )

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = room_models.Rooms
        fields = (
            'code',
            'guests_can_pause',
        )

class SuccessTracksSerializer(serializers.ModelSerializer):
    """Intended to clear the data before is sending in response
    """
    class Meta:
        model = room_models.SuccessTracks
        exclude = ('room','id')

class SkippedTracksSerializer(serializers.ModelSerializer):
    class Meta:
        model = room_models.SkippedTracks
        exclude = ('room','id')

class RecommendedTracksSerializer(serializers.ModelSerializer):
    class Meta:
        model = room_models.RecommendedTracks
        exclude = ('room','id')

class TrackIdSerializer(serializers.Serializer):
    track_id = serializers.CharField()

class CodeSerializer(serializers.Serializer):
    code = serializers.CharField()

class StateManagerSerializer(TrackIdSerializer, CodeSerializer):
    pass

    