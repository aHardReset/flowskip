from django.db import models
from django.db.models import fields
from rest_framework import serializers
from room.models import Rooms

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
            'votes_to_skip',
            'current_votes'
        )
