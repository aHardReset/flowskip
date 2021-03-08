from django.contrib.sessions.models import Session
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from user.models import Users, PaidUsers, Commerces
from spotify.api import get_current_user
from spotify.snippets import update_data_changed
from flowskip import response_msgs

class StartSession(APIView):
    # Must be post
    def post(self, request, format=None):
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

class Create(APIView):
    def post(self, request, format=None):
        response = {}

        try:
            session_key = request.data["session_key"]
            session = Session.objects.get(pk=session_key)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        if Users.objects.filter(pk=session).exists():
            response['msg'] = response_msgs.user_already_exists(session_key)
            return Response(response, status=status.HTTP_409_CONFLICT)
        
        user = Users(pk=session)
        user.save()
        response['msg'] = response_msgs.user_created(session_key)
        return Response(response, status=status.HTTP_201_CREATED)

class Delete(APIView):
    def delete(self, request, format=None):
        response = {}

        try:
            session_key = request.data["session_key"]
            session = Session.objects.get(pk=session_key)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        user = Users.objects.filter(pk=session).delete()
        response['msg'] = response_msgs.user_deleted(user[0], session_key)
        return Response(response, status=status.HTTP_204_NO_CONTENT)

class Status(APIView):
    def get(self, request, format=None):
        response = {}

        try:
            session_key = request.GET["session_key"]
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
            expire_date = user.session.expire_date
            response['session_key'] = session_key
            response['user'] = f'user found and will be live up to {expire_date}'
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_200_OK)
        except Users.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_exists(session_key)
            return Response(response, status=status.HTTP_200_OK)
        
        spotify_basic_data = not user.spotify_basic_data is None
        has_room = not user.room is None
        
        if spotify_basic_data:
            response['is_paid_user'] = PaidUsers.objects.filter(pk=user.spotify_basic_data.id).exists()
            response['is_commerce'] = Commerces.objects.filter(pk=user.spotify_basic_data.id).exists()
        response['has_spotify_login_info'] = spotify_basic_data
        response['has_room'] = has_room

        return Response(response, status=status.HTTP_200_OK)

class Details(APIView):
    def get(self, request, format=None):
        response = {}

        try:
            session_key = request.GET["session_key"]
            session = Session.objects.get(pk=session_key)
            user = Users.objects.get(pk=session)
        except KeyError as key:
            response['msg'] = response_msgs.key_error(key)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        except Session.DoesNotExist:
            response['msg'] = response_msgs.session_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)  
        except Users.DoesNotExist:
            response['msg'] = response_msgs.user_does_not_exists(session_key)
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        spotify_basic_data = user.spotify_basic_data
        if spotify_basic_data is None:
            response['msg'] = response_msgs.user_not_authenticated(session_key)
            return Response(response, status=status.HTTP_401_UNAUTHORIZED)
        
        tokens = {
            'access_token': spotify_basic_data.access_token,
            'refresh_token': spotify_basic_data.refresh_token,
            'expires_at': spotify_basic_data.access_token_expires_at
        }
        data, new_tokens = get_current_user(tokens)
        if new_tokens:
            spotify_basic_data.access_token = new_tokens['access_token'],
            spotify_basic_data.refresh_token=new_tokens['refresh_token'],
            spotify_basic_data.access_token_expires_at = new_tokens['expires_at']
            spotify_basic_data.save(update_fields=[
                'access_token',
                'refresh_token',
                'access_token_expires_at'
            ])
        # Updating data if has changed
        update_data_changed(spotify_basic_data, data)
        response['user'] = data
        return Response(response, status=status.HTTP_200_OK)