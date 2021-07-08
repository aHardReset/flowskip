"""Redefinitions of auths to use the API"""

# Django
from rest_framework import authentication
from rest_framework import exceptions

# Models
from user import models as user_models


class UserAuthentication(authentication.BaseAuthentication):
    """Handling request headers to retrieve a Users instance

    Args:
        authentication (BaseAuth): djangorestframework Base auth
    """

    def authenticate(self, request):
        try:
            session_key = str(request.headers['Authorization']).removeprefix('Bearer ')
            # session = Session.objects.get(pk=session_key)
            # user = Users.objects.get(pk=session)
            user = user_models.Users.objects.get(pk=session_key)
        except KeyError:
            raise exceptions.NotAuthenticated("you need a session key")
        except user_models.Users.DoesNotExist:
            raise exceptions.NotFound("user doesn't exists")

        if user.room is not None:
            user.is_host = session_key == user.room.host.session.session_key
        return (user, None)


class SessionAuthentication(authentication.BaseAuthentication):
    """Handling headers to take session_key and see if is a valid
    Session instance

    Args:
        authentication (BaseAuth): djangorestframework Base Auth
    """

    def authenticate(self, request):
        Session = user_models.Session
        try:
            session_key = str(request.headers['Authorization']).removeprefix('Bearer ')
            _ = Session.objects.get(pk=session_key)
        except KeyError:
            raise exceptions.NotAuthenticated("you need a session key")
        except Session.DoesNotExist:
            raise exceptions.AuthenticationFailed("this session doesn't exists")
        return (None, None)
