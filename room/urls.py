"""flowskip.room URL Configuration"""

# Django
from django.urls import path, include
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
    path(
        'update',
        view=views.RoomManager.as_view(),
        name='update'
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
    path(
        'state/add-to-queue',
        view=views.StateManager.as_view(),
        name='add-to-queue',
    ),
    path(
        'state/toggle-is-playing',
        view=views.StateManager.as_view(),
        name='toggle-is-playing',
    ),
]

urlpatterns = format_suffix_patterns(urlpatterns)

urlpatterns.append(
    # Player
    path(
        'state/player/',
        include(('room.player.urls', 'player'), namespace='player')
    )
)