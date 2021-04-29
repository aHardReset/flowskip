from django.urls import path
from spotify import views
urlpatterns = [
    path(
        'authenticate-user',
        view=views.AuthenticateUser.as_view(),
        name='authenticate-user',
    ),
    path(
        'update',
        view=views.AuthenticateUser.as_view(),
        name='update',
    ),
    path(
        'spotify-oauth-redirect',
        view=views.SpotifyOauthRedirect.as_view(),
        name='spotify-oauth-redirect',
    ),
]
