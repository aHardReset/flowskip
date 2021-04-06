from user.models import Users
from django.apps import apps
from rest_framework import authentication
from rest_framework import exceptions

class SessionAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            session_key = request.headers['session_key']
            #session = Session.objects.get(pk=session_key)
            #user = Users.objects.get(pk=session)
            user = Users.objects.get(pk=session_key)
        except KeyError as key:
            raise exceptions.AuthenticationFailed(f"API needs a {key}")
        except Users.DoesNotExist as e:
            raise exceptions.AuthenticationFailed("this Session does not exists")
        return (user, None)