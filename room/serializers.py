from django.db.models import fields
from rest_framework import serializers
from room.models import Rooms, SuccessTracks, SkippedTracks, RecommendedTracks

class CreateRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rooms
        fields=(
            'guests_can_pause',
            'votes_to_skip',
        )

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rooms
        fields = (
            'code',
            'guests_can_pause',
        )

class SuccessTracksSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuccessTracks
        exclude = ('room','id')

class SkippedTracksSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkippedTracks
        exclude = ('room','id')

class RecommendedTracksSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendedTracks
        exclude = ('room','id')