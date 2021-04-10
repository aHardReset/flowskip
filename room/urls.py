"""flowskip.room URL Configuration"""

# Django
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

# Views
from room import views

urlpatterns = [
    # Room Manager
    path(
        'create',
        view=views.RoomManager.as_view(),
        name='create'
    ),
    path(
        'create-advanced',
        view=views.RoomManager.as_view(),
        name='create-advanced'
    ),
    path(
        'details',
        view=views.RoomManager.as_view(),
        name='details'
    ),

    # Participants manager
    path(
        'participants/join',
        view=views.ParticipantManager.as_view(),
        name='join'
    ),
    path(
        'participants/leave',
        view=views.ParticipantManager.as_view(),
        name='leave'
    ),

    # Room State
    path(
        'state/',
        view=views.StateManager.as_view(),
        name='state'
    ),
    path(
        'state/vote-to-skip',
        view=views.StateManager.as_view(),
        name='vote-to-skip'
    ),
    path(
        'state/tracks',
        view=views.StateManager.as_view(),
        name='tracks'
    ),
]

urlpatterns = format_suffix_patterns(urlpatterns)
