from typing import Tuple
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from flowskip.auths import UserAuthentication
from spotify.decorators import is_authenticated_in_spotify_required
from user.models import Session, Users
from rest_framework import exceptions
from spotify.snippets import construct_state_value, deconstruct_state_value, update_data_changed
from spotify.api import api_manager, auth_manager, get_current_user, delete_cached_token
from spotify.models import SpotifyBasicData
from spotify import serializers as spotify_serializers

ALLOWED_REDIRECTS = ('')


class AuthenticateUser(APIView):
    authentication_classes = [UserAuthentication]

    def get(self, request, format=None):
        response = {}

        spotify_serializers.RedirectSerializer(data=request.GET).is_valid(raise_exception=True)
        force_authentication = request.GET.get("force_authentication", "")

        if (request.user.spotify_basic_data is not None
                and not force_authentication.lower() in {'true', '1', 'yes'}):
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
        state = construct_state_value(request.user.session.session_key, request.GET['redirect_url'])
        authorize_url = auth_manager(state).get_authorize_url()
        response['authorize_url'] = authorize_url

        return Response(response, status=status.HTTP_200_OK)

    @is_authenticated_in_spotify_required
    def patch(self, request, format=None):
        old_spotify_basic_data = request.user.spotify_basic_data
        sp = api_manager(old_spotify_basic_data)
        data = sp.current_user()
        new_spotify_basic_data = update_data_changed(request.user.spotify_basic_data, data)
        if(vars(old_spotify_basic_data) == vars(new_spotify_basic_data)):
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        return Response(data, status=status.HTTP_205_RESET_CONTENT)


class SpotifyOauthRedirect(APIView):
    """Since this class is all driven by spotify
    it will the only
    """

    @staticmethod
    def get_state(request):
        try:
            return request.GET['state']
        except KeyError:
            raise exceptions.APIException(
                "Spotify doesn't provide the state. Report this immediately",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def get_user_data(state, session_key, code):
        user_auth_manager = auth_manager(state, username=session_key)
        user_auth_manager.get_access_token(
            code=code,
            as_dict=False,
            check_cache=False
        )

        # Use the tokens to get the user info
        tokens = user_auth_manager.get_cached_token()
        data, new_tokens = get_current_user(tokens)
        if new_tokens:
            tokens = new_tokens
        return data, tokens

    @staticmethod
    def get_image_url(data):
        try:
            image_url = data['images'][0].get("url")
        except IndexError:
            image_url = None
        return image_url

    @staticmethod
    def get_user_to_add_spotify_basic_data(data, session_key) -> Tuple[Users, int]:
        users = Users.objects.filter(pk=session_key)
        if not users.exists():
            raise exceptions.NotFound(f"{session_key} as user")

        for each_user in Users.objects.values('session', 'spotify_basic_data'):
            each_session_key = each_user['session']
            each_spotify_basic_data = each_user['spotify_basic_data']
            if each_spotify_basic_data == data['id']:
                if each_session_key != session_key:
                    _ = users.delete()
                    _ = Session.objects.filter(pk=session_key).delete()
                delete_cached_token(session_key)
                user = Users.objects.get(pk=each_session_key)
                response_code = status.HTTP_208_ALREADY_REPORTED
                break
        else:
            user = users[0]
            response_code = status.HTTP_200_OK

        return user, response_code

    def get(self, request, format=None):
        code = request.GET.get('code')

        # Get the info that passes from spotify state string
        state = self.get_state(request)
        params = deconstruct_state_value(state)

        try:
            session_key = params['session_key'][0]
            redirect_url = params['redirect_url'][0]
        except KeyError as key:
            print(f"not {key} provided in get")
            raise exceptions.APIException(None, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # If error, redirect with ?error=not_auth
        if request.GET.get('error') is not None:
            return HttpResponseRedirect(redirect_url + f'?status={status.HTTP_401_UNAUTHORIZED}')

        data, tokens = self.get_user_data(state, session_key, code)

        # ? First implementation of spotipy error handler
        if 'error' in data.keys():
            return HttpResponseRedirect(
                redirect_url
                + f'?status={status.HTTP_503_SERVICE_UNAVAILABLE}'
            )

        user, response_code = self.get_user_to_add_spotify_basic_data(data, session_key)

        # Do a new SpotifyBasicData object
        if user.spotify_basic_data is not None:
            user.spotify_basic_data = None
            user.save(update_fields=['spotify_basic_data'])
        spotify_basic_data = SpotifyBasicData.objects.filter(pk=data['id'])
        if spotify_basic_data.exists():
            _ = spotify_basic_data.delete()
        spotify_basic_data = SpotifyBasicData(
            id=data['id'],
            uri=data['uri'],
            display_name=data.get('display_name'),
            image_url=self.get_image_url(data),
            external_url=data['external_urls'].get("spotify"),
            product=data['product'],
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            access_token_expires_at=tokens['expires_at']
        )
        spotify_basic_data.save()
        user.spotify_basic_data = spotify_basic_data
        user.save(update_fields=['spotify_basic_data'])

        delete_cached_token(session_key)
        params = "&".join([
            f'status={response_code}',
            f'session_key={user.session.session_key}'
        ])
        return HttpResponseRedirect(redirect_url + '?' + params)
