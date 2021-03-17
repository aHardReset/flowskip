"""Views for manage User and dependences
"""

# Django
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist

# Rest Framework
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Models
from user.models import Users, PaidUsers, Commerces

# Utilities
from spotify.api import get_current_user
from spotify.snippets import update_data_changed, get_db_tokens, update_db_tokens
from flowskip import response_msgs

class UserManager(APIView):
    """Class to manage the Users in the system
    """

    def post(self, request, format=None):
        """Create a new user

        Args:
            request ([type]): The request
            format ([type], optional): [description]. Defaults to None.

        Returns:
            Response: Response object from APIView
        """
        response = {}

        try:
            session_key = request.data["session_key"]
            session = Session.objects.get(pk=session_key)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        user = Users(pk=session)
        user.save()
        response['msg'] = response_msgs.user_created(session_key)
        return Response(response, status=status.HTTP_201_CREATED)

    def delete(self, request, format=None):
        response = {}

        try:
            session_key = request.data["session_key"]
            session = Session.objects.get(pk=session_key)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        user = Users.objects.filter(pk=session).delete()
        response['msg'] = response_msgs.user_deleted(user[0], session_key)
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

        try:
            session_key = request.GET["session_key"]
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            expire_date = user.session.expire_date
            response['session_key'] = session_key
            response['msg'] = f'user found and will be live up to {expire_date}'
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            response['msg'] = response['msg'] = str(e).replace("query", session_key)
            return Response(response, status=status.HTTP_200_OK)
        
        spotify_basic_data = not user.spotify_basic_data is None
        has_room = not user.room is None
        
        if spotify_basic_data:
            response['is_paid_user'] = PaidUsers.objects.filter(pk=user.spotify_basic_data.id).exists()
            response['is_commerce'] = Commerces.objects.filter(pk=user.spotify_basic_data.id).exists()
            response['user'] = self.get_status(user)
        response['has_spotify_login_info'] = spotify_basic_data
        response['has_room'] = has_room

        return Response(response, status=status.HTTP_200_OK)
    
    def get_status(self, user: object) -> dict:
        """Read information from spotify api

        Args:
            user (User Object): A single object query from DB from Users table

        Returns:
            data (dict): The data retrieved from spotify api for the current user
        """

        spotify_basic_data = user.spotify_basic_data
        tokens = get_db_tokens(spotify_basic_data)
        data, new_tokens = get_current_user(tokens)
        if new_tokens:
            spotify_basic_data =  update_db_tokens(spotify_basic_data, new_tokens)
        
        update_data_changed(spotify_basic_data, data)
        return data

class SessionManager(APIView):
    """Views for manage sessions
    """
    def post(self, request, format=None):
        """Creates a new session_key and returns it

        Args:
            request ()

        """
        response = {}
        """
        change to after go production
        if request.session.session_key == None:
            request.session.create()
        """
        request.session.create()
        session_key = request.session.session_key
        
        response['msg'] = response_msgs.session_started(session_key)
        response['session_key'] = session_key
        return Response(response, status=status.HTTP_201_CREATED)