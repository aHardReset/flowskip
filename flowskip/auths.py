from user import models as user_models
from django.apps import apps
from rest_framework import authentication
from rest_framework import exceptions

class UserAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            session_key = request.headers['session_key']
            #session = Session.objects.get(pk=session_key)
            #user = Users.objects.get(pk=session)
            user = user_models.Users.objects.get(pk=session_key)
        except KeyError:
            raise exceptions.NotAuthenticated("you need a session key")
        except user_models.Users.DoesNotExist:
            raise exceptions.NotFound("user doesn't exists")
        
        return (user, None)

class SessionAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        Session = user_models.Session
        try:
            session_key = request.headers['session_key']
            session = Session.objects.get(pk=session_key)
        except KeyError:
            raise exceptions.NotAuthenticated("you need a session key")
        except Session.DoesNotExist:
            raise exceptions.AuthenticationFailed("this session doesn't exists")

        return (None, None)