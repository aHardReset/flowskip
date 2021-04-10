"""Views for manage User and dependences"""

# Django

# Rest Framework
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import exceptions

# Models
from user import models as user_models

# Serializars
from user.serializers import SessionSerializer

# Utilities
from spotify import api as spotify_api
from spotify.snippets import update_data_changed
from flowskip.auths import SessionAuthentication


class UserManager(APIView):
    authentication_classes = [SessionAuthentication]

    def post(self, request, format=None):
        response = {}

        session = user_models.Session.objects.get(pk=request.headers['session_key'])
        users = user_models.Users.objects.filter(pk=session)
        if users.exists():
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
        user = user_models.Users(pk=session)
        user.save()
        return Response(response, status=status.HTTP_201_CREATED)

    def delete(self, request, format=None):
        response = {}

        session = user_models.Session.objects.get(pk=request.headers['session_key'])

        users = user_models.Users.objects.filter(pk=session)
        if not users.exists():
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        user = users[0]
        _ = user.delete()
        return Response(response, status=status.HTTP_204_NO_CONTENT)

    def get(self, request, format=None):
        """Read information about an user

        Args:
            request ([type]): The request object
            format ([type], optional): [description]. Defaults to None.

        Returns:
            Response: Response object from APIView
        """

        response = {}
        session = user_models.Session.objects.get(pk=request.headers['session_key'])
        users = user_models.Users.objects.filter(pk=session)
        if not users.exists():
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        request.user = users[0]

        if request.user.spotify_basic_data:
            response['is_paid_user'] = user_models.PaidUsers.objects.filter(
                pk=request.user.spotify_basic_data.id
            ).exists()
            response['is_commerce'] = user_models.Commerces.objects.filter(
                pk=request.user.spotify_basic_data.id
            ).exists()
            response['user'] = self.get_status(request.user)
        response['has_spotify_login_info'] = request.user.spotify_basic_data is not None
        response['has_room'] = request.user.room is not None
        return Response(response, status=status.HTTP_200_OK)

    def get_status(self, user: object) -> dict:
        """Read information from spotify api

        Args:
            user (User Object): A single object query from DB from Users table

        Returns:
            data (dict): The data retrieved from spotify api for the current user
        """

        spotify_basic_data = user.spotify_basic_data
        sp = spotify_api.api_manager(spotify_basic_data)
        data = sp.current_user()
        update_data_changed(spotify_basic_data, data)
        return data


class SessionManager(APIView):
    """Views for manage sessions"""

    def post(self, request, format=None):
        """Creates a new session_key and returns it"""

        response = {}

        if request.session.session_key:
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
        request.session.create()
        session_key = request.session.session_key
        response['session_key'] = session_key
        return Response(response, status=status.HTTP_201_CREATED)

    def get(self, request, format=None):
        session = self.get_session(request)
        response = SessionSerializer(session).data
        return Response(response, status=status.HTTP_200_OK)

    def delete(self, request, format=None):
        response = {}
        session = self.get_session(request)
        _ = session.delete()
        return Response(response, status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def get_session(request) -> user_models.Session:
        session_key = request.headers.get("session_key", False)
        if not session_key:
            raise exceptions.AuthenticationFailed()

        sessions = user_models.Session.objects.filter(pk=session_key)
        if not sessions.exists():
            raise exceptions.NotFound()
        return sessions[0]
