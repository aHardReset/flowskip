from rest_framework import serializers
from django.contrib.sessions.models import Session


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        exclude = ('session_data',)
