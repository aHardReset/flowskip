from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
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

urlpatterns = format_suffix_patterns(urlpatterns)

urlpatterns.append(
    path(
        'api/',
        include(('spotify.apimirror.urls', 'apimirror'), namespace='apimirror')
    )
)
