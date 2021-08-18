from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from room.player import views


urlpatterns = [
    path(
        'toggle-is-playing',
        view=views.PlayerManager.as_view(),
        name='toggle-is-playing'
    ),
    path(
        'play',
        view=views.PlayerManager.as_view(),
        name='play'
    ),
    path(
        'pause',
        view=views.PlayerManager.as_view(),
        name='pause'
    ),
]

urlpatterns = format_suffix_patterns(urlpatterns)
