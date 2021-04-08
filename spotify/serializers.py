from rest_framework import serializers

class RedirectSerializer(serializers.Serializer):
    redirect_url = serializers.CharField()