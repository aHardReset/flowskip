from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from flowskip.auths import UserAuthentication
from user.models import Users
from spotify.snippets import construct_state_value, deconstruct_state_value, update_data_changed
from spotify.api import auth_manager, get_current_user, delete_cached_token
from spotify.models import SpotifyBasicData
from spotify import serializers as spotify_serializers

ALLOWED_REDIRECTS = ('')

class AuthenticateUser(APIView):
    authentication_classes = [UserAuthentication]
    
    def get(self, request, format=None):
        response = {}
        spotify_serializers.RedirectSerializer(data=request.GET).is_valid(raise_exception=True)
        if request.user.spotify_basic_data is not None and not request.GET.get("force_authentication"):
            return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
        
        state = construct_state_value(request.user.session.session_key, request.GET['redirect_url'])
        authorize_url = auth_manager(state).get_authorize_url()
        response['authorize_url'] = authorize_url

        return Response(response, status=status.HTTP_200_OK)

class SpotifyOauthRedirect(APIView):

    def get(self, request, format=None):
        response = {}
        code = request.GET.get('code')

        # Get the info that passes from spotify state string
        try:
            state = request.GET['state']
            params = deconstruct_state_value(state)
            session_key = params['session_key'][0]
            redirect_url = params['redirect_url'][0]
        except KeyError as key:
            print(f"not {key} provided in get")
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # If error, redirect with ?error=not_auth
        error = request.GET.get('error')
        if error is not None:
            return HttpResponseRedirect(redirect_url+f'?status={status.HTTP_401_UNAUTHORIZED}')
        del(error); del(params)

        # Get tokens from spotify
        user_auth_manager = auth_manager(state, username=session_key)
        user_auth_manager.get_access_token(
            code=code,
            as_dict=False,
            check_cache=False
        )
        
        # Use the tokens to get the user'info
        tokens = user_auth_manager.get_cached_token()
        data, new_tokens = get_current_user(tokens)
        if new_tokens:
            tokens = new_tokens
        
        # ? First implementation of spotipy error handler 
        if 'error' in data.keys():
            return HttpResponseRedirect(redirect_url+f'?status={status.HTTP_503_SERVICE_UNAVAILABLE}')
        del user_auth_manager

        users = Users.objects.filter(pk=session_key)

        for each_user in Users.objects.values('session', 'spotify_basic_data'):
            each_session = each_user['session']
            each_spotify_basic_data = each_user['spotify_basic_data']
            if each_spotify_basic_data == data['id']:
                _ = users.delete()
                delete_cached_token(session_key)
                return HttpResponseRedirect(redirect_url+ f'?status={status.HTTP_208_ALREADY_REPORTED}&session_key={each_session}')
        
        user = users[0]

        # Do a new SpotifyBasicData object
        try:
            spotify_basic_data = SpotifyBasicData.objects.get(pk=data['id'])
            spotify_basic_data(
                access_token= tokens['access_token'],
                refresh_token= tokens['refresh_token'],
                access_token_expires_at= tokens['expires_at']
            )
            spotify_basic_data.save(update_fields=[
                'access_token',
                'refresh_token',
                'access_token_expires_at'
            ])
            spotify_basic_data = update_data_changed(spotify_basic_data, data)
        except SpotifyBasicData.DoesNotExist:
            try:
                image_url = data['images'][0].get("url")
            except IndexError:
                image_url = None
            spotify_basic_data = SpotifyBasicData(
                id= data['id'],
                uri= data['uri'],
                display_name=data.get('display_name'),
                image_url = image_url,
                external_url= data['external_urls'].get("spotify"),
                product = data['product'],
                access_token= tokens['access_token'],
                refresh_token= tokens['refresh_token'],
                access_token_expires_at= tokens['expires_at']
            )
            user.spotify_basic_data = spotify_basic_data
            spotify_basic_data.save()
            user.save(update_fields=['spotify_basic_data'])
        
        delete_cached_token(session_key)
        return HttpResponseRedirect(redirect_url+f'?status={status.HTTP_200_OK}')
        